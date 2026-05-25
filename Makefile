.PHONY: run test lint clean

run:
	python main.py

test:
	@if [ -d tests ]; then python -m pytest tests/ -v; else echo "No tests yet — create tests/ directory"; fi

lint:
	@python -m ruff check main.py --fix 2>/dev/null || python -m py_compile main.py

clean:
	rm -rf __pycache__ .pytest_cache
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
