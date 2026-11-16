.DEFAULT_GOAL := help
.PHONY: help test lint

help: ## list the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-6s %s\n", $$1, $$2}'

test: ## run the tests
	uv run --no-project --with pytest python -m pytest -q

lint: ## ruff lint and format check
	uvx ruff check .
	uvx ruff format --check .
