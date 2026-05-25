# Homefit

국토교통부 공공데이터 기반 주거 지역 추천 챗봇 MVP입니다.

## Database Strategy

DB는 환경에 따라 분리합니다.

```text
개발: Docker MySQL
운영/배포: Amazon RDS MySQL
```

개발에서는 `docker-compose.yml`의 `db` 서비스와 `db-seed` 서비스를 사용합니다.

운영 EC2에서는 Docker MySQL을 올리지 않고, Backend가 RDS endpoint로 직접 연결합니다.

운영 Backend 환경변수 예시:

```sh
SPRING_DATASOURCE_URL=jdbc:mysql://your-rds-endpoint.ap-northeast-2.rds.amazonaws.com:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8
SPRING_DATASOURCE_USERNAME=homefit
SPRING_DATASOURCE_PASSWORD=your_rds_password
```

운영 RDS는 스키마와 초기 데이터를 포함한 dump 파일을 import한 뒤 Backend가 연결합니다.
Backend는 DB schema 변경 작업을 실행하지 않습니다.

RDS 데이터 확인:

```sh
make rds-count RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com RDS_PASSWORD=your_rds_password
```

운영 systemd 예시:

- [backend.service.example](deploy/systemd/backend.service.example)
- [ai-server.service.example](deploy/systemd/ai-server.service.example)

## Production Deploy on AWS EC2

운영 배포는 `docker-compose.prod.yml`을 사용합니다.

운영 compose는 아래 서비스만 실행합니다.

```text
frontend: 80 포트 공개
ai-server: Docker 내부 통신만 사용
backend: Docker 내부 통신만 사용, DB는 Amazon RDS 연결
```

로컬 개발용 `db`, `db-seed` 서비스는 운영 compose에 포함하지 않습니다.

### 1. 서버 접속

```bash
ssh homefit
cd ~/homefit
```

### 2. 기존 개발용 스택 정리

기존에 `docker-compose.yml`로 실행한 컨테이너가 있으면 먼저 내립니다.

```bash
sudo docker-compose down
```

### 3. 최신 코드 반영

```bash
git pull
```

### 4. 운영 `.env` 설정

```bash
nano .env
```

운영 서버의 `.env`에는 최소한 아래 값이 필요합니다.

```env
SPRING_DATASOURCE_URL=jdbc:mysql://your-rds-endpoint.ap-northeast-2.rds.amazonaws.com:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8&useSSL=false
SPRING_DATASOURCE_USERNAME=homefit
SPRING_DATASOURCE_PASSWORD=your_rds_password

AI_BACKEND_MODE=http
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=your_openrouter_api_key
OPENAI_MODEL=qwen/qwen-2.5-72b-instruct:free
LLM_TIMEOUT_MS=30000
LLM_PROMPT_STYLE=hermes

CORS_ALLOW_ORIGINS=http://your-ec2-public-ip
VITE_USE_MOCK_CHAT=false
```

`frontend`는 nginx가 `/chat` 요청을 `ai-server`로 프록시하므로 운영에서는 `VITE_API_BASE_URL`을 비워두거나 생략할 수 있습니다.

### 5. 첫 배포 실행

첫 배포 또는 Dockerfile 변경 후에는 이미지를 빌드합니다.

```bash
sudo docker-compose -f docker-compose.prod.yml up -d --build
```

### 6. 이후 재시작

이미 빌드된 이미지로 다시 실행할 때는 빌드 없이 실행합니다.

```bash
sudo docker-compose -f docker-compose.prod.yml up -d
```

### 7. 상태와 로그 확인

```bash
sudo docker-compose -f docker-compose.prod.yml ps
sudo docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

개별 서비스 로그:

```bash
sudo docker-compose -f docker-compose.prod.yml logs -f backend
sudo docker-compose -f docker-compose.prod.yml logs -f ai-server
sudo docker-compose -f docker-compose.prod.yml logs -f frontend
```

### 8. 운영 스택 중지

```bash
sudo docker-compose -f docker-compose.prod.yml down
```

### AWS 보안 그룹

EC2 보안 그룹은 앱 접속용 `80` 포트만 공개합니다.

```text
EC2 inbound: 80
RDS inbound: 3306 from EC2 security group
```

`8000`, `8080`, `3307`은 외부에 공개하지 않습니다.

서버에 Docker Compose v2 플러그인이 설치되어 있으면 `docker-compose` 대신 `docker compose`를 사용할 수 있습니다.

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
