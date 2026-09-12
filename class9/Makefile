VENV := .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
export PYTHONPATH := $(CURDIR)

.PHONY: help setup test fakeworker-list fakeworker-soak fakeworker-429 fakeworker-overflow \
        sync ssh lambda-setup lambda-cluster lambda-status smoke \
        port-forward app test-traffic test-traffic-5 test-traffic-10 test-traffic-fast test-traffic-nodeport \
        logs clean superlinked-usage superlinked-keys

help:
	@echo "Capacity experiments: make test-429, test-503, test-saturation, test-overflow (see make capacity-help)"
	@echo "Class 9: Gateway + Router + vLLM Cluster"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "LAPTOP SETUP (Steps 1-9):"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make setup              Step 1-4:  Create venv and install deps"
	@echo "  make test               Step 5:    Run pytest tests"
	@echo "  make fakeworker-list    Step 6:    List fakeworker behaviors"
	@echo "  make fakeworker-soak    Step 7:    Test fleet-soak behavior"
	@echo "  make fakeworker-429     Step 8:    Test tenant-429-stays behavior"
	@echo "  make fakeworker-overflow Step 9:   Test overflow-on-503 behavior"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "LAMBDA CLUSTER (Steps 10-15):"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make sync               Step 10:   Sync code to Lambda instance"
	@echo "  make ssh                Step 11:   SSH into Lambda instance"
	@echo "  make lambda-setup       Step 12:   Run lambda_setup.sh"
	@echo "  make lambda-cluster     Step 13:   Run lambda_cluster.sh"
	@echo "  make lambda-status      Step 14:   Check cluster status"
	@echo "  make smoke              Step 15:   Run smoke_sliced.sh"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "SEND TRAFFIC (Steps 16-25):"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make port-forward       Step 16:   Start SSH tunnels (KEEP RUNNING)"
	@echo "  make app                Step 20:   Run app.py interactive REPL"
	@echo "  make test-traffic-5     Step 21:   Send 5 concurrent requests"
	@echo "  make test-traffic-10    Step 21:   Send 10 concurrent worker requests"
	@echo "  make test-traffic-fast  Step 21:   Send 3 fast requests (15 tokens)"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "UTILITIES:"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  make clean              Remove .venv and __pycache__"
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════
# LAPTOP SETUP (Steps 1-9)
# ═══════════════════════════════════════════════════════════════════════════

setup:
	@echo "Steps 1-4: Creating venv and installing dependencies..."
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo ""
	@echo "✓ Setup complete! Next: make test"

test:
	@echo "Step 5: Running pytest tests..."
	$(PYTHON) -m pytest tests/ -v

fakeworker-list:
	@echo "Step 6: Listing fakeworker behaviors..."
	$(PYTHON) -m fakeworker.run --list

fakeworker-soak:
	@echo "Step 7: Running fleet-soak behavior..."
	$(PYTHON) -m fakeworker.run --behavior fleet-soak

fakeworker-429:
	@echo "Step 8: Running tenant-429-stays behavior..."
	$(PYTHON) -m fakeworker.run --behavior tenant-429-stays

fakeworker-overflow:
	@echo "Step 9: Running overflow-on-503 behavior..."
	$(PYTHON) -m fakeworker.run --behavior overflow-on-503

# ═══════════════════════════════════════════════════════════════════════════
# LAMBDA CLUSTER (Steps 10-15)
# ═══════════════════════════════════════════════════════════════════════════

sync:
	@echo "Step 10: Syncing code to Lambda..."
	bash setup/sync_to_lambda.sh

ssh:
	@echo "Step 11: Connecting to Lambda..."
	bash setup/ssh.sh

lambda-setup:
	@echo "Step 12: You are now on Lambda. Run this:"
	@echo "  bash setup/lambda_setup.sh"

lambda-cluster:
	@echo "Step 13: Run this on Lambda:"
	@echo "  bash setup/lambda_cluster.sh"

lambda-status:
	@echo "Step 14: Check cluster status on Lambda:"
	@echo "  kubectl get deploy,svc,scaledobject"

smoke:
	@echo "Step 15: Run smoke tests on Lambda:"
	bash setup/smoke_sliced.sh

# ═══════════════════════════════════════════════════════════════════════════
# SEND TRAFFIC (Steps 16-25)
# ═══════════════════════════════════════════════════════════════════════════

port-forward:
	@echo "Step 16: Starting SSH port forwarding tunnels..."
	@echo ""
	@echo "⚠️  IMPORTANT: Keep this terminal open while testing!"
	@echo ""
	bash setup/port_forward.sh

app:
	@if [ -f .env ]; then \
		set -a && . .env && set +a && $(PYTHON) app.py; \
	else \
		echo "Error: .env file not found."; \
		echo "First: cp .env.example .env"; \
		echo "Then edit .env with your Lambda IP and credentials"; \
		exit 1; \
	fi

test-traffic:
	@echo "Sending 5 concurrent test requests to gateway..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && TEST_NUM_REQUESTS=5 $(PYTHON) tests/test_traffic.py; \
	else \
		echo "Error: .env file not found."; \
		exit 1; \
	fi

test-traffic-5:
	@echo "Sending 5 concurrent test requests to gateway..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && TEST_NUM_REQUESTS=5 $(PYTHON) tests/test_traffic.py; \
	else \
		echo "Error: .env file not found."; \
		exit 1; \
	fi

test-traffic-10:
	@echo "Sending 10 concurrent worker requests..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && TEST_NUM_REQUESTS=10 $(PYTHON) tests/test_traffic.py; \
	else \
		echo "Error: .env file not found."; \
		exit 1; \
	fi

test-traffic-fast:
	@echo "Sending 3 fast test requests (short tokens, 10s timeout)..."
	@if [ -f .env ]; then \
		set -a && . .env && set +a && TEST_NUM_REQUESTS=3 TEST_MAX_TOKENS=15 TEST_TIMEOUT=10 $(PYTHON) tests/test_traffic.py; \
	else \
		echo "Error: .env file not found."; \
		exit 1; \
	fi

test-traffic-nodeport:
	@echo "Testing direct access to NodePort (30800)..."
	@for i in 1 2 3; do \
		echo "[$$i] Sending request..."; \
		curl -s -X POST http://129.213.22.135:30800/v1/completions \
			-H "Content-Type: application/json" \
			-d '{"prompt":"Test.","max_tokens":10}' | jq -c '.usage // "error"'; \
	done

# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

superlinked-usage:
	@echo "Opening Superlinked Usage & Billing console..."
	@echo "Check: Credit balance, Spend (30d), Units metered"
	@echo ""
	open "https://console.superlinked.com/console/usage"

superlinked-keys:
	@echo "Opening Superlinked API Keys console..."
	@echo "View active keys and their usage"
	@echo ""
	open "https://console.superlinked.com/console/keys"

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned"

.DEFAULT_GOAL := help

# Capacity experiments: local router -> forwarded Lambda workers.
LAB_REQUESTS ?= 128
LAB_CONCURRENCY ?= 32
LAB_TOKENS ?= 1024
LAB_TIMEOUT ?= 120
LAB_OVERFLOW_LIMIT ?= 3
.PHONY: test-429 test-503 test-saturation test-overflow capacity-help

test-429:
	$(PYTHON) -m scripts.capacity_lab 429

test-503:
	$(PYTHON) -m scripts.capacity_lab 503

test-saturation test-overflow:
	$(PYTHON) -m scripts.capacity_lab $(if $(filter test-overflow,$@),overflow,saturation) --requests $(LAB_REQUESTS) --concurrency $(LAB_CONCURRENCY) --tokens $(LAB_TOKENS) --timeout $(LAB_TIMEOUT) --overflow-limit $(LAB_OVERFLOW_LIMIT)

capacity-help:
	@cat scripts/CAPACITY_TESTING.md
