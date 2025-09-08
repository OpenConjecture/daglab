.PHONY: install install-dev test lint format type-check build clean docs serve-docs

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Run tests
test:
	pytest tests/ -v --cov=daglab --cov-report=html --cov-report=term

# Run tests with markers
test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

# Run linting
lint:
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

# Format code
format:
	black src/ tests/
	isort src/ tests/
	ruff check --fix src/ tests/

# Run type checking
type-check:
	mypy src/daglab

# Build package
build:
	python -m build

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build documentation
docs:
	cd docs && make clean && make html

# Serve documentation locally
serve-docs:
	cd docs && python -m http.server --directory _build/html

# Run all checks
check: lint type-check test

# Development workflow
dev: format lint type-check test