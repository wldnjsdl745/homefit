# homefit 협업 규칙

- 문서 버전: `v0.1.0`
- 작성일: `2026-05-22`
- 문서 상태: `Draft`
- 적용 범위: `MVP v0`

---

## 0. 문서 목적

본 문서는 homefit 프로젝트 협업 시 지켜야 할 공통 규칙을 정리합니다.

대상 범위:

- Git 작업 규칙
- 문서 관리 규칙
- 환경변수 관리 규칙
- DB seed 데이터 관리 규칙
- API/Backend/AI/Frontend 협업 규칙
- 로컬 실행 및 검증 규칙

---

## 1. 기준 문서 우선순위

기능을 수정할 때는 아래 순서로 기준을 확인합니다.

1. [API.md](../api/API.md)
2. 실제 구현 코드
3. 관련 draft 문서
4. README

API 계약이 바뀌면 먼저 [API.md](../api/API.md)를 수정합니다.

실제 구현이 API 문서와 다르면 아래 중 하나로 처리합니다.

- API 문서가 맞고 구현이 뒤처진 경우: 구현 TODO로 남깁니다.
- 구현이 맞고 API 문서가 오래된 경우: API 문서를 먼저 수정합니다.
- 판단이 애매한 경우: `docs/api/API-PLAN.md`에 변경 계획을 먼저 작성합니다.

---

## 2. Git 작업 규칙

## 2.1 Pull 정책

`git pull` 시 divergent branches 오류가 발생할 수 있습니다.

팀에서 별도 합의가 없다면 아래 중 하나를 명시해서 사용합니다.

```sh
git pull --rebase
```

또는 전역 설정:

```sh
git config --global pull.rebase true
```

remote branch 충돌 또는 오래된 ref 오류가 발생하면 아래 명령으로 정리합니다.

```sh
git remote prune origin
```

## 2.2 변경 전 확인

작업 전에는 현재 변경 상태를 확인합니다.

```sh
git status --short
```

다른 사람이 수정한 파일을 임의로 되돌리지 않습니다.

특히 아래 명령은 명확한 목적 없이 사용하지 않습니다.

```sh
git reset --hard
git checkout -- <file>
```

## 2.3 커밋 단위

커밋은 목적 단위로 나눕니다.

예시:

- API 명세 수정
- Backend migration 수정
- seed 자동화 수정
- 문서 추가

문서만 수정한 작업과 코드 수정 작업은 가능하면 분리합니다.

---

## 3. 문서 관리 규칙

## 3.1 문서 위치

| 문서 | 위치 |
|---|---|
| API 명세 | `docs/api/API.md` |
| API 변경 계획 | `docs/api/API-PLAN.md` |
| 아키텍처 문서 | `docs/architecture/architecture.md` |
| 협업 규칙 | `docs/convention/convention.md` |
| ERD | `docs/data/ERD.md` |
| 초안/기획 문서 | `docs/drafts/` |

## 3.2 API 변경 규칙

API 계약이 바뀌면 아래 순서로 진행합니다.

1. `docs/api/API-PLAN.md`에 변경 계획 작성
2. 합의 후 `docs/api/API.md` 수정
3. AI Server / Backend / Frontend 구현 반영
4. 테스트 또는 수동 검증

예시:

- `deal_type`에 `sale` 추가
- condition item에 `monthly_rent_max` 추가
- 서울 내부 추천 제한 추가

## 3.3 문서 작성 스타일

- 실제 명령어는 코드블록으로 작성합니다.
- 환경변수, 파일명, API path는 백틱으로 감쌉니다.
- 아직 구현되지 않은 내용은 “현재 구현 상태” 또는 “TODO”로 구분합니다.
- 운영 배포 관련 내용은 비용 발생 가능성을 함께 적습니다.

---

## 4. 환경변수 관리 규칙

## 4.1 파일 위치

환경변수 파일은 프로젝트 루트 기준으로 관리합니다.

```text
homefit/
  .env
  .env.example
  .gitignore
```

패키지별 예시 파일은 필요 시 유지합니다.

```text
frontend/.env.example
ai-server/.env.example
```

## 4.2 Git 포함 여부

| 파일 | Git 포함 | 설명 |
|---|---|---|
| `.env` | 아니오 | 실제 로컬 비밀값 |
| `.env.local` | 아니오 | 개인 로컬 override |
| `.env.example` | 예 | 공유용 예시값 |
| `.gitignore` | 예 | ignore 규칙 |

`.env`에는 실제 API key, DB password가 들어갈 수 있으므로 커밋하지 않습니다.

`.env.example`에는 실제 키를 넣지 않습니다.

## 4.3 주요 환경변수

| 변수 | 사용처 |
|---|---|
| `VITE_API_BASE_URL` | Frontend -> AI Server |
| `VITE_USE_MOCK_CHAT` | Frontend mock 여부 |
| `BACKEND_URL` | AI Server -> Backend |
| `AI_PROVIDER` | LLM provider 선택 |
| `OPENAI_BASE_URL` | OpenAI 호환 API base URL |
| `OPENAI_API_KEY` | 외부 LLM API key |
| `OPENAI_MODEL` | LLM model |
| `SPRING_DATASOURCE_URL` | Backend DB URL |
| `SPRING_DATASOURCE_USERNAME` | Backend DB user |
| `SPRING_DATASOURCE_PASSWORD` | Backend DB password |

---

## 5. DB Seed 관리 규칙

DB 사용 전략:

```text
개발: Docker MySQL
운영/배포: Amazon RDS MySQL
```

## 5.1 seed 파일 위치

Docker DB 자동 import용 seed 파일은 아래 위치에 둡니다.

```text
db/seed/seed-data.sql.gz
```

압축하지 않은 파일도 사용할 수 있습니다.

```text
db/seed/seed-data.sql
```

권장 파일은 `seed-data.sql.gz`입니다.

## 5.2 Git 포함 여부

seed dump 파일은 용량이 크고 데이터가 자주 바뀔 수 있으므로 Git에 올리지 않습니다.

루트 `.gitignore`는 아래 파일들을 제외합니다.

```text
*.sql
*.sql.gz
```

단, Flyway migration SQL은 예외로 Git에 포함합니다.

```text
!backend/src/main/resources/db/migration/*.sql
```

## 5.3 로컬 MySQL -> Docker DB 동기화

로컬 MySQL 데이터를 Docker DB에 다시 반영할 때는 아래 명령을 사용합니다.

```sh
make docker-db-refresh-from-local
```

이 명령의 역할:

1. 로컬 MySQL의 `regions`, `housing_transactions` 데이터를 dump
2. `db/seed/seed-data.sql.gz` 생성
3. Docker backend를 빌드/실행해서 Flyway migration 적용
4. Docker DB의 seed 대상 테이블을 비우고 새 데이터 import

주의:

- Docker DB의 기존 `regions`, `housing_transactions` 데이터는 덮어씁니다.
- `docker compose down -v`는 모든 Docker volume을 지우므로 seed 갱신 목적으로는 사용하지 않습니다.

## 5.4 seed import 확인

개발 Docker DB에 seed 데이터가 들어갔는지 확인할 때는 아래 쿼리를 사용합니다.

```sh
docker compose exec db sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "select count(*) as regions from regions; select count(*) as housing_transactions from housing_transactions;"'
```

운영 RDS에 seed 데이터를 import하거나 확인할 때는 아래 명령을 사용합니다.

```sh
make rds-import-seed RDS_HOST=<rds-endpoint> RDS_PASSWORD=<password>
make rds-count RDS_HOST=<rds-endpoint> RDS_PASSWORD=<password>
```

---

## 6. Backend 협업 규칙

Backend 기준:

- Java 21
- Spring Boot 3.5.14
- Gradle
- MySQL
- Flyway

주요 책임:

- 내부 API 제공
- conditions 저장
- 거래 데이터 필터링
- DB migration

Backend는 Frontend가 직접 호출하지 않습니다.

공개되어도 되는 경로:

- `/healthz`
- `/actuator/health`

내부 전용 경로:

- `/internal/upsert-conditions`
- `/internal/filter`

운영 배포에서는 `/internal/**`를 외부에 노출하지 않습니다.

---

## 7. AI Server 협업 규칙

AI Server는 Frontend의 유일한 API 진입점입니다.

주요 책임:

- `POST /chat` 제공
- 대화 흐름 제어
- Backend 내부 API 호출
- LLM provider 연동
- fallback 응답 생성

운영에서는 EC2 micro 인스턴스에서 Ollama 같은 로컬 LLM을 직접 실행하지 않습니다.

운영 기본 방향:

```text
AI Server -> external OpenAI-compatible LLM API
```

로컬 Ollama는 개발 또는 실험용으로만 사용합니다.

---

## 8. Frontend 협업 규칙

Frontend는 AI Server만 호출합니다.

주요 책임:

- 채팅 UI 렌더링
- 사용자 입력 수집
- quick reply chip을 `raw`로 변환
- AI Server 응답의 `bot_messages` 렌더링

Frontend에서 Backend 내부 API를 직접 호출하지 않습니다.

`VITE_USE_MOCK_CHAT` 설정:

| 값 | 동작 |
|---|---|
| `false` | 실제 AI Server 호출 |
| 그 외 | MockChatServer 사용 |

---

## 9. 로컬 실행 규칙

전체 스택 실행:

```sh
make docker-up-detached
```

또는:

```sh
docker compose up frontend ai-server
```

중지:

```sh
make docker-down
```

주의:

```sh
docker compose down -v
```

위 명령은 MySQL 데이터뿐 아니라 Compose volume 전체를 삭제할 수 있습니다.

DB만 갱신하려면 seed refresh 명령을 사용합니다.

---

## 10. 검증 규칙

변경 범위에 따라 필요한 검증을 실행합니다.

Frontend:

```sh
make docker-frontend-check
```

AI Server:

```sh
make docker-ai-check
```

Backend:

```sh
cd backend
./gradlew test
```

문서만 수정한 경우에는 최소한 Markdown diff와 링크 경로를 확인합니다.

---

## 11. 현재 정합성 주의사항

아래 항목은 API 명세와 실제 구현이 완전히 일치하는지 계속 확인해야 합니다.

| 항목 | 주의사항 |
|---|---|
| `deal_type=sale` | API와 Backend는 반영되었지만 AI/FE 지원 상태 확인 필요 |
| `monthly_rent_max` | API에는 있으나 전체 구현 반영 상태 확인 필요 |
| 서울 내부 추천 제한 | DB 데이터와 Backend query 중 어디서 보장할지 명확히 해야 함 |
| 매매 가격 컬럼 | 실제 Backend는 `sale_price_amount`를 사용 |
| AI Server session state | 현재 일부 대화 step이 메모리 기반일 수 있음 |
| 내부 API 보안 | 운영에서는 네트워크 제한 또는 내부 토큰 필요 |

---

## 12. 운영 배포 협업 규칙

초기 운영 배포는 비용을 줄이기 위해 아래 구성을 우선합니다.

```text
EC2 1대 + RDS MySQL 1대
```

초기에는 사용하지 않습니다.

- ALB
- NAT Gateway
- Multi-AZ
- Read Replica
- Performance Insights
- Enhanced Monitoring
- Container Insights

EC2에는 Docker를 올리지 않습니다.

Backend와 AI Server는 같은 EC2 안에서 각각 systemd service로 실행합니다.

LLM은 EC2에서 직접 실행하지 않고 외부 LLM API를 호출합니다.

로그는 EC2 로컬 로그(`/var/log/homefit/`, `/var/log/nginx/`, `journalctl`)로 확인합니다.
