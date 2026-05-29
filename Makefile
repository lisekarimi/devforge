# =====================================
# 🌱 Project & Environment Configuration
# =====================================
PROJECT_NAME = $(shell python3 -c "import re; print(re.search('name = \"(.*)\"', open('pyproject.toml').read()).group(1))")
VERSION = $(shell python3 -c "import re; print(re.search('version = \"(.*)\"', open('pyproject.toml').read()).group(1))")
-include .env
export


# =======================
# 🪝 Hooks
# =======================

hooks:	## Install pre-commit hooks
	pip install pre-commit && pre-commit install && pre-commit install --hook-type commit-msg


# =====================================
# ✨ Code Quality
# =====================================

lint:	## Run linting and format check
	uvx ruff@0.15.1 check .
	uvx ruff@0.15.1 format --check .

fix:	## Auto-fix code issues and format
	uvx ruff@0.15.1 check --fix .
	uvx ruff@0.15.1 format .


# =====================================
# ✨ Development & Run
# =====================================

install:	## Install dependencies via uv
	uv sync

api:	## Start the FastAPI agent service (port 8000)
	uv run uvicorn api:app --reload --port 8000

ngrok:	## Expose the local API publicly via ngrok
	ngrok http 8000

agent:	## Run the agent on a sample ticket (CLI mode)
	uv run python agent.py --ticket fixtures/ticket_1.json

clean:	## Remove tmp clones and cache files
	rm -rf tmp/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true


# =====================================
# 📚 Documentation & Help
# =====================================

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@python3 -c "import re; lines=open('Makefile', encoding='utf-8').readlines(); targets=[re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$',l) for l in lines]; [print(f'  make {m.group(1):<20} {m.group(2)}') for m in targets if m]"


# =======================
# 🎯 PHONY Targets
# =======================

.PHONY: $(shell python3 -c "import re; print(' '.join(re.findall(r'^([a-zA-Z_-]+):\s*.*?##', open('Makefile', encoding='utf-8').read(), re.MULTILINE)))")
