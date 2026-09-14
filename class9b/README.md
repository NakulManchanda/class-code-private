# Class 9b — Distributed LLM Orchestration Lab

**Production-grade five-plane architecture for distributed inference with KV cache hopping.**

---

## 🎯 System Architecture

```
END USER
  ↓
Open WebUI (browser chat)  http://127.0.0.1:30030
  ↓
🟡 GATEWAY (admission)     http://127.0.0.1:8080/v1
🟡 ROUTER (placement)      Which pod handles this?
🟢 MOONCAKE (KV cache)     Transfer KV between pods
🔵 HAMi (GPU slicing)      GPU allocation per pod
🟣 KEDA (auto-scaling)     Scale pods on demand
  ↓
vLLM PODS (inference)
  text-0: Qwen2.5-3B-Instruct
  vision-0: Qwen2.5-VL-3B
  ↓
Response back to user ✨
```

**All five planes orchestrating transparently!**

---

## 📚 Documentation Index

### Getting Started
- **[RESTART_GUIDE](docs/RESTART_GUIDE.md)** — Quick 4-terminal setup for next session
- **[QUICK_START](docs/QUICK_START.md)** — 7-phase walkthrough (32 steps)
- **[THE_LOOP](docs/THE_LOOP.md)** — 6-step workflow (30 seconds overview)

### Architecture & Design
- **[FIVE_PLANES](docs/FIVE_PLANES.md)** — The framework (what each plane does)
- **[ARCHITECTURE_OPTIONS](docs/ARCHITECTURE_OPTIONS.md)** — Implementation alternatives
- **[WORKLOAD_ARCHITECTURE](docs/WORKLOAD_ARCHITECTURE.md)** — Workload-driven decisions
- **[TOOLING_MATRIX](docs/TOOLING_MATRIX.md)** — Tool selection matrix
- **[CODEBASE_ARCHITECTURE](docs/CODEBASE_ARCHITECTURE.md)** — Code organization by plane

### Operations & Troubleshooting
- **[KEY_CONCEPTS](docs/KEY_CONCEPTS.md)** — Terminology guide (study checklist)
- **[REPL_COMMANDS](docs/REPL_COMMANDS.md)** — 20+ REPL commands + metrics
- **[DAY2_RUNBOOK](docs/DAY2_RUNBOOK.md)** — Troubleshooting guide
- **[REJECTION_TESTING](docs/REJECTION_TESTING.md)** — Test failure modes (8 scenarios)

### User Interface & Sessions
- **[OPEN_WEBUI_GUIDE](docs/OPEN_WEBUI_GUIDE.md)** — ChatGPT-like interface walkthrough
- **[OPEN_WEBUI_RESULTS](docs/OPEN_WEBUI_RESULTS.md)** — How to capture session metrics

### Reference & Deep Dive
- **[INSTRUCTOR_TRANSCRIPT](docs/INSTRUCTOR_TRANSCRIPT.md)** — Class notes + homework

---

## 🔬 Experiments & Results

All metrics from load tests and sessions are saved to `results/` with timestamps:

```
results/
├── metrics_20260913_151953/     ← Session 1 results
│   ├── repl/
│   │   ├── metrics_snapshot.txt
│   │   ├── board_history.txt
│   │   └── latency_profile.txt
│   ├── prometheus/
│   └── ...
└── metrics_20260913_152031/     ← Session 2 results
    └── ...
```

### Download Metrics Before Shutdown

```bash
make download-metrics
```

Results save to `results/metrics_YYYYMMDD_HHMMSS/` with:
- REPL metrics snapshot (all Prometheus data)
- Routing board (last 12 requests)
- Latency profile (stage breakdown)
- Prometheus metrics exports
- Analysis guide (METRICS_GUIDE.md)

---

## 🚀 Quick Start (3 minutes)

```bash
# Terminal 1: SSH tunnel
make ssh

# Terminal 2: Test KV hops
make repl
lab> hop Write one sentence about a GPU.
# Watch for: kv_hop=1 ✨

# Terminal 3: Load test
make locust
# Set users=4, spawn=2, Start

# Browser: Open dashboards
# http://127.0.0.1:30030   (Open WebUI - chat)
# http://127.0.0.1:31495   (Grafana - metrics)
# http://127.0.0.1:8089    (Locust - load test)
```

See **[RESTART_GUIDE](docs/RESTART_GUIDE.md)** for full 4-terminal setup.

---

## 📊 Key Results

**Session 2 Summary (Sep 13, 2026):**

| Metric | Result | Status |
|--------|--------|--------|
| Peak throughput | 157.7 RPS | ✅ |
| Failure rate | 0% | ✅ |
| P50 latency | 500ms | ✅ |
| P95 latency | 3500ms | ✅ |
| KV hops | 14,005 | ✅ |
| Tokens cached | 226,950 | ✅ |
| Open WebUI chats | Multi-turn | ✅ |

---

## 🎓 Learning Path

**Start here → Read → Test → Understand**

1. **[THE_LOOP](docs/THE_LOOP.md)** (5 min) — What you'll do
2. **[FIVE_PLANES](docs/FIVE_PLANES.md)** (15 min) — How it's organized
3. **[RESTART_GUIDE](docs/RESTART_GUIDE.md)** (2 min) — Setup quick reference
4. **[REPL_COMMANDS](docs/REPL_COMMANDS.md)** (10 min) — Commands to test
5. **Run `make repl`** — Test it live
6. **[TOOLING_MATRIX](docs/TOOLING_MATRIX.md)** (10 min) — When to use what
7. **[WORKLOAD_ARCHITECTURE](docs/WORKLOAD_ARCHITECTURE.md)** (10 min) — Design decisions

---

## 🔧 Makefile Targets

```bash
# Setup
make setup           # Install dependencies
make sync            # Sync code to Lambda
make ssh             # Connect to Lambda

# Testing
make repl            # REPL for manual testing
make locust          # Load testing (runs on :8089)
make crew-flood      # Flood test (48 rounds × 8 workers)

# Observability
make observe         # Setup Grafana & Prometheus
make grafana-open    # Open Grafana dashboard
make grafana-password # Get admin password

# Shutdown
make download-metrics  # Download all metrics before shutdown
make clean           # Clean up venv and cache
```

---

## 💾 What's Included

- **Complete codebase** — Gateway, router, vLLM cluster, K8s configs
- **Comprehensive docs** — 15 guides covering every aspect
- **Test suite** — Rejection tests (8 scenarios), load tests
- **Observability** — Grafana dashboards, Prometheus metrics
- **Quick access** — 30+ make targets for common tasks
- **Metrics archiving** — Download and analyze sessions locally

---

## 🌐 Access Points

- **Open WebUI** — http://127.0.0.1:30030 (chat interface)
- **Gateway API** — http://127.0.0.1:8080/v1 (REPL/Locust target)
- **Grafana** — http://127.0.0.1:31495 (dashboards)
- **Locust** — http://127.0.0.1:8089 (load test UI)
- **Prometheus** — http://127.0.0.1:9090 (metrics)

---

## 📖 For More Information

- **Next session?** Start with [RESTART_GUIDE](docs/RESTART_GUIDE.md)
- **Deep dive?** Read [INSTRUCTOR_TRANSCRIPT](docs/INSTRUCTOR_TRANSCRIPT.md)
- **Troubleshooting?** Check [DAY2_RUNBOOK](docs/DAY2_RUNBOOK.md)
- **Architecture decision?** See [TOOLING_MATRIX](docs/TOOLING_MATRIX.md)

---

**Built with: Gateway + Router + vLLM + Mooncake + HAMi + KEDA**

**Status:** Production-ready ✅ | Fully documented ✅ | Battle-tested ✅
