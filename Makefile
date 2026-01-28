.PHONY: help install install-dev setup test lint format clean build dist publish-test publish all

help:
	@echo "Available targets:"
	@echo "  setup         First-time setup (install dev dependencies)"
	@echo "  install       Install package with core dependencies"
	@echo "  install-dev   Install package with dev dependencies"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linters (ruff, mypy)"
	@echo "  format        Format code with ruff"
	@echo "  clean         Remove build artifacts"
	@echo "  build         Build package distribution"
	@echo "  dist          Alias for build"
	@echo "  publish-test  Publish to TestPyPI"
	@echo "  publish       Publish to PyPI (production)"
	@echo "  all           Complete build: clean, format, lint, test, build"

setup: install-dev

install:
	poetry install

install-dev:
	poetry install --with dev

test:
	poetry run pytest tests/ -v --cov=gutenfetch --cov-report=term-missing

lint:
	poetry run ruff check .
	poetry run mypy gutenfetch/

format:
	poetry run ruff format .

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache/ .ruff_cache/

build: clean
	poetry build

dist: build

publish-test: build
	poetry publish -r testpypi

publish: build
	poetry publish

all: clean install format lint test build
