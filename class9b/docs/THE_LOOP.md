# Class 9b — The Loop in Thirty Seconds

**Six steps to run the lab. Everything red, in a fixed order, is easier than anything red in a random one.**

---

## The Six-Step Loop

### 1️⃣ **Sync, Then Open the Tunnel**
```bash
cd ~/class9b
git pull origin main
bash setup/ssh.sh  # Leave this terminal open
```
**Result:** Cluster accessible at 127.0.0.1

---

### 2️⃣ **Chat in the Browser**
```bash
# WebUI on :30030
# Try text first
# Then vision with an actual image attached
```
**Gateway decision:** Text → local vLLM, Vision → Superlinked

---

### 3️⃣ **Drive It from the REPL**
```bash
make repl

lab> text Hello world
lab> vision Send me an image URL or attach one
lab> audio This will refuse (no local model)
lab> hop Write one sentence about a GPU.  ← Tests KV hop
lab> evict Forget everything and start fresh         ← Tests cache eviction
```
**Gateway + Router:** Placement, overflow, KV transfers, cache management

---

### 4️⃣ **Bring Up the Observability Stack**
```bash
# Prometheus on :9090
# Grafana on :31495
# Default: admin / (password from secret)
make observability
```
**Dashboards:** Success/Failures → Cluster → Gateway/Router → KEDA/HAMi/Mooncake/vLLM

---

### 5️⃣ **Put It Under Load**
```bash
# Locust on :8089
# Four users, ramp 2
# Watch the policy engage, not the model melt
make locust
```
**Metrics:** RPS, latency, failures (429, 503, 529)

---

### 6️⃣ **Read the Dashboards in Order**
1. **Success and Failures** → Requests vs completed vs shed
2. **Cluster** → Is the hardware what you think it is?
3. **Gateway and Router** → Which decision produced that outcome?
4. **Per-tool boards** → KEDA replicas, HAMi slices, Mooncake transfers, vLLM cache

---

## The Core Insight

> **A serving system is five questions in five places. Everything else — every tool name on every slide today — is an implementation detail of one of them.**

**The five questions:**
1. 🔴 **Northbound:** Should this request leave our cluster?
2. 🟡 **Gateway:** Do we admit it, and which pod serves it?
3. 🟢 **KV Transfer:** Where does cached state live?
4. 🔵 **Device:** How much GPU may this pod see?
5. 🟣 **Scaling:** How many pods exist?

---

## What Each Step Tests

| Step | Tests | Validates |
|------|-------|-----------|
| 1 | Connectivity | Cluster reachable |
| 2 | Gateway + overflow | Text→local, vision→Superlinked |
| 3 | Router + KV + cache | Placement, hops, eviction |
| 4 | Observability | Metrics pipeline working |
| 5 | Scaling + policy | KEDA scaling, admission control |
| 6 | End-to-end | All five planes working together |

---

## When Something Breaks

**Use the same order to diagnose:**

| Symptom | Step to Check | Plane |
|---------|---------------|-------|
| Can't connect | Step 1 | (Connectivity) |
| Request rejected (429) | Step 3, REPL | Gateway (admission) |
| Request gets 503 | Step 3, REPL | Gateway (no eligible pod) |
| No KV hop | Step 3, `lab> hop` | KV Transfer (Mooncake) |
| Wrong pod picked | Step 6, Grafana | Gateway + Router |
| Pod count wrong | Step 6, Grafana | Scaling (KEDA) |

---

## Running All Six Steps (Fastest Path)

```bash
# Terminal 1: SSH tunnel (leave open)
bash setup/ssh.sh

# Terminal 2: Grafana port-forward
kubectl port-forward svc/grafana 31495:80

# Terminal 3: REPL
make repl
lab> hop Write one sentence about a GPU.

# Terminal 4: Locust (after REPL works)
make locust

# Browser: WebUI on :30030, Grafana on :31495
```

---

## Study Checklist

- [ ] I can explain what each step tests
- [ ] I know which dashboard answers which question
- [ ] I can map a symptom to a plane
- [ ] I can run all six steps in order without looking at docs
- [ ] I understand why the order matters (builds up each plane)

---

**That's the loop. Everything else is implementation detail.** 🎯

When you can run all six steps and understand why each one matters, you understand distributed LLM orchestration.
