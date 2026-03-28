.PHONY: help install install-dev test test-cov lint format clean build build-all publish-all

help: ## Show this help message
	@echo "OpenDAN Multi-Package Project"
	@echo "============================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the main opendan package in development mode
	pip install -e src/opendan

install-dev: ## Install all packages in development mode with dev dependencies
	pip install -e src/opendan[dev]
	pip install -e src/agents/jarvis[dev]
	pip install -e src/services[dev]

test: ## Run tests for all packages
	pytest test/ -v

test-cov: ## Run tests with coverage report
	pytest test/ --cov=src --cov-report=html --cov-report=term-missing

lint: ## Run linting checks
	ruff check src/ test/
	mypy src/ --ignore-missing-imports

format: ## Format code with black and ruff
	black src/ test/
	ruff check --fix src/ test/

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

build: ## Build the main opendan package
	cd src/opendan && python -m hatch build

build-all: ## Build all packages
	python build_all.py

publish-all: ## Publish all packages (dry run)
	python build_all.py --publish --dry-run

publish-all-real: ## Publish all packages (real)
	python build_all.py --publish

# Development shortcuts
dev-install: clean install-dev ## Clean install with dev dependencies
dev-test: test-cov lint ## Run full development checks
dev-format: format test ## Format code and run tests


