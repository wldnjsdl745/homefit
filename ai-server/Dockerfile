# ── base: 런타임 의존성만 (pytest/ruff 없음) ──────────────────────
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# OS 패키지 보안 패치 적용 후 캐시 제거
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# ── dev: 테스트·린트 도구 추가 (docker compose 개발 모드) ──────────
FROM base AS dev

RUN pip install --no-cache-dir ".[dev]"

COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# ── prod: 소스 직접 포함, 런타임만 ──────────────────────────────────
FROM base AS prod

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
