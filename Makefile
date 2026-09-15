.DEFAULT_GOAL := help
ENV ?= local
PYTHON ?= python3
export ENV MESSAGE
export PYTHONDONTWRITEBYTECODE = 1
.PHONY: help setup build migrate run stop logs unit integration test smoke check coverage migration migration-check certify
help setup build migrate run stop logs unit integration test smoke check coverage migration migration-check certify:
	@$(PYTHON) scripts/workflow.py $@
