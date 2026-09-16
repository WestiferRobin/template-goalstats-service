.PHONY: unit integration test smoke
unit integration test smoke:
	@$(PYTHON) scripts/workflow.py $@
