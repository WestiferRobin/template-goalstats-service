.PHONY: check tooling certify certify-host
check tooling certify certify-host:
	@$(PYTHON) scripts/workflow.py $@
