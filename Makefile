# =========================================================
# Makefile for Introducing Agents
# =========================================================
# Provides tasks for:
#   - Setting up virtual environment
#   - Installing dependencies
#   - Running tests and type checks
#   - Formatting code
#   - Cleaning up artifacts
# =========================================================

.DEFAULT_GOAL := help

# =========================================================
# Variables
# =========================================================

# Accept: 3.MIN ≤ version < 3.MAX_EXCL
PYTHON ?= python3
PY_MIN ?= 10
PY_MAX_EXCL ?= 13

# Configuration
VENV ?= ai_agents
VENV_BIN := $(VENV)/bin
PYTHON_IN_VENV := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
PIP_COMPILE := $(VENV_BIN)/pip-compile
PYTEST := $(VENV_BIN)/pytest
RUFF := $(VENV_BIN)/ruff
BLACK := $(VENV_BIN)/black
MYPY := $(VENV_BIN)/mypy

PYTEST_ARGS ?= tests

SRC_DIRS := src
INSTALL_STAMP := $(VENV)/.install.stamp

.PHONY: help python-version-check venv run test lint typecheck format qa format-html lint-html clean clean-all

# =========================================================
# Help
# =========================================================

help: ## Show available commands.
	@awk 'BEGIN {FS=":.*## "; print "\nAvailable commands:"} /^[[:alnum:]_.-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =========================================================
# Environment setup
# =========================================================

python-version-check: ## Ensure interpreter exists and matches the supported range.
	@echo "Checking Python version from '$$(which $(PYTHON))'..."
	@if ! command -v $(PYTHON) >/dev/null 2>&1; then \
		echo "'$(PYTHON)' not found in PATH."; \
		echo "Please install Python 3.$(PY_MIN) or newer (but < 3.$(PY_MAX_EXCL))."; \
		exit 1; \
	fi; \
	MAJOR=`$(PYTHON) -c 'import sys; print(sys.version_info[0])'`; \
	MINOR=`$(PYTHON) -c 'import sys; print(sys.version_info[1])'`; \
	if [ "$$MAJOR" -ne 3 ]; then \
		echo "Detected Python $$MAJOR, expected Python 3.x."; \
		exit 1; \
	elif [ "$$MINOR" -lt $(PY_MIN) ] || [ "$$MINOR" -ge $(PY_MAX_EXCL) ]; then \
		echo "Detected Python version $$MAJOR.$$MINOR."; \
		echo "Please install Python between 3.$(PY_MIN) and 3.$$(($(PY_MAX_EXCL)-1))."; \
		exit 1; \
	else \
		echo "Python version $$MAJOR.$$MINOR is acceptable."; \
	fi

venv: python-version-check ## Create the virtual environment and ensure pip-tools is available.
	@if [ -d "$(VENV)" ]; then \
		echo "virtual environment already exists: $(VENV)"; \
	else \
		echo "Creating virtual environment with $(PYTHON)..."; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@echo "Upgrading pip and installing pip-tools..."
	@$(PIP) install --upgrade 'pip<25' 'pip-tools>=7.5.1' 

requirements.txt: pyproject.toml | venv ## Compile a locked requirements file from pyproject.toml.
	@echo "Compiling requirements.txt from pyproject.toml..."
	@$(PIP_COMPILE) --output-file=requirements.txt pyproject.toml --extra dev
	@echo "requirements.txt updated."

install: $(INSTALL_STAMP) ## Fully provision the development environment.

$(INSTALL_STAMP): requirements.txt | venv
	@echo "Installing dependencies into virtual environment..."
	@$(PIP) install -r requirements.txt
	@$(PIP) install -e .
	@touch $(INSTALL_STAMP)

# =========================================================
# Running and testing
# =========================================================

run: install ## Run the lesson 02 agent CLI (override APP_ENTRY or RUN_ARGS as needed).
	@echo "Running $(APP_ENTRY) $(RUN_ARGS)..."
	@$(PYTHON_IN_VENV) $(APP_ENTRY) $(RUN_ARGS)

test: install ## Run the unit test suite.
	@echo "Running tests..."
	@PYTHONPATH=. $(PYTEST) $(PYTEST_ARGS)

# =========================================================
# Python code quality
# =========================================================

lint: install ## Run Ruff linter across source, lessons, and tests.
	@echo "Running Ruff (lint checks)..."
	@$(RUFF) check $(SRC_DIRS)

typecheck: install ## Run MyPy static type checks.
	@echo "Running MyPy (static type checks)..."
	@$(MYPY) $(SRC_DIRS)

format: install ## Format code using Black.
	@echo "Formatting code with Black..."
	@$(BLACK) $(SRC_DIRS)

qa: lint typecheck test ## Run lint, type checks, and tests.

# =========================================================
# HTML Code quality
# =========================================================

format-html: ## Format HTML, CSS, and JS files with Prettier.
	@echo "Formatting HTML, CSS, and JS files with Prettier..."
	npx prettier --write "index.html"

lint-html: ## Lint HTML files with htmlhint.
	@echo "Linting HTML files with htmlhint..."
	npx htmlhint "index.html"

# =========================================================
# Cleaning
# =========================================================

clean: ## Remove caches and temporary files (keeps the virtual environment).
	@echo "Cleaning build and cache artifacts (keeping virtual environment)..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name '__pycache__' -exec rm -rf {} +

clean-all: clean ## Remove the virtual environment and build artifacts.
	@echo "Removing virtual environment and build artifacts..."
	rm -rf $(VENV) dist build *.egg-info
