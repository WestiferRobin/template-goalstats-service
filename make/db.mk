.PHONY: migrate migration migration-check
migrate migration migration-check:
	@$(PYTHON) scripts/workflow.py $@
