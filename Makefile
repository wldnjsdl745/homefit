FRONTEND_DIR := frontend
AI_DIR := ai-server
NPM := npm --prefix $(FRONTEND_DIR)
COMPOSE := docker compose
SEED_DATA ?= seed-data.sql
SEED_DIR ?= db/seed
SEED_ARCHIVE ?= $(SEED_DIR)/seed-data.sql.gz
LOCAL_MYSQL_HOST ?= localhost
LOCAL_MYSQL_PORT ?= 3306
LOCAL_MYSQL_USER ?= root
LOCAL_MYSQL_DATABASE ?= homefit

.PHONY: help
help:
	@printf "Homefit commands\n"
	@printf "\n"
	@printf "  ── 전체 스택 (한 번에) ──\n"
	@printf "  make up                 Bring up the full stack (frontend / ai-server / llm-runtime / backend / db) detached\n"
	@printf "  make down               Stop and remove all stack containers\n"
	@printf "  make logs               Tail logs for the full stack\n"
	@printf "  make ps                 Show stack container status\n"
	@printf "  make restart            Restart the full stack\n"
	@printf "  make build              Build all docker images\n"
	@printf "\n"
	@printf "  ── Qwen 통합 테스트 ──\n"
	@printf "  make qwen-test          Run Qwen integration tests against the running llm-runtime\n"
	@printf "  make qwen-smoke         Quick curl-based smoke test against /chat with raw_message\n"
	@printf "  make llm-list           List models inside the llm-runtime\n"
	@printf "  make llm-pull           Manually pull \$$OPENAI_MODEL into llm-runtime\n"
	@printf "\n"
	@printf "  ── Frontend ──\n"
	@printf "  make frontend-install   Install frontend dependencies\n"
	@printf "  make frontend-dev       Run frontend dev server (host)\n"
	@printf "  make frontend-build     Type-check and build frontend\n"
	@printf "  make frontend-test      Run frontend unit/component tests\n"
	@printf "  make frontend-lint      Run frontend lint\n"
	@printf "  make frontend-check     Lint + test + build\n"
	@printf "\n"
	@printf "  ── AI server ──\n"
	@printf "  make ai-test            Run ai-server unit tests in Docker\n"
	@printf "  make ai-lint            Run ai-server lint in Docker\n"
	@printf "  make ai-check           ai-server lint + unit tests\n"
	@printf "\n"
	@printf "  ── 데이터베이스 (Docker) ──\n"
	@printf "  make docker-db-up       Run Docker MySQL only\n"
	@printf "  make docker-db-pack     Compress seed-data.sql for automatic Docker seed import\n"
	@printf "  make docker-db-import   Import db/seed seed data into Docker MySQL when empty\n"
	@printf "  make docker-db-refresh-from-local Dump local MySQL data and force-import it into Docker MySQL\n"
	@printf "  make docker-db-backup   Export Docker MySQL data to backup-data.sql\n"
	@printf "  make docker-db-shell    Open Docker MySQL shell\n"
	@printf "  make docker-down-volumes Stop services and remove Docker volumes\n"
	@printf "\n"
	@printf "  ── 개별 서비스 컨트롤 ──\n"
	@printf "  make frontend-up / frontend-down\n"
	@printf "  make ai-up / ai-down\n"
	@printf "  make llm-up / llm-down\n"

# ─────────────────────────────────────────────────────────
#  전체 스택 (한 번에)
# ─────────────────────────────────────────────────────────

.PHONY: up
up:
	$(COMPOSE) up -d
	@echo ""
	@echo "✓ Stack starting. Tail logs with 'make logs'."
	@echo "  frontend:    http://localhost:5173"
	@echo "  ai-server:   http://localhost:8000"
	@echo "  backend:     http://localhost:8080"
	@echo "  llm-runtime: http://localhost:11434"

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: logs
logs:
	$(COMPOSE) logs -f --tail=50

.PHONY: ps
ps:
	$(COMPOSE) ps

.PHONY: restart
restart: down up

.PHONY: build
build:
	$(COMPOSE) build

# ─────────────────────────────────────────────────────────
#  Qwen 통합 테스트
# ─────────────────────────────────────────────────────────

# pytest 통합 테스트. 실제 Ollama 호출 → 케이스당 ~25-30초.
.PHONY: qwen-test
qwen-test:
	$(COMPOSE) up -d llm-runtime
	$(COMPOSE) run --rm ai-server pytest -m integration tests/integration -v -s

# curl로 빠른 smoke test (자본금 자연어 1회 호출).
.PHONY: qwen-smoke
qwen-smoke:
	@echo "[smoke] starting session..."
	@SID=$$(curl -fs -X POST http://localhost:8000/chat \
	  -H "Content-Type: application/json" \
	  -d '{"session_id":null,"raw":{}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"); \
	echo "[smoke] session_id=$$SID"; \
	echo "[smoke] sending '2억 정도 있어요' (Qwen 호출, 25-30초 소요)..."; \
	time curl -fs -X POST http://localhost:8000/chat \
	  -H "Content-Type: application/json" \
	  -d "{\"session_id\":\"$$SID\",\"raw\":{},\"raw_message\":\"2억 정도 있어요\"}" \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d,ensure_ascii=False,indent=2))"

.PHONY: llm-list
llm-list:
	$(COMPOSE) exec llm-runtime ollama list

.PHONY: llm-pull
llm-pull:
	$(COMPOSE) exec llm-runtime sh -c 'ollama pull "$${OLLAMA_MODEL:-qwen3.5:4b}"'

# ─────────────────────────────────────────────────────────
#  Frontend (host)
# ─────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────
#  Frontend (Docker)
# ─────────────────────────────────────────────────────────

.PHONY: docker-build
docker-build:
	$(COMPOSE) build frontend ai-server backend

.PHONY: docker-frontend-install
docker-frontend-install:
	$(COMPOSE) run --rm frontend npm install

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

# ─────────────────────────────────────────────────────────
#  AI server (Docker)
# ─────────────────────────────────────────────────────────

# Default pytest run (excludes integration tests via pyproject addopts).
.PHONY: ai-test
ai-test:
	$(COMPOSE) run --rm ai-server pytest

.PHONY: ai-lint
ai-lint:
	$(COMPOSE) run --rm ai-server ruff check app tests

.PHONY: ai-check
ai-check: ai-lint ai-test

# legacy aliases
.PHONY: docker-ai-test docker-ai-lint docker-ai-check
docker-ai-test: ai-test
docker-ai-lint: ai-lint
docker-ai-check: ai-check

# ─────────────────────────────────────────────────────────
#  데이터베이스 (Docker, develop branch에서 합류)
# ─────────────────────────────────────────────────────────

.PHONY: docker-db-up
docker-db-up:
	$(COMPOSE) up -d db

.PHONY: docker-db-pack
docker-db-pack:
	@test -f $(SEED_DATA) || (printf "$(SEED_DATA) not found. Create it with mysqldump first.\n" && exit 1)
	@mkdir -p $(SEED_DIR)
	gzip -c $(SEED_DATA) > $(SEED_ARCHIVE)
	@printf "Wrote $(SEED_ARCHIVE). This file is ignored by git; share it separately.\n"

.PHONY: docker-db-import
docker-db-import:
	@test -f $(SEED_ARCHIVE) -o -f $(SEED_DIR)/seed-data.sql || (printf "$(SEED_ARCHIVE) or $(SEED_DIR)/seed-data.sql not found. Run make docker-db-pack first.\n" && exit 1)
	$(COMPOSE) up -d backend
	$(COMPOSE) run --rm db-seed

.PHONY: docker-db-refresh-from-local
docker-db-refresh-from-local:
	@printf "Dumping local MySQL $(LOCAL_MYSQL_DATABASE).regions and $(LOCAL_MYSQL_DATABASE).housing_transactions into $(SEED_DATA)...\n"
	mysqldump --no-create-info --complete-insert --single-transaction \
	  -h $(LOCAL_MYSQL_HOST) \
	  -P $(LOCAL_MYSQL_PORT) \
	  -u $(LOCAL_MYSQL_USER) \
	  -p \
	  $(LOCAL_MYSQL_DATABASE) regions housing_transactions > $(SEED_DATA)
	$(MAKE) docker-db-pack
	$(COMPOSE) up -d --build backend
	$(COMPOSE) run --rm -e FORCE_SEED_IMPORT=true db-seed

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

# ─────────────────────────────────────────────────────────
#  개별 서비스 컨트롤
# ─────────────────────────────────────────────────────────

.PHONY: frontend-up
frontend-up:
	$(COMPOSE) up -d frontend

.PHONY: frontend-down
frontend-down:
	$(COMPOSE) stop frontend

.PHONY: ai-up
ai-up:
	$(COMPOSE) up -d ai-server

.PHONY: ai-down
ai-down:
	$(COMPOSE) stop ai-server

.PHONY: llm-up
llm-up:
	$(COMPOSE) up -d llm-runtime

.PHONY: llm-down
llm-down:
	$(COMPOSE) stop llm-runtime

# ─────────────────────────────────────────────────────────
#  legacy aliases (이전 README/스크립트 호환)
# ─────────────────────────────────────────────────────────

.PHONY: docker-up docker-up-detached docker-down app-up app-down app-check
docker-up:
	$(COMPOSE) up
docker-up-detached: up
docker-down: down
app-up: up
app-down: down
app-check: docker-frontend-check
