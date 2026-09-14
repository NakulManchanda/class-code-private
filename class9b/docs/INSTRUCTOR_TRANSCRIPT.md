# Class 9b Instructor Transcript

**Date**: Sep 13, 2026 (approx 11:44 onwards)

---

## Overview: Three Ways to Interact with the System

### 1. **WebUI (Open WebUI)**
- Direct chat interface at `http://127.0.0.1:30030`
- Talk to the models in real-time
- Example: "Can you tell me about..."
- Models automatically route based on type (text/vision)

### 2. **Crew AI Flooding** 
- Sends concurrent requests programmatically
- Test concurrency patterns and scalability
- See how the system handles multiple simultaneous requests
- Command: `make crew-flood` (48 rounds, 8 workers)

### 3. **Locust Load Testing**
- Pick concurrent users (e.g., 10 users)
- Spawn rate (e.g., 1 user every 2 seconds)
- Sends requests to backend (orch-serve)
- Live dashboard showing:
  - RPS (requests per second)
  - Failure rate (0%, 429 errors, etc.)
  - Real-time metrics updates (every 5 seconds)
- All visible in Grafana dashboards

---

## Architecture: Layers

```
WebUI / Locust / Crew AI
        ↓
    Gateway (orch-serve)  ← Admission control
        ↓
    Router              ← Model/endpoint binding
        ↓
Backend (vLLM replicas)  ← Prefill + Decode
        ↓
    GPU (KV cache)      ← Mooncake
        ↓
    K8s (KEDA scaling)  ← HAMi slicing
```

### Key Components

1. **Gateway** (orch-serve)
   - Orchestration layer
   - Admission control
   - Health checks → auto-scaling
   - Same as class 9

2. **Router**
   - Model/capability binding
   - Text request → text model
   - Vision request → vision model
   - Overflow → Superlinked (fallback)
   - Defined in gateway/planner

3. **App Layer**
   - Harness: max tokens, behaviors
   - Locustfile: test payloads
   - Guardrails (not heavily used today)
   - Request formats

4. **vLLM Backend**
   - Prefill + Decode separation
   - KV cache management
   - Models loaded on startup

---

## Models & Routing

### Text Model
- **Model**: Qwen/Qwen2.5-3B-Instruct
- **Endpoint**: Prefill/Decode (disaggregated)
- Automatically routes text requests

### Vision Model
- **Model**: Qwen/Qwen2.5-VL-3B-Instruct
- **Endpoint**: Separate endpoint
- Automatically routes vision requests

### Overflow
- **Handler**: Superlinked API
- **Fallback**: When models are overloaded
- **Cost**: Different pricing than local models
- Response might come from different model than requested

---

## Observability: Grafana Dashboards

Collected from k8s metrics (not just NVIDIA SMI).

### Dashboards (in order)

1. **Cluster Dashboard**
   - Node count, memory, CPU
   - Overall cluster health

2. **Success & Failures**
   - RPS (requests/sec)
   - Success rate
   - Failure reasons (429, 503, errors)
   - Shedding by system

3. **Overview (metrics.py)**
   - Request-level metrics
   - Averaged stats

4. **Gateway + Admission**
   - Admission control behavior
   - Request admission/rejection

5. **Router**
   - Routing decisions
   - Model selection

6. **KEDA**
   - Auto-scaling status
   - Replica count changes

7. **HAMi Slices**
   - GPU slicing allocation
   - Memory per slice

8. **Mooncake KV Cache**
   - KV hops (prefill→decode)
   - Cache evictions
   - Block tracking

9. **Pods & Replicas**
   - Pod status
   - Replica distribution

10. **vLLM Metrics**
    - GPU utilization
    - Token throughput
    - Inference stats

---

## Setup Steps

### Part 1: Sync & Basic Setup (Mac terminal)

```bash
# Step 1: Sync code to Lambda
bash setup/sync_to_lambda.sh

# Step 2: Open SSH tunnel (keep this terminal open!)
bash setup/ssh.sh
```

### Part 2: Lambda Setup (Same SSH terminal)

```bash
# Step 3: Install vLLM, transformers, models
bash setup/lambda_setup.sh

# Step 4: Install k3s + HAMi + KEDA + Mooncake
bash setup/lambda_cluster.sh    # Takes 5-7 min on 80GB machine

# Step 5: Check cluster status
kubectl get deploy,svc,scaledobject

# Step 6: Smoke test
bash setup/smoke_sliced.sh
```

Expected output: `SLICED SMOKE PASS`

### Part 3: Interactions (New Mac terminal)

```bash
# Step 7: Open WebUI
open http://127.0.0.1:30030

# Step 8: Send a message in browser

# Step 9-20: REPL traffic testing
cd class-code/class9b
source .venv/bin/activate
set -a && source .env && set +a
python -m gateway.repl
```

### Part 4: Day 2 - Observability

```bash
# Step 22: Setup Grafana (on Lambda)
bash setup/day2_observability.sh

# Step 23: Get Grafana password
kubectl -n monitoring get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo

# Step 24: Open Grafana
open http://127.0.0.1:31495
# Login: admin / <password from Step 23>
```

### Part 5: Load Testing

```bash
# Step 25: Install Locust
pip install -r requirements-load.txt

# Step 26: Run Locust
locust -f app/locustfile.py --host http://127.0.0.1:8080

# Step 27: Open Locust UI
open http://127.0.0.1:8089

# Step 28: Set users=4, spawn_rate=2, click Start
# Let it run 1+ min for Grafana rate() panels to populate
```

### Part 6: Crew Flood Analysis

```bash
# Step 29: Run crew_flood
ORCH_URL=http://127.0.0.1:8080/v1 python -m app.crew_flood --rounds 48 --workers 8

# Step 30: View Grafana dashboards (10 dashboards in order)
```

---

## Important Notes

### Memory & Concurrency

- **40GB Machine**: ~15GB per replica (2 replicas)
- **Model + KV cache**: ~6-7GB per model
- **Safe limit**: 5-10 concurrent requests max
- **Beyond 10**: More 429/503 errors (system shedding)
- **H100**: Can push further, more headroom

### Lambda Specifics

- **Firewall**: Lambda only allows SSH
- **Port forwarding**: Via SSH tunnel (`make ssh` keeps it open)
- **Local access**: Only 127.0.0.1 URLs from Mac
- **No direct public IP access**: Must use tunnel

### Request Format

- Defined in `gateway/planner` (or similar routing config)
- **Prefill**: Always goes to prefill endpoint
- **Decode**: Always goes to decode endpoint
- **Model selection**: Based on request format
- **Overflow**: Superlinked handles fallback

### Metrics

- Emitted by code (gateway, router, vLLM)
- **Not from NVIDIA SMI directly**, but aggregated
- Collected via k8s scraping
- Dashboards defined in observability configs
- Can add more metrics to Grafana YAML

---

## Q&A Highlights

**Q**: Why are models listed separately if router does binding?
**A**: Different models can be marked as "text" or "vision" labels. If you pick "vision", it explicitly requests that model. If you pick a generic model, it goes through overflow. Allows distinction between labeled requests vs fallback.

**Q**: Where do Grafana metrics come from?
**A**: From code-emitted metrics (not just NVIDIA SMI). Aggregated at k8s level. Defined in observability YAML configs.

**Q**: How much memory will Qwen 3B need?
**A**: ~6-7GB per model + KV cache overhead. With 40GB total and 2 replicas (~15GB each), should be fine for ~10 concurrent requests.

**Q**: What if system breaks?
**A**: KEDA auto-scales replicas up. Admission control sheds requests (429/503). All visible in dashboards.

---

## Advanced: Debugging Under Load (500+ Users)

### Identifying Bottlenecks

When running 500+ concurrent users and seeing issues:

1. **Check Admission Layer First**
   - Go to Gateway + Admission dashboard
   - Look for "Admit rate" vs expected requests/sec
   - If admits < requests, gateway is rejecting load

2. **Identify Rejection Reason**
   - Not visible in dashboards directly
   - Must check logs at specific timestamp
   - Common reasons:
     - `tenant_tokens`: Quota exhausted
     - `no_eligible_pod`: Capacity full
     - `overcapacity`: System overloaded
     - `queue_full`: Request queue exceeded

3. **Correlate with VLLM Metrics**
   - TTFT (Time To First Token) — prefill latency
   - ITL (Inter-Token Latency) — decode speed
   - Prefix cache hits — reuse rate
   - Tokens in flight — load indicator

### Concurrency Limits (by GPU)

| GPU | Memory | Safe Users | Max Users |
|-----|--------|------------|-----------|
| A100 40GB | 40GB | 10 | 20-30 |
| A100 80GB | 80GB | 50 | 200-500 |
| H100 80GB | 80GB | 100 | 500+ |

**Key Factor**: KV cache grows ~1-3GB per concurrent request at 2K tokens

### Troubleshooting Guide

**Issue: Grafana Connection Refused**
- Solution: `kubectl -n monitoring port-forward svc/grafana 31495:80` (new terminal)
- Key: Explicit port-forward needed, not just SSH tunnel

**Issue: CUDA Graph Not Initialized**
- Solution: Re-run `bash setup/lambda_setup.sh`
- Check: `nvidia-smi` shows GPU detected

**Issue: Instance Spins Up Then Dies**
- Cause: SXM GPUs have capacity issues on Lambda
- Solution: Use PCIe GPU instead (a100_pcie_40gb)

**Issue: Grafana/Locust Won't Load**
- Check: SSH tunnel still running? Port forwarding active?
- Solution: Reconnect SSH, re-establish port-forward

---

## Homework Assignment (Week 8)

**Goal**: Profile error handling on real GPU cluster

**Tasks**:
1. Run all 10 dashboard tests on actual GPU
2. Identify 3+ different error types (beyond 429/503)
3. Add logging for each error type
4. Create 2-3 new Grafana panels for errors
5. Document concurrency degradation point
6. Recommend optimal GPU/replica count

**Deliverables**:
- Error categorization (10-15 types typical for LLM)
- Enhanced dashboards with error profiling
- Performance curves (latency vs concurrency)
- Hardware recommendation report

---

## Next Steps

1. ✅ Sync code to Lambda
2. ✅ SSH tunnel open
3. ✅ Run lambda_setup.sh
4. ✅ Run lambda_cluster.sh
5. ✅ Smoke test
6. 🚀 Start experiments (WebUI → REPL → Locust → Crew Flood)
7. 📊 Watch Grafana dashboards update in real-time
