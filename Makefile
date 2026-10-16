.PHONY: install dev test lint format up down logs check-gemini

install:            ## Install dependencies (incl. dev tools)
	uv sync

dev:                ## Run the app with auto-reload at http://localhost:8000
	uv run uvicorn app.main:app --reload --port 8000

test:               ## Run the test suite
	uv run pytest -q

lint:               ## Lint
	uv run ruff check .

format:             ## Auto-fix lint issues
	uv run ruff check . --fix

up:                 ## Build and start with Docker Compose
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app

check-gemini:       ## Live check of GEMINI_API_KEY and model names
	uv run python scripts/check_gemini.py --edit
