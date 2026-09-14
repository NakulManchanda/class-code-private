#!/usr/bin/env python3
"""
Targeted rejection tests — trigger specific rejection paths
Run with: python -m tests.test_rejections <rejection_type>
"""

import os
import sys
import json
import asyncio
import aiohttp
from typing import List, Dict

# Load config
ORCH_URL = os.getenv("ORCH_URL", "http://127.0.0.1:8080/v1")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
NUM_REQUESTS = int(os.getenv("NUM_REQUESTS", "5"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "1"))

print(f"Testing rejections against: {ORCH_URL}")
print(f"Max tokens: {MAX_TOKENS}, Requests: {NUM_REQUESTS}, Concurrency: {CONCURRENCY}")

# ============================================================================
# REJECTION TRIGGERS
# ============================================================================

class RejectionTests:
    """Trigger different rejection paths in the system"""

    # Test 1: ADMISSION — Tenant token limit (429)
    @staticmethod
    def admission_tenant_tokens() -> Dict:
        """Exhaust tenant token quota → 429 rejection"""
        return {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "Write a comprehensive response covering the following topics: quantum computing, artificial intelligence, machine learning, neural networks, and their applications in modern technology. Please be detailed and thorough."
                }
            ],
            "max_tokens": 2048,  # Max allowed - trigger quota check
            "temperature": 1.0,  # Force diversity
        }

    # Test 2: ADMISSION — Queue full (429)
    @staticmethod
    def admission_queue_full() -> Dict:
        """Fill request queue → 429 rejection"""
        return {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "This is a normal request but queue will be full from other concurrent requests"
                }
            ],
            "max_tokens": 1024,
            "timeout": 30,  # Long timeout to keep request in queue
        }

    # Test 3: ROUTER — No eligible pod (503)
    @staticmethod
    def router_no_eligible_pod() -> Dict:
        """Request model with no available pods → 503 rejection"""
        return {
            "model": "Qwen/Qwen2.5-VL-3B-Instruct",  # Vision model (no local pod)
            "messages": [
                {
                    "role": "user",
                    "content": "What's in this image? (This will route to Superlinked)"
                }
            ],
            "max_tokens": 512,
        }

    # Test 4: ROUTER — Unknown model (503/overflow)
    @staticmethod
    def router_unknown_model() -> Dict:
        """Request unknown model → overflow to Superlinked"""
        return {
            "model": "meta-llama/Llama-2-7b-chat-hf",  # Not in local allowlist
            "messages": [
                {
                    "role": "user",
                    "content": "This model doesn't exist locally, route to Superlinked"
                }
            ],
            "max_tokens": 512,
        }

    # Test 5: GATEWAY — High concurrency (429/503 staggered)
    @staticmethod
    def gateway_high_concurrency() -> Dict:
        """High concurrency → admission/placement rejection"""
        return {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "Process this quickly among 50+ concurrent requests"
                }
            ],
            "max_tokens": 256,  # Short response to compete for resources
        }

    # Test 6: MOONCAKE — KV cache pressure
    @staticmethod
    def mooncake_kv_pressure() -> Dict:
        """Large context → KV cache pressure → 503"""
        context = "Machine learning is transforming industries. " * 50  # ~2000 chars
        return {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nBased on the above context, summarize the key points."
                }
            ],
            "max_tokens": 1024,
        }

    # Test 7: KEDA — Insufficient replicas
    @staticmethod
    def keda_insufficient_replicas() -> Dict:
        """Trigger KEDA to scale up (or hit current replica limit)"""
        return {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "Waiting for KEDA to scale... Request with concurrent load"
                }
            ],
            "max_tokens": 512,
        }

    # Test 8: OVERFLOW — Trigger Superlinked fallback
    @staticmethod
    def overflow_superlinked() -> Dict:
        """Request that will overflow to Superlinked"""
        return {
            "model": "Qwen/Qwen3.5-4B",  # Non-local model (will use Superlinked)
            "messages": [
                {
                    "role": "user",
                    "content": "This request will overflow to Superlinked paid API"
                }
            ],
            "max_tokens": 256,
        }

# ============================================================================
# CLIENT
# ============================================================================

async def send_request(session: aiohttp.ClientSession, payload: Dict) -> Dict:
    """Send single request and capture response"""
    try:
        async with session.post(
            f"{ORCH_URL}/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            return {
                "status": resp.status,
                "error": data.get("error", {}).get("message", ""),
                "model": payload.get("model"),
                "tokens": payload.get("max_tokens", 0),
            }
    except Exception as e:
        return {
            "status": 0,
            "error": str(e),
            "model": payload.get("model"),
            "tokens": payload.get("max_tokens", 0),
        }

async def run_rejection_test(test_name: str, test_fn, concurrency: int, num_requests: int):
    """Run rejection test with specified concurrency"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Concurrency: {concurrency}, Requests: {num_requests}")

    async with aiohttp.ClientSession() as session:
        results = {
            200: 0,
            429: 0,
            503: 0,
            0: 0,
            "errors": []
        }

        # Send all requests concurrently
        tasks = []
        for i in range(num_requests):
            payload = test_fn()
            tasks.append(send_request(session, payload))

            # Limit concurrency
            if len(tasks) >= concurrency:
                responses = await asyncio.gather(*tasks)
                for resp in responses:
                    status = resp["status"]
                    if status in results and status != "errors":
                        results[status] += 1
                    else:
                        results[0] += 1
                    if resp["error"]:
                        results["errors"].append(f"{status}: {resp['error']}")
                tasks = []

        # Wait for remaining
        if tasks:
            responses = await asyncio.gather(*tasks)
            for resp in responses:
                status = resp["status"]
                if status in results and status != "errors":
                    results[status] += 1
                else:
                    results[0] += 1
                if resp["error"]:
                    results["errors"].append(f"{status}: {resp['error']}")

    # Print results
    total = sum(v for k, v in results.items() if k != "errors")
    print(f"\nResults:")
    print(f"  ✅ 200 (Success):     {results[200]:3d} ({100*results[200]/total:.1f}%)")
    print(f"  🔴 429 (Shed):        {results[429]:3d} ({100*results[429]/total:.1f}%)")
    print(f"  🟠 503 (No pod):      {results[503]:3d} ({100*results[503]/total:.1f}%)")
    print(f"  ❌ Errors:           {results[0]:3d}")

    if results["errors"] and len(results["errors"]) <= 5:
        print(f"\nSample errors:")
        for err in results["errors"][:5]:
            print(f"  - {err}")

    return results

# ============================================================================
# MAIN
# ============================================================================

async def main():
    if len(sys.argv) < 2:
        print("\nUsage: python -m tests.test_rejections <rejection_type>")
        print("\nAvailable rejection types:")
        print("  1. admission_tenant_tokens   — Exhaust token quota (429)")
        print("  2. admission_queue_full      — Fill request queue (429)")
        print("  3. router_no_eligible_pod    — No pod for model (503)")
        print("  4. router_unknown_model      — Unknown model (503/overflow)")
        print("  5. gateway_high_concurrency  — High concurrency (429/503)")
        print("  6. mooncake_kv_pressure      — Large context → KV pressure (503)")
        print("  7. keda_insufficient_replicas— Insufficient replicas (503)")
        print("  8. overflow_superlinked      — Trigger Superlinked fallback (200)")
        print("  all                          — Run all tests")
        sys.exit(1)

    test_type = sys.argv[1].lower()
    tests = RejectionTests()

    if test_type == "all":
        for name in ["admission_tenant_tokens", "router_no_eligible_pod",
                     "gateway_high_concurrency", "overflow_superlinked"]:
            test_fn = getattr(tests, name)
            await run_rejection_test(name, test_fn, CONCURRENCY, NUM_REQUESTS)
    else:
        if not hasattr(tests, test_type):
            print(f"Unknown rejection type: {test_type}")
            sys.exit(1)

        test_fn = getattr(tests, test_type)
        await run_rejection_test(test_type, test_fn, CONCURRENCY, NUM_REQUESTS)

if __name__ == "__main__":
    asyncio.run(main())
