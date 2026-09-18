.PHONY: unit integration test smoke test-providers
unit integration test smoke test-providers:
	@$(PYTHON) scripts/workflow.py $@
