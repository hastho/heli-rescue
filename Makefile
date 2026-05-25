.PHONY: run test lint clean

run:
	python main.py

test:
	python -m pytest tests/ -v

lint:
	@python -m ruff check main.py --fix 2>/dev/null || python -m py_compile main.py

clean:
	rm -rf __pycache__ .pytest_cache
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
