"""Makefile for common development tasks."""

.PHONY: help setup dev up down logs db-migrate db-reset clean test lint format

help:
	@echo "Ejicode BDP Development Commands"
	@echo "=================================="
	@echo "make setup        - Initial setup (copy .env, create volumes)"
	@echo "make dev          - Start development environment"
	@echo "make up           - Start services (docker-compose up)"
	@echo "make down         - Stop services"
	@echo "make logs         - Show service logs"
	@echo "make db-migrate   - Run database migrations"
	@echo "make db-reset     - Reset database (careful!)"
	@echo "make clean        - Remove volumes and containers"
	@echo "make test         - Run tests"
	@echo "make lint         - Run linters"
	@echo "make format       - Format code"

setup:
	@echo "Setting up Ejicode BDP..."
	@test -f .env || cp .env.example .env
	@mkdir -p data/postgres data/redis data/ollama data/chroma
	@echo "✅ Setup complete! Run 'make up' to start services"

dev: up
	@echo "Development environment started"
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Docs: http://localhost:8000/docs"

up:
	docker-compose up -d
	@echo "✅ Services started"

down:
	docker-compose down
	@echo "✅ Services stopped"

logs:
	docker-compose logs -f

db-migrate:
	docker-compose exec backend alembic upgrade head

db-reset:
	@read -p "Are you sure? This will delete all data (y/n): " confirm && \
	[ "$$confirm" = "y" ] && \
	docker-compose exec postgres psql -U bdp_user -d ejicode_bdp -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
	docker-compose exec backend alembic upgrade head

clean:
	docker-compose down -v
	rm -rf data/

test:
	docker-compose exec backend pytest tests/ -v

lint:
	docker-compose exec backend flake8 backend/ agents/
	docker-compose exec backend mypy backend/ agents/

format:
	docker-compose exec backend black backend/ agents/
	docker-compose exec backend isort backend/ agents/

.DEFAULT_GOAL := help
