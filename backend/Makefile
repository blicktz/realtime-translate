.PHONY: install dev start test lint format clean help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies with Poetry
	poetry install
	poetry run pip install -e ./pipecat

install-dev: ## Install all dependencies including dev
	poetry install --with dev
	poetry run pip install -e ./pipecat

dev: ## Run development server with auto-reload
	poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000

start: ## Run production server
	poetry run uvicorn main:app --host 0.0.0.0 --port 8000

test: ## Run tests
	poetry run pytest -v

test-cov: ## Run tests with coverage
	poetry run pytest --cov=. --cov-report=html --cov-report=term

lint: ## Run linting checks
	poetry run ruff check .

format: ## Format code with Black
	poetry run black .

type-check: ## Run type checking with MyPy
	poetry run mypy .

check-all: format lint type-check test ## Run all checks (format, lint, type-check, test)

clean: ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf dist/ build/ htmlcov/ .coverage

update: ## Update all dependencies
	poetry update

lock: ## Update poetry.lock without installing
	poetry lock --no-update

shell: ## Activate Poetry virtual environment
	poetry shell

docker-build: ## Build Docker image
	docker build -t nebula-translate-backend .

docker-run: ## Run Docker container with fixed name
	docker run --rm --name nebula-translate-backend -p 8000:8000 --env-file .env nebula-translate-backend

docker-run-detached: ## Run Docker container in background
	docker run -d --rm --name nebula-translate-backend -p 8000:8000 --env-file .env nebula-translate-backend

docker-down: ## Stop and remove running Docker container
	@docker stop nebula-translate-backend 2>/dev/null || true
	@docker rm nebula-translate-backend 2>/dev/null || true

docker-logs: ## View Docker container logs
	docker logs -f nebula-translate-backend

docker-stop: ## Stop Docker container
	docker stop nebula-translate-backend

docker-restart: ## Restart Docker container
	docker restart nebula-translate-backend

docker-clean: ## Remove all stopped nebula-translate containers
	@docker ps -a | grep nebula-translate-backend | awk '{print $$1}' | xargs docker rm 2>/dev/null || true
	@echo "✓ Cleaned up stopped containers"

setup: install ## Initial setup (install dependencies)
	@echo "✓ Dependencies installed"
	@echo "✓ Pipecat submodule installed"
	@echo ""
	@echo "Next steps:"
	@echo "  1. cp .env.example .env"
	@echo "  2. Edit .env with your API keys"
	@echo "  3. make dev"
