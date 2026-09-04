# =============================================================================
# RegimeX — Developer Makefile
# =============================================================================
#
# Provides a consistent, documented interface for all quality commands.
#
# Usage:
#   make help              — Show available commands
#   make quality           — Run the full quality gate
#   make backend-test      — Run backend tests
#   make backend-lint      — Run Ruff lint check
#   make backend-format    — Apply Ruff formatter
#   make backend-typecheck — Run mypy
#   make frontend-lint     — Run Next.js ESLint
#   make frontend-typecheck— Run tsc --noEmit
#   make frontend-build    — Run production build
#
# Prerequisites:
#   Backend: Python 3.11+, pip install -e ".[dev]" in apps/api/
#   Frontend: Node 20+, npm install in apps/web/
#   Pre-commit: pip install pre-commit && pre-commit install
#
# This Makefile is cross-platform compatible (Linux, macOS, Windows via Git Bash).
# Windows users without make: use the commands documented in docs/V04/DEVELOPMENT.md
# or install Make via chocolatey: choco install make
# =============================================================================

.PHONY: help quality \
        backend-test backend-lint backend-format backend-format-check backend-typecheck \
        frontend-lint frontend-typecheck frontend-build \
        pre-commit-install pre-commit-run \
        clean

# Default target
.DEFAULT_GOAL := help

# Directories
API_DIR := apps/api
WEB_DIR := apps/web

# Python binary (use venv if present)
PYTHON := python

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo ""
	@echo "RegimeX Development Commands"
	@echo "============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Run 'make quality' to execute the full quality gate."
	@echo ""

# =============================================================================
# Full Quality Gate
# =============================================================================

quality: backend-format-check backend-lint backend-typecheck backend-test \
         frontend-lint frontend-typecheck ## Run all quality checks (full gate)
	@echo ""
	@echo "✅  All quality gates passed."
	@echo ""

# =============================================================================
# Backend — Python
# =============================================================================

backend-test: ## Run pytest (all backend unit tests)
	@echo "▶  Backend: running tests..."
	cd $(API_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short
	@echo "✅  Backend tests passed."

backend-lint: ## Run Ruff lint check (no fix)
	@echo "▶  Backend: running Ruff lint..."
	cd $(API_DIR) && ruff check app/ tests/
	@echo "✅  Backend lint clean."

backend-format: ## Apply Ruff formatter (modifies files)
	@echo "▶  Backend: applying Ruff format..."
	cd $(API_DIR) && ruff format app/ tests/
	@echo "✅  Backend format applied."

backend-format-check: ## Check Ruff formatting (no modifications)
	@echo "▶  Backend: checking Ruff format..."
	cd $(API_DIR) && ruff format --check app/ tests/
	@echo "✅  Backend format clean."

backend-typecheck: ## Run mypy strict type check
	@echo "▶  Backend: running mypy..."
	cd $(API_DIR) && mypy app tests
	@echo "✅  Backend type check passed."

# =============================================================================
# Frontend — TypeScript / Next.js
# =============================================================================

frontend-lint: ## Run Next.js ESLint
	@echo "▶  Frontend: running ESLint..."
	cd $(WEB_DIR) && npm run lint
	@echo "✅  Frontend lint clean."

frontend-typecheck: ## Run TypeScript compiler (no emit)
	@echo "▶  Frontend: running tsc --noEmit..."
	cd $(WEB_DIR) && npm run type-check
	@echo "✅  Frontend type check passed."

frontend-build: ## Run Next.js production build
	@echo "▶  Frontend: running production build..."
	cd $(WEB_DIR) && npm run build
	@echo "✅  Frontend build succeeded."

# =============================================================================
# Pre-commit
# =============================================================================

pre-commit-install: ## Install pre-commit hooks
	pre-commit install
	@echo "✅  Pre-commit hooks installed."

pre-commit-run: ## Run all pre-commit hooks against all files
	pre-commit run --all-files

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Remove generated build artefacts (NOT node_modules or venv)
	@echo "▶  Cleaning generated artefacts..."
	find $(API_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(API_DIR) -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find $(API_DIR) -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find $(API_DIR) -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find $(API_DIR) -type f -name "*.pyc" -delete 2>/dev/null || true
	find $(WEB_DIR) -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find $(WEB_DIR) -type f -name "tsconfig.tsbuildinfo" -delete 2>/dev/null || true
	@echo "✅  Clean complete."
