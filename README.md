# Homefit

국토교통부 공공데이터 기반 주거 지역 추천 챗봇 MVP입니다.

## Frontend

프론트엔드는 `frontend/` 디렉터리에 있으며 React, TypeScript, Vite, Tailwind CSS 기반입니다.

### Docker로 실행

```bash
make docker-up-detached
```

브라우저에서 아래 주소로 접속합니다.

```txt
http://localhost:5173/
```

로그 확인:

```bash
docker compose logs -f frontend
```

중지:

```bash
make docker-down
```

### Frontend 검증

lint, test, build를 한 번에 실행합니다.

```bash
make docker-frontend-check
```

개별 실행:

```bash
make docker-frontend-lint
make docker-frontend-test
make docker-frontend-build
```

### 로컬 npm 실행

Docker 없이 로컬 Node 환경에서 실행할 수도 있습니다.

```bash
make frontend-install
make frontend-dev
```

로컬 검증:

```bash
make frontend-check
```

## AI Server

AI 서버는 `ai-server/` 디렉터리에 있으며 FastAPI 기반입니다. MVP에서는 LLM을 호출하지 않고, mock backend 모드로 `/chat` 응답을 생성합니다.

### Docker로 실행

프론트와 AI 서버를 함께 실행합니다.

```bash
make docker-up-detached
```

AI 서버 헬스체크:

```bash
curl http://localhost:8000/healthz
```

### AI Server 검증

```bash
make docker-ai-check
```

개별 실행:

```bash
make docker-ai-lint
make docker-ai-test
```

### 앱 / AI / LLM 분리 실행

프론트 앱 스택만 실행합니다. Backend 서비스가 compose에 추가되면 같은 app stack에 붙이면 됩니다.

```bash
make app-up
```

AI 서버만 실행합니다.

```bash
make ai-up
```

Qwen 모델 런타임은 별도 compose 파일로 실행합니다. 기본 모델은 `Qwen/Qwen3.5-2B`이며 OpenAI-compatible API를 제공합니다.

```bash
make llm-up
```

모델 캐시 확인 또는 다운로드:

```bash
make llm-model-check
```

Qwen provider를 AI 서버에서 의미 추출용으로 사용하려면 아래 환경변수를 설정합니다.

```bash
AI_PROVIDER=qwen
OPENAI_BASE_URL=http://llm-runtime:8000/v1
OPENAI_MODEL=Qwen/Qwen3.5-2B
LLM_PROMPT_STYLE=hermes
```

Qwen/Hermes는 사용자 자연어를 `raw conditions`로 추출하는 데만 사용합니다. 지역 추천, 필터링, 정렬은 Backend 책임입니다.
