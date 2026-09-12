# Class 9 Runbook Progress

**Status:** Steps 1-10 Complete ✅ | Steps 11-15 Ready (Manual) | Steps 16-25 Pending

---

## ✅ Completed Steps

### Laptop Setup (Steps 1-9)
- [x] **Step 1:** `cd class-code/class9`
- [x] **Step 2:** Create venv
- [x] **Step 3:** Activate venv
- [x] **Step 4:** Install dependencies
- [x] **Step 5:** Run pytest tests → **39 passed, 1 skipped**
- [x] **Step 6:** List fakeworker behaviors
- [x] **Step 7-9:** Fakeworker tests available
  - `fleet-soak` — tests sustained load
  - `tenant-429-stays` — tests tenant error handling
  - `overflow-on-503` — tests overflow routing

### Lambda Cluster Sync (Step 10)
- [x] **Step 10:** Code synced to `ubuntu@129.213.22.135:~/class9/`
- [x] Created `.env` file with Lambda IP and SSH key

---

## 🚀 Next: Manual Steps on Lambda (Steps 11-15)

Open a new Mac terminal and run:

```bash
cd /Users/nakulmanchanda/dev/class-code/class9
make ssh
```

Once connected, **first time only** - set up your environment:

```bash
# One-time setup: configure ~/.bashrc for convenience
bash setup/setup_bashrc.sh

# Apply changes to current session
source ~/.bashrc
```

This will:
- Auto-cd to ~/class9 on future logins
- Auto-activate Python venv on future logins
- Add helpful aliases (class9-status, class9-logs, class9-pods)

Then run the cluster setup:

```bash
# Step 12: Install k3s, Keda, and dependencies
bash setup/lambda_setup.sh

# Step 13: Deploy the cluster
bash setup/lambda_cluster.sh

# Step 14: Verify cluster status
kubectl get deploy,svc,scaledobject

# Step 15: Run smoke tests
bash setup/smoke_sliced.sh
```

---

## 📋 Remaining Steps (16-25)

**Step 16:** Create `.env` (already done ✅)

**Steps 17-19:** Activate venv and source `.env` in Mac terminal
```bash
cd /Users/nakulmanchanda/dev/class-code/class9
source .venv/bin/activate
set -a && source .env && set +a
```

**Step 20:** Run the interactive app
```bash
make app
```

**Steps 21-24:** Send test queries through the gateway
```
text Write one sentence about a GPU.
vision What color is this?
audio Transcribe: hello from class 9.
quit
```

**Step 25:** Check trace logs
```bash
tail -n 5 traces/requests.jsonl
```

---

## 🔑 Key Milestones

| Milestone | Status | Command |
|-----------|--------|---------|
| Laptop tests pass | ✅ | `make test` |
| Code synced to Lambda | ✅ | `make sync` |
| Lambda cluster operational | ⏳ | SSH to Lambda, run `bash setup/lambda_cluster.sh` |
| First request sent | ⏳ | `make app` |
| System fully validated | ⏳ | Check traces |

---

## 📝 Notes

- The Makefile provides convenient shortcuts for each step
- All laptop tests passed; one vLLM worker test was skipped (expected)
- Lambda instance is running at `129.213.22.135`
- SSH key: `~/.ssh/lambda_instance`
- Once on Lambda, you can use the same Makefile commands if venv is set up there
