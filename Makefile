.DEFAULT_GOAL := help

.PHONY: help install lint typecheck format test-unit test-contract test-integration test-e2e test check coverage build clean

help: ## Show this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	uv sync --all-extras

lint: ## Run ruff linter
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

format: ## Auto-format code
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

test-unit: ## Run unit tests
	uv run pytest tests/unit/ -v

test-contract: ## Run contract tests
	uv run pytest tests/contract/ -v

test-integration: ## Run integration tests
	uv run pytest tests/integration/ -v

test-e2e: ## Run e2e tests (requires cluster)
	uv run pytest tests/e2e/ -v --timeout=300

test: test-unit test-contract test-integration ## Run unit + contract + integration tests

check: lint typecheck test ## Run all checks

coverage: ## Run unit tests with coverage
	uv run pytest tests/unit/ --cov=src/kuberay_sdk --cov-report=term-missing --cov-report=html

build: ## Build distribution packages
	uv run python -m build

clean: ## Remove build artifacts
	rm -rf dist/ build/ .mypy_cache/ .pytest_cache/ .ruff_cache/ htmlcov/
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
