PYTHON ?= python
PACKAGE_SRC := src
TEST_DIR := tests

.PHONY: help test test-verbose coverage coverage-html compile check clean build publish-pypi

help:
	@echo "Available targets:"
	@echo "  test          Run unit tests (unittest discovery)"
	@echo "  test-verbose  Run unit tests with verbose output"
	@echo "  coverage      Run unit tests with coverage report"
	@echo "  coverage-html Generate HTML coverage report (htmlcov/index.html)"
	@echo "  compile       Compile-check source and tests"
	@echo "  check         Run compile check + tests"
	@echo "  build         Build source and wheel distributions"
	@echo "  publish-pypi  Build, validate, and upload distributions to PyPI"
	@echo "  clean         Remove temporary/build/coverage artifacts"

test:
	PYTHONPATH=$(PACKAGE_SRC) $(PYTHON) -m unittest discover -s $(TEST_DIR) -p "test_*.py"

test-verbose:
	PYTHONPATH=$(PACKAGE_SRC) $(PYTHON) -m unittest discover -s $(TEST_DIR) -p "test_*.py" -v

coverage:
	PYTHONPATH=$(PACKAGE_SRC) $(PYTHON) -m coverage run -m unittest discover -s $(TEST_DIR) -p "test_*.py"
	$(PYTHON) -m coverage report -m

coverage-html:
	PYTHONPATH=$(PACKAGE_SRC) $(PYTHON) -m coverage run -m unittest discover -s $(TEST_DIR) -p "test_*.py"
	$(PYTHON) -m coverage html
	@echo "Coverage HTML report: htmlcov/index.html"

compile:
	$(PYTHON) -m compileall src tests

check: compile test

build:
	$(PYTHON) -m build

publish-pypi: build
	$(PYTHON) -m twine check dist/*
	$(PYTHON) -m twine upload dist/*

clean:
	rm -rf .coverage htmlcov build dist .pytest_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
