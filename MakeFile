.PHONY: help \
	install install-dev install-prod install-test \
	run shell migrate makemigrations collectstatic createsuperuser \
	test test-cov \
	docker-build docker-up docker-down docker-logs docker-shell docker-migrate docker-restart \
	prod-build prod-up prod-down prod-logs prod-restart \
	lint format clean

# ─── Config ──────────────────────────────────────────────────────────────────
PYTHON     = python
MANAGE     = $(PYTHON) manage.py
DC         = docker compose -f docker-compose.yml
DC_PROD    = docker compose --env-file .env.prod -f docker-compose.prod.yml
CONTAINER  = chic_transfer_api_dev
CONTAINER_PROD = chic_transfer_api

# ─── Help ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Usage: make <command>"
	@echo ""
	@echo "  Local Development"
	@echo "    install           Install development dependencies"
	@echo "    run               Start the Django dev server"
	@echo "    shell             Open Django shell"
	@echo "    migrate           Apply migrations"
	@echo "    makemigrations    Create new migrations"
	@echo "    collectstatic     Collect static files"
	@echo "    createsuperuser   Create a superuser"
	@echo ""
	@echo "  Testing"
	@echo "    test              Run test suite"
	@echo "    test-cov          Run tests with coverage report"
	@echo ""
	@echo "  Docker (dev)"
	@echo "    docker-build      Build dev image"
	@echo "    docker-up         Start dev stack"
	@echo "    docker-down       Stop dev stack"
	@echo "    docker-logs       Tail dev logs"
	@echo "    docker-shell      Shell into web container"
	@echo "    docker-migrate    Run migrations in container"
	@echo "    docker-restart    Restart web container"
	@echo ""
	@echo "  Docker (prod)"
	@echo "    prod-build        Build prod image"
	@echo "    prod-up           Start prod stack"
	@echo "    prod-down         Stop prod stack"
	@echo "    prod-logs         Tail prod logs"
	@echo "    prod-restart      Restart prod web container"
	@echo ""
	@echo "  Code Quality"
	@echo "    lint              Run flake8"
	@echo "    format            Run black + isort"
	@echo "    clean             Remove .pyc files and __pycache__"
	@echo ""

# ─── Local Development ───────────────────────────────────────────────────────
install:
	pip install -r requirements/development.txt

install-prod:
	pip install -r requirements/production.txt

install-test:
	pip install -r requirements/testing.txt

run:
	$(MANAGE) runserver

shell:
	$(MANAGE) shell

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

collectstatic:
	$(MANAGE) collectstatic --noinput

createsuperuser:
	$(MANAGE) createsuperuser

# ─── Testing ─────────────────────────────────────────────────────────────────
test:
	pytest

test-cov:
	pytest --cov=apps --cov-report=term-missing

# ─── Docker (dev) ────────────────────────────────────────────────────────────
docker-build:
	$(DC) build

docker-up:
	$(DC) up -d

docker-down:
	$(DC) down

docker-logs:
	$(DC) logs -f web

docker-shell:
	docker exec -it $(CONTAINER) bash

docker-migrate:
	docker exec $(CONTAINER) python manage.py migrate

docker-restart:
	$(DC) restart web

# ─── Docker (prod) ───────────────────────────────────────────────────────────
prod-build:
	$(DC_PROD) build

prod-up:
	$(DC_PROD) up -d

prod-down:
	$(DC_PROD) down

prod-logs:
	$(DC_PROD) logs -f web

prod-restart:
	$(DC_PROD) restart web

# ─── Code Quality ────────────────────────────────────────────────────────────
lint:
	flake8 apps config

format:
	black apps config && isort apps config

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
