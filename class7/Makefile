VENV := .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
export PYTHONPATH := $(CURDIR)

.PHONY: setup sync ssh smoke test bench bench-stress bench-clean replicas app logs logs1 logs2 gateway results

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo
	@echo "Mac:     bash setup/sync_to_lambda.sh && bash setup/ssh.sh"
	@echo "Lambda:  bash setup/lambda_setup.sh && bash setup/launch_replicas.sh && make smoke"

sync:
	bash setup/sync_to_lambda.sh

ssh:
	@. .env && ssh -i $$LAMBDA_SSH_KEY $$LAMBDA

replicas:
	-pkill -f 'vllm serve' 2>/dev/null
	sleep 2
	bash setup/launch_replicas.sh

logs:
	tail -f /tmp/vllm-8001.log /tmp/vllm-8002.log

logs1:
	tail -f /tmp/vllm-8001.log

logs2:
	tail -f /tmp/vllm-8002.log

smoke:
	bash setup/smoke_test.sh

test:
	$(PYTHON) -m pytest tests/

app:
	$(PYTHON) app.py

gateway:
	$(PYTHON) -m gateway.main --replicas http://127.0.0.1:8001,http://127.0.0.1:8002

bench:
	$(PYTHON) -m bench.report --replicas http://127.0.0.1:8001,http://127.0.0.1:8002 --queries 12 --workers 4

bench-stress:
	$(PYTHON) -m bench.report --replicas http://127.0.0.1:8001,http://127.0.0.1:8002 --queries 24 --workers 8

bench-clean:
	$(PYTHON) -m bench.report --replicas http://127.0.0.1:8001,http://127.0.0.1:8002 --queries 24 --workers 8

results:
	@. .env && scp -i $$LAMBDA_SSH_KEY $$LAMBDA:~/class7/results.html ~/Desktop/class7_results.html && open ~/Desktop/class7_results.html
