.PHONY: build run stop logs
build run stop logs:
	@$(PYTHON) scripts/workflow.py $@
