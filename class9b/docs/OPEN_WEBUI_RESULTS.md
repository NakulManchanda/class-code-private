# Class 9b — Open WebUI Session Results

**Purpose:** Capture and analyze real user interactions through Open WebUI

---

## 📋 How to Capture Open WebUI Metrics

### Method 1: REPL Board (Routing History)
```bash
# After Open WebUI requests have been sent
make repl
lab> board    # Shows last 12 requests with routing decisions
```

### Method 2: REPL Metrics (All Prometheus metrics)
```bash
lab> metrics | grep "orch_" > webui_metrics.txt
# Save to file for analysis
```

### Method 3: Grafana Export
1. Open http://127.0.0.1:31495 (Grafana)
2. Go to: Success and Failures dashboard
3. Click: Export (top right)
4. Download JSON for historical analysis

---

## 🎯 What to Look For

### From Open WebUI Usage

**Each conversation through Open WebUI should show:**

```
Request 1: "Write a haiku about GPUs"
  ↓ Captured in: lab> board

Request 2: "Help me study vocabulary"
  ↓ Captured in: lab> board

Request 3: Follow-up in same conversation
  ↓ Captured in: lab> board
```

### Metrics to Extract

Run after Open WebUI testing:

```bash
lab> metrics | grep -E "orch_requests_total|orch_completed_total|orch_pick_total|orch_kv_transfer"

Expected output:
orch_requests_total 3                    # 3 requests from Open WebUI
orch_completed_total 3                   # All succeeded
orch_pick_total 3                        # 3 routing decisions
orch_kv_transfer_total 2 or 3            # KV hops during multi-turn
orch_kv_transfer_tokens 47               # Total tokens cached
```

---

## 📊 Sample Open WebUI Test Results

**Test scenario:** 3 conversations, 2-3 turns each

### Conversation 1: GPU Haiku
```
User prompt:     "Write a haiku about GPUs"
Model:           text (Qwen2.5-3B)
Tokens:          ~37 input + 17 output = 54 total
Latency:         ~1.2 seconds
Route:           Gateway → text-0 (prefill) → text-0 (decode)
KV hop:          1 (prefill→decode via Mooncake)
Status:          200 (success)
```

### Conversation 2: Vocabulary Study (Multi-turn)

**Turn 1:**
```
User prompt:     "Help me study vocabulary"
Model:           text
Tokens:          ~25 input + 50 output = 75 total
Latency:         ~1.3 seconds
Route:           Gateway → text-0 (prefill) → text-0 (decode)
KV hop:          1
Status:          200
```

**Turn 2:**
```
User prompt:     "Give me another example"
Model:           text
Tokens:          ~18 input + 45 output = 63 total
Latency:         ~1.1 seconds
Route:           Gateway → text-0 (prefill) → text-0 (decode)
KV hop:          1 (reuses previous context via Mooncake!)
Status:          200
```

### Conversation 3: Mixed

**Turn 1 (Text):**
```
Prompt:          "What is a GPU?"
Tokens:          45
Latency:         ~1.2s
Route:           text-0
```

**Turn 2 (Vision):**
```
Prompt:          [Upload GPU image] + "Describe this"
Tokens:          ~60 (image tokens + text)
Latency:         ~2.1s (vision is slower)
Route:           vision-0
```

---

## 📈 Expected Aggregate Metrics

**After 3 conversations, 6-7 turns total:**

```
From lab> metrics:

orch_requests_total:              7
orch_completed_total:             7
orch_pick_total:                  7
orch_place_total{capability="text"}: 5
orch_place_total{capability="vision"}: 2
orch_kv_transfer_total:           5 or 6    (multi-turn conversations)
orch_kv_transfer_tokens:          ~350      (total tokens cached)
orch_overflow_total:              0         (no overflows needed)
orch_shed_total:                  0         (no rejections)

orch_request_duration_seconds_sum{stage="e2e"}: ~8.0s
orch_request_duration_seconds_count{stage="e2e"}: 7
orch_request_duration_seconds_average: ~1.14s per request
```

---

## 🎯 How to Capture Live

**While using Open WebUI:**

### Terminal 1: Watch Metrics in Real-Time
```bash
make repl

# In REPL, run this repeatedly
lab> metrics | grep "orch_requests\|orch_completed\|orch_kv_transfer" | head -5
```

### Terminal 2: Watch Grafana
Open http://127.0.0.1:31495 → Success and Failures dashboard
- Watch "Requests/s" chart spike as you use Open WebUI
- Watch "Success/s" chart rise

### Terminal 3: Capture Board
```bash
make repl
lab> board    # After each request, see routing history

Example output:
id             cap    pod / phase                 via      code         why
14ab3c7d...    text   text-0 both                 local    200          BIND text → text  PLACE text-0
2f8c4d9e...    text   text-0 both                 local    200          BIND text → text  PLACE text-0  [kv_hop=1]
```

---

## 📊 Grafana Dashboards to Watch

### Dashboard 1: Success and Failures
```
During Open WebUI usage:
- Requests/s line: Jumps when you type
- Success/s line: Jumps when responses received
- Failures/s line: Should stay at zero
- Shed/s line: Should stay at zero (unless overloaded)
```

### Dashboard 2: Mooncake KV
```
During multi-turn conversations:
- Hops counter: Increments with each KV hop
- Hop tokens: Increases (shows tokens cached)
- Blocks in store: Grows as more conversations cached
- Router KV transfers: Activity visible on chart
```

### Dashboard 3: Cluster
```
- Pod health: All green (healthy)
- Replica count: May increase if load high
- Active requests per pod: Shows distribution
```

---

## 🔍 Analysis Template

**After Open WebUI testing, fill this out:**

```
TEST DATE: ___________
DURATION: ___________
CONVERSATIONS: _______
TOTAL TURNS: _________

METRICS CAPTURED:
  orch_requests_total: _______
  orch_completed_total: _______
  orch_kv_transfer_total: _______
  orch_kv_transfer_tokens: _______
  orch_shed_total: _______
  orch_overflow_total: _______

LATENCIES:
  Average P50: _______ms
  Average P95: _______ms
  Min latency: _______ms
  Max latency: _______ms

MODELS USED:
  Text model requests: _______
  Vision model requests: _______
  
FAILURES:
  Total failures: _______
  Rejection rate: _______

KV CACHE EFFICIENCY:
  Total KV hops: _______
  Total tokens cached: _______
  Average tokens/hop: _______
```

---

## 🎯 Commands to Run Now

```bash
# 1. Start fresh REPL
make repl

# 2. Use Open WebUI normally (3+ conversations, 2+ turns each)

# 3. Capture board (routing history)
lab> board

# 4. Capture metrics
lab> metrics | head -50

# 5. Check profile (latency breakdown)
lab> profile

# 6. Export results
lab> metrics > webui_test_results.txt
```

---

## 📱 What Each Metric Tells You

| Metric | Meaning | Ideal Value |
|--------|---------|------------|
| `orch_requests_total` | Requests processed | High (more usage) |
| `orch_completed_total` | Successful completions | Equal to requests |
| `orch_kv_transfer_total` | KV hops performed | High for multi-turn |
| `orch_kv_transfer_tokens` | Tokens cached | High (more efficiency) |
| `orch_shed_total` | Rejections | Zero (no overload) |
| `orch_overflow_total` | Overflows | Low (prefer local) |

---

## 🚀 Next Steps

1. **Use Open WebUI** naturally (chat, ask questions, multi-turn)
2. **Capture metrics** after each session
3. **Compare with Locust** load test results
4. **Analyze KV efficiency** (cached tokens vs total tokens)
5. **Document results** in this template

---

## 📊 Example Complete Session Report

**Test: Multi-turn Chat via Open WebUI**

```
Date: Sep 13, 2026
Duration: 15 minutes
Conversations: 3
Total turns: 8

Metrics:
  Requests: 8
  Completed: 8 (100%)
  KV transfers: 6
  KV tokens: 420
  Sheds: 0
  Overflows: 0

Latencies:
  P50: 1.1s
  P95: 2.1s
  Min: 0.9s
  Max: 2.8s

Results:
  ✅ All requests succeeded
  ✅ 420 tokens cached via KV hops
  ✅ No admission control rejections
  ✅ No overflows to Superlinked
  ✅ Smooth user experience
```

---

**Ready to test? Start with `make repl` and use Open WebUI naturally!** 🚀
