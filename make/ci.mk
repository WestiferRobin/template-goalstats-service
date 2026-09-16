.PHONY: check tooling certify
check tooling certify:
	@$(PYTHON) scripts/workflow.py $@
