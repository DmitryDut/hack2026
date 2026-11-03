.PHONY: dev test lint fmt seed reset check demo progress todo

dev:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

fmt:
	uv run ruff check --fix . && uv run ruff format .

seed:
	uv run python -m scripts.seed

reset:
	rm -f data/app.db
	$(MAKE) seed

check: lint test

demo: reset dev

progress:
	uv run python scripts/progress.py

todo:
	uv run python scripts/progress.py --todo
