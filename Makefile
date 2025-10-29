.PHONY: requirements venv install-local build publish

requirements:
	@mkdir -p deployment_package
	@uv export --format requirements.txt

venv: requirements
	@if [ ! -d ".venv" ]; then \
      echo "Creating venv…"; \
      uv venv .venv; \
    fi
	@. .venv/bin/activate && \
      uv pip install --upgrade pip && \
      uv sync

install-local:
	@uv pip uninstall ".[dev]"
	@uv pip install -e ".[dev]"

build:
	@uv build

publish: build
	@uv version --bump patch
	@uv publish