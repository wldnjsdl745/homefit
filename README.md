# Homefit

국토교통부 공공데이터 기반 주거 지역 추천 챗봇 MVP입니다.

## Database Strategy

DB는 환경에 따라 분리합니다.

```text
개발: Docker MySQL
운영/배포: Amazon RDS MySQL
```

개발에서는 `docker-compose.yml`의 `db` 서비스와 `db-seed` 서비스를 사용합니다.

운영 EC2에서는 Docker와 MySQL을 올리지 않고, Backend가 RDS endpoint로 직접 연결합니다.

운영 Backend 환경변수 예시:

```sh
SPRING_DATASOURCE_URL=jdbc:mysql://your-rds-endpoint.ap-northeast-2.rds.amazonaws.com:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8
SPRING_DATASOURCE_USERNAME=homefit
SPRING_DATASOURCE_PASSWORD=your_rds_password
```

이미 테이블이 생성된 RDS를 처음 연결하는 경우에는 Backend가 핵심 테이블 존재 여부를 확인합니다.
`regions`, `housing_transactions`, `chat_messages`, `housing_transactions.sale_price_amount`가 있고 Flyway 이력이 없으면 현재 스키마를 자동으로 `V3` baseline으로 등록합니다.

기존 RDS에 실패한 Flyway 이력이 남아 있으면 먼저 이력만 확인/정리합니다. 데이터 테이블은 삭제하지 않습니다.

```sh
make rds-flyway-history RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com RDS_PASSWORD=your_rds_password
make rds-flyway-adopt-v3 RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com RDS_PASSWORD=your_rds_password CONFIRM_DROP_FLYWAY_HISTORY=yes
```

RDS 데이터 확인:

```sh
make rds-count RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com RDS_PASSWORD=your_rds_password
```

운영 systemd 예시:

- [backend.service.example](deploy/systemd/backend.service.example)
- [ai-server.service.example](deploy/systemd/ai-server.service.example)

## Frontend

프론트엔드는 `frontend/` 디렉터리에 있으며 React, TypeScript, Vite, Tailwind CSS 기반입니다.

### Docker로 실행

```bash
make docker-up-detached
```

브라우저에서 아래 주소로 접속합니다.

```txt
http://localhost:5173
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
