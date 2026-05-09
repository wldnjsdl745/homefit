FRONTEND_DIR := frontend
AI_DIR := ai-server
NPM := npm --prefix $(FRONTEND_DIR)
COMPOSE := docker compose
SEED_DATA ?= seed-data.sql

.PHONY: help
help:
	@printf "Homefit commands\n"
	@printf "  make frontend-install   Install frontend dependencies\n"
	@printf "  make frontend-dev       Run frontend dev server\n"
	@printf "  make frontend-build     Type-check and build frontend\n"
	@printf "  make frontend-test      Run frontend unit/component tests\n"
	@printf "  make frontend-test-watch Run frontend tests in watch mode\n"
	@printf "  make frontend-lint      Run frontend lint\n"
	@printf "  make frontend-check     Run lint, tests, and build\n"
	@printf "  make docker-build       Build frontend Docker image\n"
	@printf "  make docker-frontend-install Install frontend dependencies through Docker\n"
	@printf "  make docker-up          Run frontend dev server in Docker\n"
	@printf "  make docker-up-detached Run frontend dev server in Docker background\n"
	@printf "  make docker-down        Stop Docker services\n"
	@printf "  make docker-db-up       Run Docker MySQL only\n"
	@printf "  make docker-db-import   Import seed-data.sql into Docker MySQL\n"
	@printf "  make docker-db-backup   Export Docker MySQL data to backup-data.sql\n"
	@printf "  make docker-db-shell    Open Docker MySQL shell\n"
	@printf "  make docker-down-volumes Stop services and remove Docker volumes\n"
	@printf "  make docker-frontend-test Run frontend tests in Docker\n"
	@printf "  make docker-frontend-lint Run frontend lint in Docker\n"
	@printf "  make docker-frontend-build Build frontend app in Docker\n"
	@printf "  make docker-frontend-check Run Docker lint, tests, and build\n"
	@printf "  make docker-ai-test    Run AI server tests in Docker\n"
	@printf "  make docker-ai-lint    Run AI server lint in Docker\n"
	@printf "  make docker-ai-check   Run AI server lint and tests in Docker\n"

.PHONY: frontend-install
frontend-install:
	$(NPM) install

.PHONY: frontend-dev
frontend-dev:
	$(NPM) run dev -- --host 0.0.0.0

.PHONY: frontend-build
frontend-build:
	$(NPM) run build

.PHONY: frontend-test
frontend-test:
	$(NPM) run test

.PHONY: frontend-test-watch
frontend-test-watch:
	$(NPM) run test:watch

.PHONY: frontend-lint
frontend-lint:
	$(NPM) run lint

.PHONY: frontend-check
frontend-check: frontend-lint frontend-test frontend-build

.PHONY: docker-build
docker-build:
	$(COMPOSE) build frontend ai-server backend

.PHONY: docker-frontend-install
docker-frontend-install:
	$(COMPOSE) run --rm frontend npm install

.PHONY: docker-up
docker-up:
	$(COMPOSE) up frontend ai-server

.PHONY: docker-up-detached
docker-up-detached:
	$(COMPOSE) up -d frontend ai-server

.PHONY: docker-down
docker-down:
	$(COMPOSE) down

.PHONY: docker-db-up
docker-db-up:
	$(COMPOSE) up -d db

.PHONY: docker-db-import
docker-db-import:
	@test -f $(SEED_DATA) || (printf "$(SEED_DATA) not found. Create it with mysqldump --no-create-info first.\n" && exit 1)
	$(COMPOSE) up -d db
	$(COMPOSE) exec -T db sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"' < $(SEED_DATA)

.PHONY: docker-db-backup
docker-db-backup:
	$(COMPOSE) up -d db
	$(COMPOSE) exec -T db sh -c 'mysqldump --no-create-info --single-transaction -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE" regions housing_transactions' > backup-data.sql

.PHONY: docker-db-shell
docker-db-shell:
	$(COMPOSE) exec db sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'

.PHONY: docker-down-volumes
docker-down-volumes:
	$(COMPOSE) down -v

.PHONY: docker-frontend-test
docker-frontend-test:
	$(COMPOSE) run --rm frontend npm run test

.PHONY: docker-frontend-lint
docker-frontend-lint:
	$(COMPOSE) run --rm frontend npm run lint

.PHONY: docker-frontend-build
docker-frontend-build:
	$(COMPOSE) run --rm frontend npm run build

.PHONY: docker-frontend-check
docker-frontend-check: docker-frontend-lint docker-frontend-test docker-frontend-build

.PHONY: docker-ai-test
docker-ai-test:
	$(COMPOSE) run --rm ai-server pytest

.PHONY: docker-ai-lint
docker-ai-lint:
	$(COMPOSE) run --rm ai-server ruff check app tests

.PHONY: docker-ai-check
docker-ai-check: docker-ai-lint docker-ai-test
