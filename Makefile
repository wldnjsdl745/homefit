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
RDS_HOST ?=
RDS_PORT ?= 3306
RDS_DATABASE ?= homefit
RDS_USER ?= homefit
RDS_PASSWORD ?=

.PHONY: help
help:
	@printf "Homefit commands\n"
	@printf "\n"
	@printf "  ── 전체 스택 (한 번에) ──\n"
	@printf "  make up                 Bring up the full stack (frontend / ai-server / backend / db) detached\n"
	@printf "  make down               Stop and remove all stack containers\n"
	@printf "  make logs               Tail logs for the full stack\n"
	@printf "  make ps                 Show stack container status\n"
	@printf "  make restart            Restart the full stack\n"
	@printf "  make build              Build all docker images\n"
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
	@printf "  make rds-count          Count regions and housing_transactions in RDS\n"
	@printf "  make rds-import-seed    Import db/seed seed data into RDS\n"
	@printf "  make rds-shell          Open RDS MySQL shell\n"
	@printf "  make docker-down-volumes Stop services and remove Docker volumes\n"
	@printf "\n"
	@printf "  ── 개별 서비스 컨트롤 ──\n"
	@printf "  make frontend-up / frontend-down\n"
	@printf "  make ai-up / ai-down\n"

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

.PHONY: rds-count
rds-count:
	@test -n "$(RDS_HOST)" || (printf "RDS_HOST is required.\n" && exit 1)
	@test -n "$(RDS_PASSWORD)" || (printf "RDS_PASSWORD is required.\n" && exit 1)
	MYSQL_PWD="$(RDS_PASSWORD)" mysql -h "$(RDS_HOST)" -P "$(RDS_PORT)" -u "$(RDS_USER)" "$(RDS_DATABASE)" \
	  -e "select count(*) as regions from regions; select count(*) as housing_transactions from housing_transactions;"

.PHONY: rds-import-seed
rds-import-seed:
	@test -f $(SEED_ARCHIVE) -o -f $(SEED_DIR)/seed-data.sql || (printf "$(SEED_ARCHIVE) or $(SEED_DIR)/seed-data.sql not found. Run make docker-db-pack first.\n" && exit 1)
	@test -n "$(RDS_HOST)" || (printf "RDS_HOST is required.\n" && exit 1)
	@test -n "$(RDS_PASSWORD)" || (printf "RDS_PASSWORD is required.\n" && exit 1)
	@if [ -f "$(SEED_ARCHIVE)" ]; then \
	  gzip -dc "$(SEED_ARCHIVE)" | MYSQL_PWD="$(RDS_PASSWORD)" mysql -h "$(RDS_HOST)" -P "$(RDS_PORT)" -u "$(RDS_USER)" "$(RDS_DATABASE)"; \
	else \
	  MYSQL_PWD="$(RDS_PASSWORD)" mysql -h "$(RDS_HOST)" -P "$(RDS_PORT)" -u "$(RDS_USER)" "$(RDS_DATABASE)" < "$(SEED_DIR)/seed-data.sql"; \
	fi

.PHONY: rds-shell
rds-shell:
	@test -n "$(RDS_HOST)" || (printf "RDS_HOST is required.\n" && exit 1)
	@test -n "$(RDS_PASSWORD)" || (printf "RDS_PASSWORD is required.\n" && exit 1)
	MYSQL_PWD="$(RDS_PASSWORD)" mysql -h "$(RDS_HOST)" -P "$(RDS_PORT)" -u "$(RDS_USER)" "$(RDS_DATABASE)"

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
