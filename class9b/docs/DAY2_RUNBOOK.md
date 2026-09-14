# Class 9b — Day 2: Grafana Walkthrough

**Date**: Sep 13, 2026  
**Lambda**: 193.122.152.87  

---

## 🔗 Day 2 URLs (Mac, Step 2 tunnel must stay open)

**Only access via 127.0.0.1 on Mac**

| Service | URL | Login |
|---------|-----|-------|
| WebUI | http://127.0.0.1:30030 | (no login) |
| Grafana | http://127.0.0.1:31495 | admin / (password below) |
| Locust UI | http://127.0.0.1:8089 | (no login, after Step 26) |
| Gateway | http://127.0.0.1:8080 | (backend) |

---

## 🚀 Generate Load First

Before walking dashboards, generate some load:

### Option 1: Locust (UI-driven)
```bash
# Terminal 3 (Mac)
locust -f app/locustfile.py --host http://127.0.0.1:8080

# Open: http://127.0.0.1:8089
# Set: users=4, spawn_rate=2
# Click: Start
# Let it run 1+ minute (for rate() panels to populate)
```

### Option 2: Crew Flood (programmatic)
```bash
# Terminal 3 (Mac)
ORCH_URL=http://127.0.0.1:8080/v1 python -m app.crew_flood --rounds 48 --workers 8
```

### Option 3: WebUI (manual)
```bash
# Terminal 3 (Mac)
open http://127.0.0.1:30030
# Send messages, watch metrics update in real-time
```

---

## 📊 Grafana Dashboards: Walkthrough Order

Open Grafana at http://127.0.0.1:31495  
Login: `admin` / `MGpRVMGVLT4SEzgo45KT13eaizmQ9QvPvgU1fQv8`

**Walk these dashboards in order (while traffic is flowing):**

### 1️⃣ **Cluster**
- **Metrics**: node-exporter CPU/mem, kube-state pods, cAdvisor
- **Focus**: GPU metrics (DCGM), node health
- **Look for**: 
  - CPU/memory utilization
  - GPU temperature
  - Pod status (READY/NOT_READY)

### 2️⃣ **Success and Failures**
- **Metrics**: Requests vs completed vs shed (429/503) vs overflow
- **Focus**: Request lifecycle
- **Look for**:
  - Requests per second (RPS)
  - Completion rate
  - Shedding by system (admission control)
  - Overflow to Superlinked
- **Normal**: Some 429/503 when under load (system protecting itself)

### 3️⃣ **Overview (metrics.py)**
- **Metrics**: `orch_*` from `GET /metrics`
- **Focus**: Gateway metrics directly
- **Look for**:
  - `orch_requests_total`
  - `orch_request_duration_*`
  - `orch_tokens_*`

### 4️⃣ **Gateway + Admission**
- **Metrics**: admit, shed, place, gateway-stage histograms
- **Focus**: Admission control behavior
- **Look for**:
  - Admit rate (how many accepted)
  - Shed rate (how many rejected)
  - Placement decisions
  - Histogram latencies (p50, p95, p99)

### 5️⃣ **Router**
- **Metrics**: pick / sticky / unknown snapshot / overflow / planner / KV hop
- **Focus**: Routing decisions
- **Look for**:
  - Pick: Initial model selection
  - Sticky: Staying on same model
  - Unknown: Unidentified request type
  - Overflow: Sent to Superlinked
  - Planner: Routing logic decision
  - KV hop: Prefill→Decode cache transfer

### 6️⃣ **KEDA**
- **Metrics**: scaler value/active vs kube replicas vs `orch_tokens_in_flight`
- **Focus**: Auto-scaling
- **Look for**:
  - Scaler value: What KEDA sees
  - Replica count: Current pods
  - Tokens in flight: Load indicator
  - Scaling up/down events

### 7️⃣ **HAMi (GPU Slicing)**
- **Metrics**: device memory/cores vs `nvidia.com/gpumem` slice limits
- **Focus**: GPU resource allocation
- **Look for**:
  - Memory per slice
  - Core allocation
  - Slice limits enforced
  - Fragmentation (if any)

### 8️⃣ **Mooncake (KV Cache)**
- **Metrics**: hops / blocks / hop tokens vs `orch_kv_transfer_*`
- **Focus**: KV cache management
- **Look for**:
  - Hops: Prefill→Decode transfers
  - Blocks: Cache blocks used
  - Transfer latency
  - Normal**: 0 hops until Step 16 `hop` command
  - Normal**: 0 evictions until Step 17 `evict` command

### 9️⃣ **Pods and Replicas**
- **Metrics**: kube-state-metrics + `orch_replica_*`
- **Focus**: Pod lifecycle
- **Look for**:
  - Pod count (should match KEDA scaler)
  - Pod restarts (should be 0)
  - Ready vs NotReady

### 🔟 **vLLM**
- **Metrics**: gpu_cache, running/waiting, TTFT / ITL / e2e, prefix cache
- **Focus**: Model inference stats
- **Look for**:
  - GPU cache utilization
  - Requests running vs waiting
  - TTFT: Time To First Token (prefill latency)
  - ITL: Inter-Token Latency (decode speed)
  - E2E: End-to-end latency
  - Prefix cache hits

---

## 🔄 Special Test: KV Eviction

**Prerequisite**: REPL running (from Step 12)

### Step 1: Flood until slice is hot
```bash
# In Grafana, watch Mooncake dashboard
# Run crew_flood or Locust to generate load
# Watch gpu_cache reach ~80-90% utilization
```

### Step 2: Trigger KV hop (Step 16)
```bash
# In REPL terminal (from Step 12):
hop Write one sentence about a GPU.

# In Grafana Mooncake dashboard:
# - Watch "hops" counter increment
# - Watch "hop tokens" increase
# - Check "orch_kv_transfer_*" latency
```

### Step 3: Evict and watch BlockRemoved
```bash
# In REPL terminal:
evict

# In Grafana Mooncake dashboard:
# - Watch "evictions" counter increment
# - Look for BlockRemoved in logs
# - Router should NOT route on ghost cache
```

**Critical**: If Router routes on ghost cache after eviction, cache consistency is broken!

---

## 🔍 Advanced: Prometheus Metrics

Access raw Prometheus metrics:

```bash
# Forward Prometheus (on Lambda)
kubectl -n monitoring port-forward svc/prometheus-server 9090:80

# Query Prometheus: http://localhost:9090
# Example queries:
#   rate(orch_requests_total[1m])      → RPS
#   orch_kv_transfer_duration_seconds  → KV hop latency
#   node_cpu_seconds_total             → CPU usage
```

---

## 🖥️ Grafana Setup (Day 2 Step 22)

Already done if you ran `make observe` or `bash setup/day2_observability.sh`

```bash
# On Lambda (from Step 2 SSH):
bash setup/day2_observability.sh

# Output shows:
# NAME      TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
# grafana   NodePort   10.43.104.30   <none>        80:31280/TCP   22s
# MGpRVMGVLT4SEzgo45KT13eaizmQ9QvPvgU1fQv8  ← Password

# **IMPORTANT: On Lambda, run explicit port-forward in separate terminal:**
kubectl -n monitoring port-forward svc/grafana 31495:80

# Port forwarded as: 127.0.0.1:31495
```

### Get Password if Forgotten
```bash
kubectl -n monitoring get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

---

## 📋 Dashboard Checklist

Use this while walking dashboards:

- [ ] **Cluster** — CPU/mem/GPU look healthy?
- [ ] **Success/Failures** — How many requests succeeded vs shed?
- [ ] **Overview** — Can you see `orch_*` metrics flowing?
- [ ] **Gateway+Admission** — Is admission working (rejecting load)?
- [ ] **Router** — Are requests routing to correct models?
- [ ] **KEDA** — Is replica count tracking load?
- [ ] **HAMi** — Are slices allocated and enforced?
- [ ] **Mooncake** — Any KV hops/evictions happening?
- [ ] **Pods** — All pods READY?
- [ ] **vLLM** — TTFT/ITL/E2E latencies reasonable?

---

## 🐛 Troubleshooting Day 2

### Grafana not loading?
**Most likely cause:** Missing explicit port-forward

```bash
# On Lambda, run this in a NEW terminal:
kubectl -n monitoring port-forward svc/grafana 31495:80

# Keep it running, then on Mac:
open http://127.0.0.1:31495
```

If still not working:
```bash
# Check if Grafana pod is running
kubectl -n monitoring get pods

# Check if service exists
kubectl -n monitoring get svc grafana

# Restart if needed
kubectl -n monitoring delete pod -l app=grafana
```

### Dashboards empty (no data)?
- Ensure traffic is flowing (Locust/crew_flood running)
- Wait 30+ seconds for metrics to scrape
- Check Prometheus is running: `kubectl get svc -n monitoring`

### Can't access Grafana from Mac?
- Check SSH tunnel is still open: `make ssh` in Terminal 1
- Check port forwarding: `lsof -i :31495` (should show sshd)

### Metrics look flat?
- Ensure load is running (watch Locust/crew_flood terminal)
- Check Prometheus scrape targets: http://localhost:9090/targets

---

## 📚 Reference: Makefile Commands

```bash
# Setup observability
make observe            # Step 22: bash setup/day2_observability.sh

# Open Grafana
make grafana-open       # Opens http://127.0.0.1:31495

# Get password
make grafana-password   # Shows kubectl command to retrieve it

# List dashboards to view
make dashboards-list    # Shows 10 dashboards in order

# Generate load
make locust-run         # Locust UI at :8089
make crew-flood         # Programmatic load
make webui-open         # Manual WebUI chat
```

---

## 🎯 Expected Observations

**During 4-user Locust run (1+ minute):**

- ✅ RPS: 2-6 requests/sec
- ✅ Success rate: 70-95% (some 429 normal)
- ✅ TTFT: 0.1-0.5s (prefill)
- ✅ ITL: 0.02-0.1s (decode)
- ✅ Replica count: 1-2 pods
- ✅ GPU cache: 40-80% utilization
- ✅ CPU: 20-40% per pod
- ✅ No BlockRemoved until evict

---

## 📞 Q&A

**Q**: Why are some requests showing 429?  
**A**: Admission control shedding load (by design). Protects system.

**Q**: Why is KEDA only showing 1 replica?  
**A**: Low concurrency (4 users). KEDA scales based on tokens in flight.

**Q**: What if all requests fail?  
**A**: Check cluster is READY (`make lambda-status`), SSH tunnel is open.

**Q**: Can I add more dashboards?  
**A**: Yes, edit observability YAML files, but current 10 cover everything.

---

## 🚀 Next Steps After Day 2

1. ✅ Walk all 10 dashboards (30 min)
2. ✅ Run KV eviction test (10 min)
3. ✅ Compare with previous class9 metrics
4. ✅ Document findings
5. 🔜 Explore edge cases (10+ users, large models, etc.)

---

**Grafana Login**: admin / MGpRVMGVLT4SEzgo45KT13eaizmQ9QvPvgU1fQv8  
**Prometheus**: http://localhost:9090 (after port-forward)  
**Lambda**: ubuntu@193.122.152.87  
**Status**: ✅ Ready for Day 2 walkthrough
