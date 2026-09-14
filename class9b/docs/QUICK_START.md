# Class 9b Quick Start Guide

**Lambda Instance**: 193.122.152.87 (gpu_1x_a100_sxm4)

---

## 🚀 Phase 1: Initial Setup (5 min)

```bash
cd /Users/nakulmanchanda/dev/class-code/class9b

# Create venv + install deps
make setup
```

---

## 🔌 Phase 2: Lambda Cluster (15 min)

**Terminal 1 (Keep Open):**
```bash
# Sync code to Lambda
make sync

# SSH tunnel (DO NOT CLOSE THIS TERMINAL)
make ssh
```

**Terminal 2 (Same SSH prompt):**
```bash
# Step 3: Install vLLM + models
bash setup/lambda_setup.sh

# Step 4: Install k3s + HAMi + KEDA + Mooncake
bash setup/lambda_cluster.sh      # ~5-7 minutes

# Step 5: Verify cluster
make lambda-status

# Step 6: Smoke test (should pass)
make smoke
```

---

## 💬 Phase 3: Test the System

**Terminal 3 (New Mac terminal, not SSH):**

### 3a. WebUI Chat
```bash
make webui-open   # Opens http://127.0.0.1:30030
```
- Pick "text" or "vision" model
- Send a message
- See response in real-time

### 3b. REPL Traffic
```bash
make repl
```

In REPL prompt, try:
```
text Write one sentence about a GPU.
vision What color is this?
audio Transcribe: hello from class 9b.
hop Write one sentence about a GPU.   # Test KV cache hop
evict                                  # Clear cache
metrics                                # Show metrics
profile                                # Show profile
quit                                   # Exit
```

---

## 📊 Phase 4: Day 2 - Observability (5 min)

**Terminal 2a (Lambda SSH):**
```bash
# Step 22: Setup Grafana
bash setup/day2_observability.sh

# Step 23: Get admin password (output shows it, save it)
make grafana-password
```

**Terminal 2b (Lambda SSH - NEW terminal):**
```bash
# ⚠️ CRITICAL: Port-forward Grafana (keep running)
kubectl -n monitoring port-forward svc/grafana 31495:80
```

**Terminal 3 (Mac):**
```bash
# Step 24: Open Grafana
make grafana-open

# Login: admin / <password from step 23>
# Browse dashboards: Class 9b / Cluster, etc.
```

---

## 📈 Phase 5: Load Testing

**Terminal 3 (Mac):**
```bash
# Step 25-26: Install and run Locust
make locust-run
```

**Terminal 4 (New Mac terminal):**
```bash
# Step 27: Open Locust UI
make locust-open

# Step 28: Set users=4, spawn_rate=2, click "Start"
# Watch Grafana update every 5 seconds
# Run for 1+ minute to populate rate() panels
```

---

## 🌊 Phase 6: Crew Flood

**Terminal 3 (Mac):**
```bash
# Stop Locust first (Ctrl+C)
# Then run crew_flood
make crew-flood    # 48 rounds, 8 workers

# Step 30: View dashboards in Grafana
make dashboards-list
```

---

## 🔗 Key URLs

| Service | URL | When Available |
|---------|-----|-----------------|
| WebUI | http://127.0.0.1:30030 | After Step 4 (lambda_cluster.sh) |
| Gateway | http://127.0.0.1:8080 | After Step 4 |
| Grafana | http://127.0.0.1:31495 | After Step 22 (day2_observability.sh) |
| Locust | http://127.0.0.1:8089 | After running `make locust-run` |

---

## 📋 Important Commands

```bash
# Setup & status
make help                   # Full Makefile help
make setup                  # Create venv + deps
make sync                   # Sync to Lambda
make ssh                    # SSH tunnel (keep open!)
make lambda-status          # Check cluster health
make smoke                  # Smoke test

# Testing
make webui-open             # Open WebUI browser
make repl                   # Interactive REPL
make repl-demo              # Show REPL commands

# Observability
make observe                # Setup Grafana (on Lambda)
make grafana-open           # Open Grafana
make grafana-password       # Show Grafana password
make dashboards-list        # List all dashboards

# Load testing
make locust-run             # Run Locust
make locust-open            # Open Locust UI
make crew-flood             # Run crew_flood
```

---

## ⚠️ Critical Rules

1. **SSH Tunnel** (Terminal 1): Keep `make ssh` running throughout entire lab
   - If it closes, all 127.0.0.1 URLs break
   - Don't Ctrl+C it, just leave it open

2. **Concurrent Requests**: Max ~10 users
   - Beyond 10: system sheds requests (429/503 errors)
   - This is by design (admission control)
   - H100 can handle more

3. **Memory**: ~40GB total, ~15GB per replica
   - Model + KV cache = ~6-7GB
   - Safe for 2-10 concurrent requests

4. **Metrics**: Watch Grafana update every 5 seconds
   - Only updates while traffic is flowing
   - Run tests for 1+ minute for good data

---

## 🐛 If Something Breaks

**WebUI not loading?**
- Check SSH tunnel (Terminal 1) is still open
- Check `make lambda-status` shows READY replicas

**Requests failing with 429?**
- This is admission control (system shedding load)
- Reduce concurrent users in Locust
- Normal behavior when overloaded

**Grafana not loading?**
- Check `make observe` was run on Lambda
- Wait 30 seconds, it takes time to start
- Check Grafana password is correct

**Locust says "Connection refused"?**
- Make sure `make ssh` tunnel is still open
- Make sure gateway pod is READY (`make lambda-status`)

---

## 📚 Related Files

- **README.md** — Full step-by-step instructions
- **INSTRUCTOR_TRANSCRIPT.md** — Detailed architecture & Q&A
- **Makefile** — All commands with help text
- **.env** — Configuration (Lambda IP, models, etc.)

---

## 🎯 Expected Outcome

By the end of this lab, you will have:

✅ Running vLLM cluster on Lambda  
✅ Gateway + Router orchestration  
✅ WebUI for interactive chat  
✅ REPL for programmatic traffic  
✅ Locust for load testing  
✅ Grafana dashboards showing:
  - Cluster health
  - Request success/failure rates
  - Gateway admission control
  - Router decisions
  - KV cache management
  - vLLM metrics
  - Pod auto-scaling

---

## 📞 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Ports not reachable | Check SSH tunnel is open |
| Cluster not ready | Run `make lambda-status`, wait for READY |
| Models not loading | Check disk space on Lambda (80GB should be fine) |
| Out of memory | Reduce concurrent requests to 5-7 |
| Grafana metrics flat | Ensure traffic is flowing, wait 1+ min |

---

**Start**: `cd class9b && make setup && make sync && make ssh`  
**Next**: Follow Phase 2+ in new terminals  
**Questions**: See INSTRUCTOR_TRANSCRIPT.md or README.md
