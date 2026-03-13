.PHONY: help install install-dev test test-cov lint format type-check clean docs build publish

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e "."

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests
	pytest -m "not slow and not integration"

test-cov: ## Run tests with coverage
	pytest --cov=video_cut_skill --cov-report=term-missing

test-all: ## Run all tests including slow ones
	pytest

lint: ## Run linting
	ruff check src tests
	ruff check --select I src tests

format: ## Format code
	black src tests
	ruff check --fix src tests

type-check: ## Run type checking
	mypy src

check: lint type-check test ## Run all checks (lint, type-check, test)

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

docs-deploy: ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy

build: ## Build package
	python -m build

publish-test: ## Publish to TestPyPI
	python -m twine upload --repository testpypi dist/*

publish: ## Publish to PyPI
	python -m twine upload dist/*

docker-build: ## Build Docker image
	docker build -t video-cut-skill:latest .

docker-run: ## Run Docker container
	docker run -it --rm -v $(PWD)/data:/data video-cut-skill:latest
