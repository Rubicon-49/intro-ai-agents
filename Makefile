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

# =========================================================
# Variables
# =========================================================

# Accept: 3.MIN ≤ version < 3.MAX_EXCL
PYTHON := python3
PY_MIN := 11
PY_MAX_EXCL := 13

# Configuration
VENV := ai_agents
PYTHONPATH := .
PYTEST := $(VENV)/bin/pytest
PIP := $(VENV)/bin/pip

# =========================================================
# Main targets
# =========================================================

.PHONY: help venv run test lint typecheck format Cleaning

help:
	@echo "Available commands:"
	@echo "  make venv        - Create a virtual environment using Python 3"
	@echo "  make install     - Create venv (if missing) with a Python in range and install deps"
	@echo "  make run         - Run the FastAPI app with Uvicorn"
	@echo "  make test        - Run unit and integration tests"
	@echo "  make lint        - Run Ruff linter"
	@echo "  make typecheck   - Run MyPy for static type checking"
	@echo "  make format      - Format code using Black"
	@echo "  make clean       - Remove caches and temporary files (keep venv)"
	@echo "  make clean-all   - Remove virtual environment and build artifacts"
	@echo ""

# =========================================================
# Environment setup
# =========================================================

# Ensure interpreter exists and matches the version window
python-version-check::
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

venv: python-version-check
	@if [ -d "$(VENV)" ]; then \
	  echo "virtual environment already exists: $(VENV)"; \
	else \
	  echo "Creating virtual environment with $(PYTHON) ..."; \
	  $(PYTHON) -m venv $(VENV); \
	fi
	@echo "Upgrading pip and installing pip-tools..."
	@$(PIP) install --upgrade pip pip-tools

compile-deps: venv
	@echo "Compiling requirements.txt from pyproject.toml..."
	@$(VENV)/bin/pip-compile --output-file=requirements.txt pyproject.toml --extra dev
	@echo "requirements.txt updated."

deps: compile-deps
	@echo "Installing dependencies into virtual environment..."
	$(PIP) install -r requirements.txt

devlink:
	@echo "Emsuring package is installed in editable mode..."	
	$(PIP) install -e .

install: deps devlink

# =========================================================
# Running and testing
# =========================================================

run1:
	python lessons/lesson_01_prompting/simple_llm.py
#	@echo "Start FastAPI app..."
#	PYTHONPATH=$(PYTHONPATH) $(UVICORN) src.app:app --reload

test:
	@echo "Running tests..."
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) -vv tests

# =========================================================
# PYTHON Code quality
# =========================================================

lint-python:
	@echo "Running Ruff (lint checks)..."
	$(VENV)/bin/ruff check src/

check-python:
	@echo "Running MyPy (static type checks)...":
	$(VENV)/bin/mypy src/

format-python:
	@echo "Formatting code with Black..."
	$(VENV)/bin/black src/

# =========================================================
# HTML Code quality
# =========================================================

# Format HTML, CSS, JS
format-html:
	@echo "Formatting HTML, CSS, and JS files with Prettier..."
	npx prettier --write "index.html"

# Lint HTML
lint-html:
	@echo "Linting HTML files with htmlhint..."
	npx htmlhint "index.html"

format: format-python
check: check-python lint-python

# =========================================================
# Cleaning
# =========================================================

# Clean caches only (keep env)
clean:
	@echo "Cleaning build and cache artifacts (keeping virtual environment)..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name '__pycache__' -exec rm -rf {} +

# Deep clean — use only when you need a total reset
clean-all: clean
	@echo "Removing virtual environment and build artifacts..."
	rm -rf $(VENV) dist build *.egg-info