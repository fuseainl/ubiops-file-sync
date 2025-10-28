.PHONY: install-local

install-local:
	@uv pip uninstall ".[dev]"
	@uv pip install -e ".[dev]"