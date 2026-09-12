#!/usr/bin/env python3
"""
Test traffic script for Class 9 - sends concurrent requests to the gateway
Tests admission control, routing, and overflow to Superlinked
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Load environment variables
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

PREFILL_URL = os.getenv("PREFILL_URLS", "http://127.0.0.1:8000").split(",")[0]
GATEWAY_URL = f"{PREFILL_URL}/v1/completions"
NUM_REQUESTS = int(os.getenv("TEST_NUM_REQUESTS", "5"))
MAX_TOKENS = int(os.getenv("TEST_MAX_TOKENS", "100"))
REQUEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "10"))

class TestResults:
    def __init__(self):
        self.success = 0
        self.overflow = 0  # 503 Service Unavailable
        self.rejected = 0  # 429 Too Many Requests
        self.errors = 0
        self.responses = []
        self.total_time = 0
        self.start_time = None

    def add_response(self, status, response_time, body):
        if status == 200:
            self.success += 1
        elif status == 503:
            self.overflow += 1
        elif status == 429:
            self.rejected += 1
        else:
            self.errors += 1

        self.responses.append({
            "status": status,
            "time": response_time,
            "timestamp": datetime.now().isoformat()
        })

    def print_summary(self):
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total requests sent:        {len(self.responses)}")
        print(f"✅ Success (200):           {self.success}")
        print(f"🚀 Overflow (503):          {self.overflow}")
        print(f"⚠️  Rejected (429):         {self.rejected}")
        print(f"❌ Errors:                  {self.errors}")
        print(f"\nTotal time:                 {sum(r['time'] for r in self.responses):.2f}s")
        print(f"Average time per request:   {sum(r['time'] for r in self.responses)/len(self.responses):.2f}s" if self.responses else "N/A")
        print("="*60)

        if self.overflow > 0:
            print("✅ OVERFLOW DETECTED!")
            print("   Requests were successfully sent to Superlinked")
            print("   Check Superlinked console for spend increase")
        elif self.success > 0:
            print("✅ REQUESTS PROCESSED")
            print("   Cluster handled requests without overflow")
        else:
            print("⚠️  NO SUCCESSFUL REQUESTS")
            print("   Check gateway connectivity and logs")

async def send_request(session, request_num, results):
    """Send a single request to the gateway"""
    payload = {
        "prompt": f"[Request {request_num}] Write a short paragraph about GPU memory optimization and inference performance.",
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }

    try:
        start = asyncio.get_event_loop().time()

        async with session.post(
            GATEWAY_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            headers={"Content-Type": "application/json"}
        ) as resp:
            elapsed = asyncio.get_event_loop().time() - start
            body = await resp.text()

            status = resp.status
            results.add_response(status, elapsed, body)

            # Print immediate feedback
            status_emoji = "✅" if status == 200 else "🚀" if status == 503 else "⚠️ " if status == 429 else "❌"
            print(f"  [{request_num}] {status_emoji} Status: {status:3d} | Time: {elapsed:6.2f}s")

            return status

    except asyncio.TimeoutError:
        print(f"  [{request_num}] ❌ Timeout after {REQUEST_TIMEOUT}s")
        results.errors += 1
    except aiohttp.ClientError as e:
        print(f"  [{request_num}] ❌ Connection error: {e}")
        results.errors += 1
    except Exception as e:
        print(f"  [{request_num}] ❌ Unexpected error: {e}")
        results.errors += 1

async def send_concurrent_requests(num_requests):
    """Send multiple requests concurrently"""
    print(f"\n🚀 Sending {num_requests} concurrent requests to: {GATEWAY_URL}")
    print("=" * 60)

    results = TestResults()
    results.start_time = asyncio.get_event_loop().time()

    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, i+1, results)
            for i in range(num_requests)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    results.total_time = asyncio.get_event_loop().time() - results.start_time
    return results

def main():
    print("\n" + "="*60)
    print("CLASS 9: GATEWAY TEST TRAFFIC GENERATOR")
    print("="*60)
    print(f"Gateway:                    {GATEWAY_URL}")
    print(f"Concurrent requests:        {NUM_REQUESTS}")
    print(f"Max tokens per request:     {MAX_TOKENS}")
    print(f"Request timeout:            {REQUEST_TIMEOUT}s")
    print("="*60)

    try:
        results = asyncio.run(send_concurrent_requests(NUM_REQUESTS))
        results.print_summary()

        # Exit with proper code
        if results.overflow > 0:
            print("\n✅ Test PASSED: Overflow detected!")
            sys.exit(0)
        elif results.success > 0:
            print("\n✅ Test PASSED: Requests processed!")
            sys.exit(0)
        else:
            print("\n❌ Test FAILED: No successful requests")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
