VENV := .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
export PYTHONPATH := $(CURDIR)

.PHONY: help setup venv sync ssh lambda-setup lambda-cluster lambda-status smoke \
        webui-open repl repl-demo metrics profile \
        observe grafana-open grafana-password \
        locust-install locust-run locust-open \
        crew-flood dashboards-list \
        test test-all clean

help:
	@echo ""
	@echo "Class 9b: Distributed LLM Gateway + Router + vLLM Cluster"
	@echo "IP: 193.122.152.87  |  Region: us-east-1  |  Type: gpu_1x_a100_sxm4"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 1: LAPTOP SETUP (Steps 1-4)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make setup              Create venv and install dependencies"
	@echo "  make venv               Create venv only (pip not run)"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 2: LAMBDA CLUSTER (Steps 1-6)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make sync               Step 1:  Sync code to Lambda (193.122.152.87)"
	@echo "  make ssh                Step 2:  SSH into Lambda (keep open)"
	@echo "  make lambda-setup       Step 3:  Run lambda_setup.sh (on Lambda)"
	@echo "  make lambda-cluster     Step 4:  Run lambda_cluster.sh (on Lambda)"
	@echo "  make lambda-status      Step 5:  Check cluster status"
	@echo "  make smoke              Step 6:  Run smoke_sliced.sh test"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 3: CHAT IN BROWSER (Steps 7-8)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make webui-open         Step 7:  Open WebUI at http://127.0.0.1:30030"
	@echo "                          Step 8:  Send a message in the browser"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 4: SEND TRAFFIC FROM REPL (Steps 9-20)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make repl               Step 12: Run gateway.repl (REPL prompt)"
	@echo "  make repl-demo          Show example REPL commands"
	@echo ""
	@echo "  In REPL, try:"
	@echo "    text <prompt>         Send text request"
	@echo "    vision <image-q>      Send vision request"
	@echo "    audio <audio-q>       Send audio request"
	@echo "    hop <prompt>          Test KV cache hop (prefill→decode)"
	@echo "    evict                 Clear hopped cache"
	@echo "    metrics               Show gateway metrics"
	@echo "    profile               Show request profile"
	@echo "    quit                  Exit REPL"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 5: DAY 2 - OBSERVABILITY (Steps 22-24)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make observe            Step 22: Setup Grafana (on Lambda)"
	@echo "  make grafana-open       Step 24: Open Grafana at http://127.0.0.1:31495"
	@echo "  make grafana-password   Step 23: Show Grafana admin password"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 6: LOCUST LOAD TESTING (Steps 25-28)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make locust-install     Step 25: Install locust requirements"
	@echo "  make locust-run         Step 26: Run Locust (keeps terminal)"
	@echo "  make locust-open        Step 27: Open Locust UI at http://127.0.0.1:8089"
	@echo "                          Step 28: Set users=4, spawn_rate=2, click Start"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "PHASE 7: CREW FLOOD & ANALYSIS (Steps 29-32)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make crew-flood         Step 29: Run crew_flood (48 rounds, 8 workers)"
	@echo "  make dashboards-list    Step 30: List Grafana dashboards to view"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "UTILITIES"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make test               Run pytest tests"
	@echo "  make test-all           Run all tests with verbose output"
	@echo ""
	@echo "REJECTION TESTING - Trigger specific failure modes"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make test-rejection-admission-tokens"
	@echo "                          429: Exhaust tenant token quota"
	@echo "  make test-rejection-router-no-pod"
	@echo "                          503: No available pod for model"
	@echo "  make test-rejection-gateway-concurrency"
	@echo "                          429/503: High concurrency stress"
	@echo "  make test-rejection-mooncake-kv"
	@echo "                          KV cache pressure from large context"
	@echo "  make test-rejection-overflow"
	@echo "                          Trigger Superlinked fallback"
	@echo "  make test-rejection-all"
	@echo "                          Run all rejection tests"
	@echo "  make test-rejections-help"
	@echo "                          Detailed rejection testing guide"
	@echo ""
	@echo "  make clean              Remove .venv and __pycache__"
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: LAPTOP SETUP
# ═══════════════════════════════════════════════════════════════════════════

setup: venv
	@echo "Installing dependencies..."
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. make sync       (sync code to Lambda)"
	@echo "  2. make ssh        (SSH into Lambda, keep open)"
	@echo "  3. On Lambda: bash setup/lambda_setup.sh"
	@echo "  4. On Lambda: bash setup/lambda_cluster.sh"
	@echo "  5. On Lambda: make smoke"
	@echo ""

venv:
	@if [ ! -d $(VENV) ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "✓ venv created at $(VENV)"; \
	else \
		echo "✓ venv already exists at $(VENV)"; \
	fi

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: LAMBDA CLUSTER
# ═══════════════════════════════════════════════════════════════════════════

sync:
	@echo "Step 1: Syncing code to Lambda (193.122.152.87)..."
	bash setup/sync_to_lambda.sh

ssh:
	@echo "Step 2: Connecting to Lambda..."
	@echo "⚠️  IMPORTANT: Keep this terminal open for port forwarding!"
	@echo ""
	bash setup/ssh.sh

lambda-setup:
	@echo "Step 3: You are now on Lambda. Run this:"
	@echo ""
	@echo "  bash setup/lambda_setup.sh"
	@echo ""

lambda-cluster:
	@echo "Step 4: You are on Lambda. Run this:"
	@echo ""
	@echo "  bash setup/lambda_cluster.sh"
	@echo ""

lambda-status:
	@echo "Step 5: Checking cluster status..."
	@echo ""
	@echo "Run this on Lambda:"
	@echo "  kubectl get deploy,svc,scaledobject"
	@echo ""

smoke:
	@echo "Step 6: Running smoke test..."
	bash setup/smoke_sliced.sh

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: CHAT IN BROWSER
# ═══════════════════════════════════════════════════════════════════════════

webui-open:
	@echo "Step 7: Opening WebUI..."
	@echo ""
	@echo "WebUI: http://127.0.0.1:30030"
	@echo "Gateway: http://127.0.0.1:8080"
	@echo ""
	open http://127.0.0.1:30030

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: SEND TRAFFIC FROM REPL
# ═══════════════════════════════════════════════════════════════════════════

repl:
	@echo "Step 12: Starting REPL..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && $(PYTHON) -m gateway.repl; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

repl-demo:
	@echo "REPL Demo Commands:"
	@echo ""
	@echo "Step 13: text <prompt>"
	@echo "  text Write one sentence about a GPU."
	@echo ""
	@echo "Step 14: vision <prompt>"
	@echo "  vision What color is this?"
	@echo ""
	@echo "Step 15: audio <prompt>"
	@echo "  audio Transcribe: hello from class 9b."
	@echo ""
	@echo "Step 16: hop <prompt> (tests KV cache prefill→decode hop)"
	@echo "  hop Write one sentence about a GPU."
	@echo ""
	@echo "Step 17: evict (drops hopped cache)"
	@echo "  evict"
	@echo ""
	@echo "Step 18: metrics"
	@echo "  metrics"
	@echo ""
	@echo "Step 19: profile"
	@echo "  profile"
	@echo ""
	@echo "Step 20: quit"
	@echo "  quit"
	@echo ""

metrics:
	@echo "Showing REPL metrics command (run inside REPL):"
	@echo "  metrics"

profile:
	@echo "Showing REPL profile command (run inside REPL):"
	@echo "  profile"

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: DAY 2 - OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════════════

observe:
	@echo "Step 22: Setting up Grafana observability..."
	@echo "⚠️  Run this on Lambda (in SSH terminal):"
	@echo ""
	@echo "  bash setup/day2_observability.sh"
	@echo ""

grafana-open:
	@echo "Step 24: Opening Grafana..."
	@echo ""
	@echo "Grafana: http://127.0.0.1:31495"
	@echo "Username: admin"
	@echo "Password: (from step 23, see: make grafana-password)"
	@echo ""
	open http://127.0.0.1:31495

grafana-password:
	@echo "Step 23: Retrieving Grafana admin password..."
	@echo ""
	@echo "Run this on Lambda:"
	@echo "  kubectl -n monitoring get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo"
	@echo ""

grafana-port-forward:
	@echo "⚠️  CRITICAL: Grafana port-forward (run on Lambda in new terminal)"
	@echo ""
	@echo "  kubectl -n monitoring port-forward svc/grafana 31495:80"
	@echo ""
	@echo "Keep this terminal open. Then on Mac: make grafana-open"
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: LOCUST LOAD TESTING
# ═══════════════════════════════════════════════════════════════════════════

locust-install:
	@echo "Step 25: Installing Locust requirements..."
	$(PYTHON) -m pip install -q -r requirements-load.txt
	@echo "✓ Locust installed"

locust-run: locust-install
	@echo "Step 26: Starting Locust..."
	@echo ""
	@echo "Wait for: 'Locust web interface now available at http://0.0.0.0:8089'"
	@echo "Then: make locust-open (in new terminal)"
	@echo ""
	$(PYTHON) -m locust -f app/locustfile.py --host http://127.0.0.1:8080

locust-open:
	@echo "Step 27: Opening Locust UI..."
	@echo ""
	@echo "Locust: http://127.0.0.1:8089"
	@echo "Step 28: Set Number of users=4, Ramp up=2, click Start"
	@echo ""
	open http://127.0.0.1:8089

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 7: CREW FLOOD & ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

crew-flood:
	@echo "Step 29: Running crew_flood (48 rounds, 8 workers)..."
	$(PYTHON) -m pip install -q -r requirements-load.txt
	ORCH_URL=http://127.0.0.1:8080/v1 $(PYTHON) -m app.crew_flood --rounds 48 --workers 8

dashboards-list:
	@echo "Step 30: Grafana dashboards to view (in order):"
	@echo ""
	@echo "1.  Class 9b / Cluster"
	@echo "2.  Class 9b / Success and failures"
	@echo "3.  Class 9b / Overview (metrics.py)"
	@echo "4.  Class 9b / Gateway + admission"
	@echo "5.  Class 9b / Router"
	@echo "6.  Class 9b / KEDA"
	@echo "7.  Class 9b / HAMi slices"
	@echo "8.  Class 9b / Mooncake KV"
	@echo "9.  Class 9b / Pods and replicas"
	@echo "10. Class 9b / vLLM"
	@echo ""
	@echo "Grafana: http://127.0.0.1:31495"
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

test:
	@echo "Running pytest tests..."
	$(PYTHON) -m pytest tests/ -q

test-all:
	@echo "Running all tests (verbose)..."
	$(PYTHON) -m pytest tests/ -v

# ═══════════════════════════════════════════════════════════════════════════
# REJECTION TESTING - Trigger specific failure modes
# ═══════════════════════════════════════════════════════════════════════════

test-rejection-admission-tokens:
	@echo "Triggering ADMISSION rejection (429 tenant_tokens)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && \
		NUM_REQUESTS=5 CONCURRENCY=1 $(PYTHON) -m tests.test_rejections admission_tenant_tokens; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

test-rejection-router-no-pod:
	@echo "Triggering ROUTER rejection (503 no_eligible_pod)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && \
		NUM_REQUESTS=5 CONCURRENCY=1 $(PYTHON) -m tests.test_rejections router_no_eligible_pod; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

test-rejection-gateway-concurrency:
	@echo "Triggering GATEWAY rejection (high concurrency)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && \
		NUM_REQUESTS=50 CONCURRENCY=50 $(PYTHON) -m tests.test_rejections gateway_high_concurrency; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

test-rejection-mooncake-kv:
	@echo "Triggering MOONCAKE KV pressure (large context)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && \
		NUM_REQUESTS=5 CONCURRENCY=1 $(PYTHON) -m tests.test_rejections mooncake_kv_pressure; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

test-rejection-overflow:
	@echo "Triggering OVERFLOW (Superlinked fallback)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && \
		NUM_REQUESTS=5 CONCURRENCY=1 $(PYTHON) -m tests.test_rejections overflow_superlinked; \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

test-rejection-all:
	@echo "Running ALL rejection tests (one by one)..."
	@make test-rejection-admission-tokens
	@echo ""
	@make test-rejection-router-no-pod
	@echo ""
	@make test-rejection-gateway-concurrency
	@echo ""
	@make test-rejection-mooncake-kv
	@echo ""
	@make test-rejection-overflow

test-rejections-help:
	@echo "Rejection Testing Targets:"
	@echo ""
	@echo "  make test-rejection-admission-tokens"
	@echo "    → Exhaust tenant token quota (429 rejection)"
	@echo ""
	@echo "  make test-rejection-router-no-pod"
	@echo "    → Request model with no available pod (503 rejection)"
	@echo ""
	@echo "  make test-rejection-gateway-concurrency"
	@echo "    → High concurrency stress (429/503 from admission)"
	@echo ""
	@echo "  make test-rejection-mooncake-kv"
	@echo "    → Large context → KV cache pressure"
	@echo ""
	@echo "  make test-rejection-overflow"
	@echo "    → Trigger Superlinked overflow (200 via fallback)"
	@echo ""
	@echo "  make test-rejection-all"
	@echo "    → Run all rejection tests sequentially"
	@echo ""
	@echo "Customize with env vars:"
	@echo "  NUM_REQUESTS=10 CONCURRENCY=5 make test-rejection-gateway-concurrency"
	@echo ""

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned"

.DEFAULT_GOAL := help
