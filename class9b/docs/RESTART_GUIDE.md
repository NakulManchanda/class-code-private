# Class 9b — Quick Restart Guide

**For next session — minimal steps to get everything running.**

---

## 🚀 **Terminal Setup (4 terminals on Mac)**

### Terminal 1: SSH Tunnel (KEEP OPEN)
```bash
cd /Users/nakulmanchanda/dev/class-code/class9b
make ssh
```
**Status**: Should show `ubuntu@193-122-152-87:~/class9b$`  
**⚠️ KEEP THIS OPEN** — All port forwarding depends on it

---

### Terminal 2a: Grafana Port-Forward (KEEP OPEN)
```bash
# SSH into Lambda from Terminal 1 output, or:
ssh ubuntu@193.122.152.87

# Then run:
kubectl -n monitoring port-forward svc/grafana 31495:80
```
**Status**: Should show `Forwarding from 127.0.0.1:31495 -> 3000`  
**⚠️ KEEP THIS OPEN** — Grafana access depends on it

---

### Terminal 2b: Start Locust
```bash
# Back in Mac terminal (class9b directory)
make locust-run
```
**Status**: Should show `Locust web interface now available at http://0.0.0.0:8089`

---

### Terminal 3: Open URLs
```bash
# Option 1: Open Locust UI
make locust-open
# or: open http://127.0.0.1:8089

# Option 2: Open Grafana
make grafana-open
# or: open http://127.0.0.1:31495

# Option 3: Open WebUI
make webui-open
# or: open http://127.0.0.1:30030
```

---

## 🔐 **Credentials & URLs**

| Service | URL | Login |
|---------|-----|-------|
| **WebUI** | http://127.0.0.1:30030 | (no login) |
| **Grafana** | http://127.0.0.1:31495 | admin / `MGpRVMGVLT4SEzgo45KT13eaizmQ9QvPvgU1fQv8` |
| **Locust** | http://127.0.0.1:8089 | (no login) |
| **Gateway** | http://127.0.0.1:8080 | (backend only) |

---

## 📋 **Load Testing Quick Start**

### Generate Load (Locust)
1. Open http://127.0.0.1:8089
2. Set **Number of users**: 4-10 (max safe)
3. Set **Spawn rate**: 2
4. Click **Start**
5. Watch Grafana update every 5 seconds

### Generate Load (Crew Flood)
```bash
make crew-flood    # Runs 48 rounds × 8 workers
```

### Generate Load (REPL)
```bash
make repl

# In REPL prompt:
text Write one sentence about a GPU.
vision What color is this?
audio Transcribe: hello from class 9b.
hop Write one sentence about a GPU.
evict
quit
```

---

## 📊 **Grafana Dashboard Order**

While traffic is flowing, walk these **10 dashboards**:

1. **Cluster** — Node/GPU health
2. **Success and failures** — RPS, shedding, overflow
3. **Overview (metrics.py)** — orch_* metrics
4. **Gateway + admission** — Admission control
5. **Router** — Model routing
6. **KEDA** — Auto-scaling
7. **HAMi** — GPU slicing
8. **Mooncake** — KV cache
9. **Pods and replicas** — Pod health
10. **vLLM** — TTFT/ITL/cache

---

## ⚠️ **Critical Remember**

| Item | Action |
|------|--------|
| **SSH Tunnel (T1)** | Keep `make ssh` running all session |
| **Grafana Forward (T2a)** | Keep `kubectl port-forward` running |
| **Max Users** | 10 concurrent max (40GB machine) |
| **Grafana Refresh** | Updates every 5 seconds when traffic flows |
| **Port Forwarding** | Explicit `kubectl port-forward` needed for Grafana |

---

## 🆘 **If Grafana Won't Load**

1. Check Terminal 2a is still running (kubectl port-forward)
2. Check Terminal 1 is still running (SSH tunnel)
3. Try: `kubectl -n monitoring port-forward svc/grafana 31495:80` on Lambda again
4. Refresh browser (Cmd+Shift+R)

---

## ✅ **Checklist Before Starting**

- [ ] Terminal 1: `make ssh` running (shows Lambda prompt)
- [ ] Terminal 2a: `kubectl port-forward` running (shows "Forwarding from 127.0.0.1:31495")
- [ ] Terminal 2b: `make locust-run` running (shows Locust ready)
- [ ] Verify cluster: `kubectl get pods` shows deployments READY
- [ ] Open URLs: WebUI, Grafana, Locust all accessible

---

## 📚 **Full Documentation**

- **QUICK_START.md** — Full 7-phase walkthrough
- **README.md** — Detailed 32-step runbook
- **DAY2_RUNBOOK.md** — Dashboard guide + troubleshooting
- **INSTRUCTOR_TRANSCRIPT.md** — Architecture notes
- **Makefile** — All commands (`make help`)

---

## 🎯 **One-Line Quick Start**

```bash
cd /Users/nakulmanchanda/dev/class-code/class9b
# Terminal 1:
make ssh

# Terminal 2a (on Lambda):
kubectl -n monitoring port-forward svc/grafana 31495:80

# Terminal 2b (on Mac):
make locust-run

# Terminal 3 (on Mac):
make grafana-open    # and/or
make locust-open     # and/or
make webui-open
```

---

**Lambda IP**: 193.122.152.87  
**Status**: ✅ Cluster running, ready to test  
**Last Updated**: Sep 13, 2026
