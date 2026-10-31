.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt check install probe

help: ## list the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## install the dev environment (uv)
	uv sync

test: ## run the tests (no Claude calls, no network)
	uv run pytest -q

lint: ## ruff lint, format check and ty type check
	uv run ruff check src tests
	uv run ruff format --check src tests
	uvx ty check src tests

fmt: ## format the code
	uv run ruff format src tests
	uv run ruff check --fix src tests

check: test lint ## tests and lint

install: ## install the global `factory` command, editable
	uv tool install --editable .

probe: ## re-run the paid print-mode probe (about $0.03 on haiku) in a temp dir
	experiments/probe_print_mode.sh "$$(mktemp -d)"
