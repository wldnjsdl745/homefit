FRONTEND_DIR := frontend
AI_DIR := ai-server
NPM := npm --prefix $(FRONTEND_DIR)
COMPOSE := docker compose
LLM_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.llm.yml

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
	@printf "  make docker-ai-test    Run AI server tests in Docker\n"
	@printf "  make docker-ai-lint    Run AI server lint in Docker\n"
	@printf "  make docker-ai-check   Run AI server lint and tests in Docker\n"
	@printf "  make app-up            Run app stack: frontend (backend can be added later)\n"
	@printf "  make app-down          Stop app stack\n"
	@printf "  make app-check         Run frontend checks\n"
	@printf "  make ai-up             Run AI server only\n"
	@printf "  make ai-down           Stop AI server\n"
	@printf "  make ai-check          Run AI server checks\n"
	@printf "  make llm-up            Run OpenAI-compatible Qwen runtime\n"
	@printf "  make llm-down          Stop Qwen runtime\n"
	@printf "  make llm-model-check   Download/check configured Qwen model cache\n"

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
	$(COMPOSE) build frontend ai-server

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

.PHONY: app-up
app-up:
	$(COMPOSE) up -d frontend

.PHONY: app-down
app-down:
	$(COMPOSE) stop frontend

.PHONY: app-check
app-check: docker-frontend-check

.PHONY: ai-up
ai-up:
	$(COMPOSE) up -d ai-server

.PHONY: ai-down
ai-down:
	$(COMPOSE) stop ai-server

.PHONY: ai-check
ai-check: docker-ai-check

.PHONY: llm-up
llm-up:
	$(LLM_COMPOSE) up -d llm-runtime

.PHONY: llm-down
llm-down:
	$(LLM_COMPOSE) stop llm-runtime

.PHONY: llm-model-check
llm-model-check:
	$(LLM_COMPOSE) run --rm --entrypoint python llm-runtime -c "from huggingface_hub import snapshot_download; import os; model=os.environ.get('OPENAI_MODEL','Qwen/Qwen3.5-2B'); print(f'Checking model: {model}'); print(snapshot_download(model))"
