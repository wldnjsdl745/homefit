FRONTEND_DIR := frontend
NPM := npm --prefix $(FRONTEND_DIR)
COMPOSE := docker compose

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
	@printf "  make docker-frontend-test Run frontend tests in Docker\n"
	@printf "  make docker-frontend-lint Run frontend lint in Docker\n"
	@printf "  make docker-frontend-build Build frontend app in Docker\n"
	@printf "  make docker-frontend-check Run Docker lint, tests, and build\n"

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
	$(COMPOSE) build frontend

.PHONY: docker-frontend-install
docker-frontend-install:
	$(COMPOSE) run --rm frontend npm install

.PHONY: docker-up
docker-up:
	$(COMPOSE) up frontend

.PHONY: docker-up-detached
docker-up-detached:
	$(COMPOSE) up -d frontend

.PHONY: docker-down
docker-down:
	$(COMPOSE) down

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
