# Class 9b — Rejection Testing Guide

**Purpose**: Trigger specific rejection modes to see them in Grafana dashboards

---

## Quick Start

```bash
# View Grafana while running tests
make grafana-open         # http://127.0.0.1:31495

# In another terminal, run rejection test
make test-rejection-admission-tokens

# Watch Grafana dashboard update in real-time
# → Success and failures dashboard
# → Gateway + admission dashboard
# → Check "Sheds by reason" for error breakdown
```

---

## Rejection Types & Triggers

### 1. ADMISSION: Tenant Token Limit (429)

**What happens**: Gateway receives request, admission control rejects it because tenant has used too many tokens.

**Trigger**:
```bash
make test-rejection-admission-tokens
```

**Expected in Grafana**:
- Success and failures dashboard:
  - `Shed/s` counter increases
  - `Sheds by reason`: `tenant_tokens 429` spike
  - Success ratio drops

- Gateway + admission dashboard:
  - `Admit rate` < `Requests/s`
  - `Sheds by reason`: Mostly yellow (`tenant_tokens`)

**Metrics affected**:
- `orch_admission_shed_tenant_tokens`
- `orch_admission_reject_rate`

---

### 2. ROUTER: No Eligible Pod (503)

**What happens**: Request reaches router, but no pod exists for the requested model (e.g., vision model with no local pod → overflow to Superlinked).

**Trigger**:
```bash
make test-rejection-router-no-pod
```

**Expected in Grafana**:
- Success and failures dashboard:
  - `Shed/s` increases
  - `Overflow/s` counter increases (goes to Superlinked)
  - `Sheds by reason`: `no_eligible_pod 503` spike

- Router dashboard:
  - `Overflow` counter increments
  - `Place by capability`: Shows "—" (no placement for vision)

- vLLM dashboard:
  - No change (request never reached local vLLM)

**Metrics affected**:
- `orch_router_overflow_count`
- `orch_placement_no_eligible_pod`

---

### 3. GATEWAY: High Concurrency (429/503)

**What happens**: 50 concurrent requests flood the gateway → admission control and router can't keep up → mixed 429/503 rejections.

**Trigger**:
```bash
make test-rejection-gateway-concurrency
```

**Expected in Grafana**:
- Success and failures dashboard:
  - RPS spikes to 40-50+
  - Shed/s also spikes
  - Success ratio drops (45-60%)
  - `Sheds by reason`: Both yellow (429) and green (503)

- Gateway + admission dashboard:
  - Gateway latency p95 increases (from 2ms to 6-10ms)
  - Completed counter shoots up
  - `Place by capability` drops

- KEDA dashboard:
  - Replica count might increase (if load is sustained)

**Metrics affected**:
- `orch_gateway_latency_seconds`
- `orch_tokens_in_flight`
- `orch_admission_queue_depth`

---

### 4. MOONCAKE: KV Cache Pressure

**What happens**: Large context requests fill GPU KV cache → memory pressure → 503 responses.

**Trigger**:
```bash
make test-rejection-mooncake-kv
```

**Expected in Grafana**:
- Mooncake (KV) dashboard:
  - `Hop tokens` increases
  - `Blocks in store` increases
  - Cache utilization climbs

- vLLM dashboard:
  - `GPU KV cache %` climbs toward 100%
  - `Waiting` queue increases (requests waiting for memory)

- Success and failures dashboard:
  - Shed/s increases (if KV allocation fails)

**Metrics affected**:
- `orch_kv_cache_bytes_used`
- `orch_kv_hop_tokens`
- `vllm_gpu_cache_usage_pct`

---

### 5. OVERFLOW: Superlinked Fallback

**What happens**: Request for non-local model → router sends to Superlinked → 200 but via fallback API.

**Trigger**:
```bash
make test-rejection-overflow
```

**Expected in Grafana**:
- Success and failures dashboard:
  - `Overflow/s` increases
  - Success ratio stays high (200 responses, but from Superlinked)
  - `Success vs shed vs overflow` graph shows overflow line

- Router dashboard:
  - `Overflow` counter increases

- Gateway + admission dashboard:
  - No shed increase (admission allowed it)
  - Latency might increase (Superlinked API slower)

**Metrics affected**:
- `orch_router_overflow_count`
- `orch_overflow_response_time`

---

## Running Tests

### Single Test

```bash
# Test admission 429 rejection
make test-rejection-admission-tokens

# Test router 503 rejection
make test-rejection-router-no-pod

# Test high concurrency
make test-rejection-gateway-concurrency

# Test KV cache pressure
make test-rejection-mooncake-kv

# Test overflow
make test-rejection-overflow
```

### All Tests

```bash
# Run all rejection tests in sequence
make test-rejection-all
```

### Customizing Tests

```bash
# Control concurrency and request count
NUM_REQUESTS=20 CONCURRENCY=10 make test-rejection-gateway-concurrency

# Very high concurrency (stress test)
NUM_REQUESTS=100 CONCURRENCY=50 make test-rejection-gateway-concurrency

# Single request with high tokens
NUM_REQUESTS=1 CONCURRENCY=1 MAX_TOKENS=4096 make test-rejection-admission-tokens
```

---

## Understanding Rejection Reasons

### HTTP Status Codes

| Code | Reason | Layer | Metric |
|------|--------|-------|--------|
| **200** | Success | Any | `success_total` |
| **429** | Quota exceeded | Admission | `admission_shed_tenant_tokens` |
| **429** | Queue full | Admission | `admission_shed_queue_full` |
| **503** | No eligible pod | Router | `placement_no_eligible_pod` |
| **503** | Overcapacity | Admission | `admission_shed_overcapacity` |

### How to Read Grafana "Sheds by reason"

**Tenant tokens 429** (yellow line):
- Tenant has exhausted their token budget
- Admission control is protecting quota
- Expected when: High concurrent requests with high `max_tokens`

**No eligible pod 503** (green line):
- No pod available for requested model
- Router cannot place request
- Overflow to Superlinked fallback
- Expected when: Vision/audio requests, or all pods busy

**Other reasons** (if visible):
- Red: `overcapacity` — System at maximum load
- Blue: `queue_full` — Request queue exhausted
- Orange: Other reasons (check logs for details)

---

## Workflow: Rejection Testing → Grafana Analysis

### Step 1: Start Observability
```bash
# Open Grafana
make grafana-open

# Keep open, watch "Success and failures" dashboard
```

### Step 2: Run Rejection Test
```bash
# In another terminal
make test-rejection-gateway-concurrency
```

### Step 3: Watch Grafana Update
- **Real-time metrics**: Dashboard updates every 5 seconds
- **Sheds by reason**: See which layer rejected requests
- **Latency panels**: Watch p50/p95 increase under load

### Step 4: Stop and Analyze
```bash
# Once test completes, check:
# 1. Success and failures — What failed?
# 2. Gateway + admission — Where rejected?
# 3. Router — What routed where?
# 4. KEDA — Did replicas scale?
# 5. vLLM — GPU metrics?
```

---

## Common Scenarios

### Scenario 1: "I want to see 429 errors"
```bash
# Send requests with high token demands
NUM_REQUESTS=10 CONCURRENCY=5 make test-rejection-admission-tokens

# Watch Grafana: "Sheds by reason" → yellow spike
```

### Scenario 2: "I want to see 503 errors"
```bash
# Request models with no local pods
make test-rejection-router-no-pod

# Watch Grafana: "Sheds by reason" → green spike, "Overflow/s" increases
```

### Scenario 3: "I want to see mixed 429+503"
```bash
# Hammer the system with 50 concurrent requests
NUM_REQUESTS=50 CONCURRENCY=50 make test-rejection-gateway-concurrency

# Watch Grafana: Both yellow and green spikes
```

### Scenario 4: "I want to see KV cache filling"
```bash
# Send large context requests
make test-rejection-mooncake-kv

# Watch Grafana Mooncake dashboard: Cache % climbs
```

### Scenario 5: "I want to see overflow happening"
```bash
# Request non-local models
make test-rejection-overflow

# Watch Grafana: "Overflow/s" increases, "Success vs shed vs overflow" shows blue line
```

---

## Combining with Locust

Run Locust + rejection test together to see how system handles mixed traffic:

```bash
# Terminal 1: Start Locust (200 users, steady traffic)
make locust-run

# Terminal 2: Meanwhile, run rejection test (adds more pressure)
make test-rejection-gateway-concurrency

# Terminal 3: Watch Grafana update with combined traffic
# Expect: Higher shed rate, longer latencies, more overflow
```

---

## Homework Assignment Ideas

1. **Run each rejection test, document expected Grafana metrics**
2. **Find the concurrency limit** where system switches from 200s to 429s
3. **Measure latency impact** of each rejection layer
4. **Create alert rules** in Grafana for each rejection type
5. **Compare rejection rates** with different GPU types (H100 vs A100)

---

## Troubleshooting

**Tests not generating 429/503?**
- Check: Cluster healthy? (`make lambda-status`)
- Check: Locust/crew_flood not already running
- Check: Replicas have capacity
- Try: Higher `CONCURRENCY` value

**Grafana metrics not updating?**
- Check: Dashboard refresh rate (5s default)
- Check: Prometheus scraping (`http://localhost:9090/targets`)
- Try: Manual refresh (Cmd+Shift+R)

**Tests timeout or fail?**
- Check: Gateway reachable? (`curl http://127.0.0.1:8080/metrics`)
- Check: .env file has correct ORCH_URL
- Try: Lower NUM_REQUESTS first

---

**Ready to trigger rejections!** 🎯

Use `make test-rejections-help` for quick reference.
