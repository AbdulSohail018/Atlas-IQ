.PHONY: help dev build up down clean test lint format install-ollama seed

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment
	docker-compose up -d postgres neo4j redis prefect-server ollama
	@echo "Waiting for services to be ready..."
	@sleep 30
	$(MAKE) install-ollama
	docker-compose up backend frontend

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 30
	$(MAKE) install-ollama

down: ## Stop all services
	docker-compose down

clean: ## Clean up containers, volumes, and images
	docker-compose down -v --remove-orphans
	docker system prune -f

test: ## Run all tests
	cd backend && python -m pytest tests/ -v
	cd frontend && npm test

lint: ## Run linting
	cd backend && python -m flake8 app/
	cd backend && python -m mypy app/
	cd frontend && npm run lint

format: ## Format code
	cd backend && python -m black app/
	cd backend && python -m isort app/
	cd frontend && npm run format

install-ollama: ## Install and pull Ollama models
	@echo "Installing Ollama models..."
	docker-compose exec ollama ollama pull llama3.1:8b || true
	docker-compose exec ollama ollama pull nomic-embed-text || true

seed: ## Seed database with sample data
	docker-compose exec backend python -m app.scripts.seed_data

logs: ## Show logs for all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d glonav

neo4j-shell: ## Open Neo4j shell
	docker-compose exec neo4j cypher-shell -u neo4j -p password

backup: ## Backup all data
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres glonav > backups/postgres_$(shell date +%Y%m%d_%H%M%S).sql
	docker-compose exec neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/backups/
	@echo "Backup completed"

restore: ## Restore from backup (usage: make restore BACKUP_FILE=path/to/backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Please specify BACKUP_FILE=path/to/backup.sql"; exit 1; fi
	docker-compose exec postgres psql -U postgres -d glonav < $(BACKUP_FILE)

install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
	cd orchestration && pip install -r requirements.txt

docs: ## Generate documentation
	cd backend && python -m pdoc app/ -o ../docs/backend/
	cd frontend && npm run build-docs

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "Backend: DOWN"
	@curl -s http://localhost:3000 || echo "Frontend: DOWN"
	@curl -s http://localhost:4200/api/health || echo "Prefect: DOWN"
	@curl -s http://localhost:7474 || echo "Neo4j: DOWN"