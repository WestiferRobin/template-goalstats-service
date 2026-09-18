.PHONY: build run stop logs providers providers-stop
build run stop logs providers providers-stop:
	@$(PYTHON) scripts/workflow.py $@
