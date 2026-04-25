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
