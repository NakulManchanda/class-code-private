VENV := .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
export PYTHONPATH := $(CURDIR)

.PHONY: setup sync ssh cluster smoke test app fakeworker

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo
	@echo "Mac:     make sync && make ssh"
	@echo "Lambda:  bash setup/lambda_setup.sh && bash setup/lambda_cluster.sh && make smoke"

sync:
	bash setup/sync_to_lambda.sh

ssh:
	bash setup/ssh.sh

cluster:
	bash setup/lambda_cluster.sh

smoke:
	bash setup/smoke_sliced.sh

test:
	$(PYTHON) -m pytest tests/

app:
	$(PYTHON) app.py

fakeworker:
	$(PYTHON) -m fakeworker.run --list
