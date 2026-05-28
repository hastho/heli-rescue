.PHONY: run test lint clean

PYTHON = python3

run:
	$(PYTHON) main.py

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	@$(PYTHON) -m ruff check main.py --fix 2>/dev/null || $(PYTHON) -m py_compile main.py

clean:
	rm -rf __pycache__ .pytest_cache
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
