# homefit Architecture

- 문서 버전: `v0.1.0`
- 작성일: `2026-05-16`
- 문서 상태: `Draft`
- 적용 범위: `MVP v0`
- 기준 문서:
  - [API.md](../api/API.md)
  - [ERD.md](../../db/ERD.md)
  - 실제 구현 코드
    - [docker-compose.yml](../../docker-compose.yml)
    - [ai-server](../../ai-server)
    - [backend](../../backend)
    - [frontend](../../frontend)

---

## 0. 문서 목적

본 문서는 homefit MVP의 전체 요청 흐름과 서버 구성을 설명합니다.

다루는 범위는 아래와 같습니다.

- 전체 시스템 구조
- 컴포넌트별 역할
- 주요 요청 흐름
- 데이터 흐름
- 인증/보안 구조
- 인프라/배포 구조
- 외부 연동
- 주요 설정 결정
- API 명세와 현재 구현 간 정합성 확인 항목

기준 우선순위는 아래와 같습니다.

1. [docs/api/API.md](../api/API.md)에 정의된 API 계약
2. 현재 프로젝트에 구현된 코드

따라서 API 계약과 구현이 다른 경우, 본 문서는 목표 구조와 현재 구현 차이를 함께 기록합니다.

---

## 1. 전체 시스템 구조

homefit MVP의 논리 구조는 아래와 같습니다.

```text
User
  |
  v
Frontend
  |
  | POST /chat
  v
AI Server
  |
  | POST /internal/upsert-conditions
  | POST /internal/filter
  v
Backend
  |
  v
MySQL
```

핵심 원칙은 아래와 같습니다.

- FE는 AI Server만 호출합니다.
- Backend API는 내부 전용으로 사용합니다.
- AI Server는 사용자 대화 흐름을 제어하고 Backend를 호출합니다.
- Backend는 세션 조건 저장과 거래 데이터 필터링을 담당합니다.
- DB에는 추천 결과와 AI 응답 문장을 저장하지 않습니다.
- DB에는 사용자 입력 `raw`와 누적 조건 `conditions`만 저장합니다.

---

## 2. 로컬 개발 구성

현재 로컬 개발 환경은 Docker Compose 기준으로 구성되어 있습니다.

```text
frontend:5173
  |
  v
ai-server:8000
  |
  v
backend:8080
  |
  v
db:3306(container) / 3307(host)

optional:
llm-runtime:11434
db-seed
```

### 로컬 컴포넌트

| 컴포넌트 | 기술 | 역할 |
|---|---|---|
| `frontend` | Vite + React | 채팅 UI, 사용자 입력 수집, AI Server 호출 |
| `ai-server` | FastAPI | 공개 API, 대화 흐름 제어, BE 호출, LLM 연동 |
| `backend` | Spring Boot | 내부 API, 조건 저장, 지역 필터링 |
| `db` | MySQL 8.4 | 로컬 개발용 DB |
| `db-seed` | MySQL client container | `db/seed/seed-data.sql.gz`를 로컬 Docker DB로 import |
| `llm-runtime` | Ollama | 로컬 LLM 실행 옵션 |

### 로컬 요청 경로

```text
http://localhost:5173
  -> http://localhost:8000/chat
  -> http://backend:8080/internal/*
  -> mysql://db:3306/homefit
```

---

## 3. AWS 배포 목표 구조

AWS 배포는 Free Tier 사용을 최대한 고려한 단순 구조를 1차 목표로 둡니다.

```text
Internet
  |
  | HTTPS 443 / HTTP 80
  v
EC2 Application Server
  |
  | internal process/container network
  | - Frontend static serving or reverse proxy
  | - AI Server
  | - Backend
  |
  | MySQL 3306
  v
Amazon RDS MySQL

Logs:
EC2 / app logs -> Amazon CloudWatch Logs

Security:
IAM Role + Security Group
```

### AWS 구성 방침

| 영역 | 선택 |
|---|---|
| Backend/Application | AWS EC2 |
| Database | Amazon RDS MySQL |
| Monitoring | Amazon CloudWatch Logs |
| Security | IAM, Security Group |

MVP에서는 비용과 운영 복잡도를 줄이기 위해 EC2 한 대에 애플리케이션 계층을 두는 구성을 우선합니다.

EC2 내부에는 아래 프로세스 또는 컨테이너가 같이 배치될 수 있습니다.

- `ai-server`
- `backend`
- frontend 정적 파일 서빙 또는 reverse proxy

저비용 MVP 기준 추천값:

| 항목 | 추천값 |
|---|---|
| Region | `ap-northeast-2` 서울 |
| OS | Ubuntu 24.04 LTS 또는 Amazon Linux 2023 |
| EC2 instance type | `t3.micro` 또는 AWS Console에서 Free tier eligible로 표시되는 micro 타입 |
| EC2 storage | 20~30GB |
| Public IP | EC2에 1개만 사용 |
| Elastic IP | 초기에는 사용하지 않음. 단, 도메인 연결이나 고정 IP가 필요하면 사용 검토 |
| 실행 방식 | Docker Compose 우선, 필요 시 systemd |
| Java memory | `-Xms128m -Xmx384m~512m` 범위로 제한 |
| LLM 실행 | EC2에서 직접 실행하지 않고 외부 LLM API 호출 |

초기 배포에서 제외하는 항목:

- ALB
- NAT Gateway
- RDS Multi-AZ
- RDS Read Replica
- RDS Performance Insights
- RDS Enhanced Monitoring
- Container Insights
- CloudWatch RUM/Synthetics

장기적으로는 Frontend를 S3/CloudFront로 분리하거나, AI Server와 Backend를 별도 인스턴스 또는 ECS로 분리할 수 있습니다. 다만 MVP의 1차 배포 기준은 EC2 1대 + RDS MySQL 1대 + CloudWatch Logs 최소 사용입니다.

---

## 4. 컴포넌트별 역할

## 4.1 Frontend

Frontend의 책임은 사용자 인터페이스와 AI Server 호출입니다.

주요 역할:

- 채팅 화면 렌더링
- 사용자 입력 수집
- quick reply chip 클릭을 구조화된 `raw` 값으로 변환
- `POST /chat` 호출
- AI Server 응답의 `bot_messages` 렌더링

Frontend가 직접 호출하지 않는 대상:

- Backend 내부 API
- MySQL
- LLM provider

현재 구현 기준:

- API base URL은 `VITE_API_BASE_URL`로 설정합니다.
- `VITE_USE_MOCK_CHAT=false`일 때 실제 AI Server를 호출합니다.
- `VITE_USE_MOCK_CHAT` 기본 동작은 mock 사용입니다.

## 4.2 AI Server

AI Server는 FE가 호출하는 유일한 공개 API 서버입니다.

주요 역할:

- `POST /chat` 공개 API 제공
- `GET /healthz` 제공
- 입력값 검증
- 대화 단계 제어
- Backend 내부 API 호출
- LLM provider를 통한 자연어 조건 추출
- fallback 응답 생성

현재 구현 기준:

- FastAPI로 구현되어 있습니다.
- `BACKEND_URL`로 Backend 위치를 설정합니다.
- `AI_BACKEND_MODE=http`이면 실제 Backend를 호출합니다.
- `AI_PROVIDER`로 LLM provider를 선택합니다.
- validation error는 가능한 한 `200 + bot_messages` 형태로 흡수합니다.

중요한 현재 구현 특성:

- 대화 단계 상태 일부가 AI Server 메모리(`_session_state`)에 저장됩니다.
- 따라서 AI Server 재시작, 다중 인스턴스, 무중단 배포 상황에서는 대화 단계가 유실될 수 있습니다.
- API 명세의 목표는 세션 상태를 DB의 `chat_messages.conditions`로 복원하는 구조이므로, 운영 전에는 대화 단계도 DB 기반으로 옮기는 것이 안전합니다.

## 4.3 Backend

Backend는 내부 API와 DB 접근을 담당합니다.

주요 역할:

- `POST /internal/upsert-conditions`
- `POST /internal/filter`
- `GET /healthz`
- `GET /actuator/health`
- 세션별 조건 저장
- 누적 conditions 복원
- 거래 데이터 기반 추천 지역 필터링

현재 구현 기준:

- Spring Boot로 구현되어 있습니다.
- JPA와 Flyway를 사용합니다.
- `chat_messages`에 매 턴의 `raw`와 누적 `conditions`를 저장합니다.
- `housing_transactions`와 `regions`를 조회해 상위 3개 지역명을 반환합니다.

## 4.4 MySQL / RDS

DB는 사용자 조건 이력과 거래 원천 데이터를 저장합니다.

핵심 테이블:

| 테이블 | 역할 |
|---|---|
| `regions` | 지역 기준 정보 |
| `housing_transactions` | 전세, 월세, 매매 거래 데이터 |
| `chat_messages` | 세션별 사용자 입력과 누적 조건 |

운영 배포에서는 Docker MySQL이 아니라 Amazon RDS MySQL을 사용합니다.

스키마 생성:

- Backend 시작 시 Flyway migration으로 schema를 생성/변경합니다.

데이터 적재:

- 로컬 개발에서는 `db-seed`가 `db/seed/seed-data.sql.gz`를 Docker MySQL에 import합니다.
- 운영 RDS에서는 `db-seed` 자동 실행보다, 명시적인 초기 데이터 import 절차를 분리하는 것이 안전합니다.

## 4.5 LLM Provider

AI Server는 LLM provider를 추상화해서 사용합니다.

현재 설정 옵션:

| 설정 | 의미 |
|---|---|
| `AI_PROVIDER=openai_compatible` | OpenAI 호환 `/v1/chat/completions` API 사용 |
| `AI_PROVIDER=ollama_native` | Ollama native API 사용 |
| `AI_PROVIDER=dummy` | LLM 미사용 |
| `OPENAI_BASE_URL` | OpenAI 호환 API base URL |
| `OPENAI_API_KEY` | 외부 LLM API key |
| `OPENAI_MODEL` | 사용할 모델명 |

현재 Docker Compose 기본값은 OpenRouter의 OpenAI 호환 API를 바라보도록 설정되어 있습니다.

---

## 5. 주요 요청 흐름

## 5.1 첫 진입

```text
1. 사용자가 Frontend 접속
2. Frontend가 AI Server에 POST /chat 호출
   - session_id: null
   - raw: {}
3. AI Server가 Backend에 POST /internal/upsert-conditions 호출
4. Backend가 새 session_id 생성
5. Backend가 chat_messages에 raw + conditions 저장
6. AI Server가 자본금 질문 bot_messages 반환
7. Frontend가 bot_messages 렌더링
```

응답 상태:

```text
state = "asking"
```

## 5.2 자본금 입력

```text
1. 사용자가 자본금 선택 또는 입력
2. Frontend가 raw.budget_max를 원 단위 숫자로 변환
3. Frontend가 POST /chat 호출
4. AI Server가 Backend에 조건 저장 요청
5. Backend가 기존 session_id의 최신 conditions를 읽고 budget_max를 병합
6. AI Server가 거래 유형 질문 반환
```

예시:

```json
{
  "session_id": "uuid",
  "raw": {
    "budget_max": 200000000
  }
}
```

## 5.3 거래 유형 입력

```text
1. 사용자가 전세, 월세, 매매 중 하나 선택
2. Frontend가 raw.deal_type 전송
3. AI Server가 Backend에 조건 저장 요청
4. Backend가 conditions에 deal_type 병합
5. 필요한 조건이 모두 있으면 AI Server가 Backend 필터 API 호출
```

API 명세 기준 허용값:

| 값 | 의미 |
|---|---|
| `jeonse` | 전세 |
| `monthly_rent` | 월세 |
| `sale` | 매매 |

## 5.4 월세 예산 입력

API 명세 기준으로 `deal_type="monthly_rent"`인 경우 월세 예산을 추가로 입력받습니다.

```text
1. 사용자가 월세 상한 입력
2. Frontend가 raw.monthly_rent_max를 원 단위 숫자로 변환
3. AI Server가 conditions에 monthly_rent_max 병합
4. Backend가 DB 조회 시 monthly_rent_max / 10000으로 만원 단위 변환
5. monthly_rent <= monthly_rent_max_in_manwon 조건으로 필터링
```

예시:

```json
{
  "session_id": "uuid",
  "raw": {
    "monthly_rent_max": 800000
  }
}
```

현재 구현 기준으로는 이 흐름이 아직 완전히 반영되어 있지 않습니다. 자세한 내용은 [10. API 명세와 현재 구현 차이](#10-api-명세와-현재-구현-차이)를 참고합니다.

## 5.5 추천 결과 생성

```text
1. AI Server가 Backend에 POST /internal/filter 호출
2. Backend가 conditions 검증
3. Backend가 원 단위 예산을 만원 단위로 변환
4. Backend가 housing_transactions 조회
5. Backend가 지역 단위로 group by
6. Backend가 상위 3개 지역명 반환
7. AI Server가 사용자에게 보여줄 bot_messages 생성
8. Frontend가 추천 결과 렌더링
```

응답 상태:

```text
state = "result"
```

결과는 DB에 저장하지 않습니다.

## 5.6 오류 및 fallback 흐름

AI Server는 FE가 별도 실패 분기를 많이 갖지 않도록 fallback 응답을 우선합니다.

```text
Backend 호출 실패
  -> AI Server가 fallback bot_messages 생성
  -> Frontend는 bot_messages 그대로 렌더링
```

권장 방향:

- 사용자 입력 오류는 재질문으로 복구합니다.
- Backend/LLM 장애는 fallback 메시지로 복구합니다.
- 운영에서는 원인 추적을 위해 AI Server와 Backend 로그를 CloudWatch Logs로 전송합니다.

---

## 6. 데이터 흐름

## 6.1 저장되는 데이터

`chat_messages`에는 매 턴마다 아래 데이터가 저장됩니다.

| 컬럼 | 내용 |
|---|---|
| `id` | 메시지 row 식별자 |
| `session_id` | 대화 세션 식별자 |
| `raw` | 이번 턴에 들어온 입력 |
| `conditions` | 누적 병합된 조건 |
| `created_at` | 생성 시각 |

예시:

```json
{
  "raw": {
    "deal_type": "monthly_rent"
  },
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  }
}
```

## 6.2 저장하지 않는 데이터

아래 데이터는 MVP 기준으로 저장하지 않습니다.

- 추천 결과 지역 목록
- AI가 생성한 설명 문장
- bot message 전문
- 최종 추천 결과 snapshot

이 결정의 의미:

- 추천 결과는 매 요청 시 현재 거래 데이터 기준으로 다시 계산됩니다.
- 사용자 대화의 조건 이력은 남지만, 결과 이력은 남지 않습니다.
- 추후 추천 이력 기능이 필요하면 별도 `recommendation_results` 테이블을 추가해야 합니다.

## 6.3 거래 데이터 단위

API 입력값:

- `budget_max`: 원 단위
- `monthly_rent_max`: 원 단위

DB 저장값:

- `deposit_amount`: 만원 단위
- `sale_price_amount`: 만원 단위
- `monthly_rent`: 만원 단위

Backend 변환:

```text
budget_max_in_manwon = budget_max / 10000
monthly_rent_max_in_manwon = monthly_rent_max / 10000
```

## 6.4 매매 데이터 기준

현재 DB migration과 Backend entity에는 매매가 전용 컬럼인 `sale_price_amount`가 있습니다.

현재 Backend 조회 기준:

- `deal_type = 'sale'`이면 `sale_price_amount <= budget_max_in_manwon`
- `deal_type != 'sale'`이면 `deposit_amount <= budget_max_in_manwon`

주의:

- [API.md](../api/API.md)는 매매 데이터를 `deposit_amount`에 저장한다고 설명하는 부분이 있습니다.
- 현재 구현은 `sale_price_amount`를 사용합니다.
- 운영 전 API 문서와 DB 설계 중 하나로 기준을 통일해야 합니다.

---

## 7. 인증/보안 구조

## 7.1 현재 구현

현재 Spring Security 설정은 아래 경로를 허용합니다.

- `/internal/**`
- `/healthz`
- `/actuator/health`

즉, 애플리케이션 레벨에서는 내부 API가 토큰 없이 접근 가능합니다.

현재 보안 전제:

- Backend는 외부 인터넷에 직접 노출하지 않습니다.
- FE는 Backend를 직접 호출하지 않습니다.
- AI Server와 Backend는 내부 네트워크에서 통신합니다.

## 7.2 운영 배포 권장 구조

운영 배포에서는 네트워크와 애플리케이션 레벨을 함께 제한합니다.

### Security Group

권장 Security Group 규칙:

| 대상 | Inbound |
|---|---|
| EC2 | `80`, `443` from Internet |
| EC2 SSH | 가능하면 닫고 SSM 사용. SSH가 필요하면 관리자 IP만 허용 |
| RDS MySQL | `3306` from EC2 Security Group only |

RDS는 public access를 끄고, EC2에서만 접근하도록 제한합니다.

### Internal API 보호

현재 구조에서는 `/internal/**`가 `permitAll`입니다.

운영 전 권장 보강:

- Backend를 public subnet에 직접 노출하지 않기
- reverse proxy에서 Backend 포트를 외부에 열지 않기
- AI Server -> Backend 호출에 `X-Internal-Token` 추가
- Backend에서 내부 토큰 검증 filter 추가

### IAM

EC2에는 IAM Role을 연결합니다.

권장 역할:

- CloudWatch Logs로 로그를 전송할 권한
- 필요 시 SSM Parameter Store 또는 Secrets Manager에서 설정값을 읽을 권한

원칙:

- AWS access key를 EC2 파일이나 Git에 저장하지 않습니다.
- EC2 Instance Profile을 통해 임시 자격 증명을 사용합니다.
- 권한은 필요한 작업에만 최소화합니다.

### Secret 관리

민감 정보:

- `SPRING_DATASOURCE_PASSWORD`
- `OPENAI_API_KEY`
- 내부 API token

권장 저장 위치:

- AWS Systems Manager Parameter Store
- AWS Secrets Manager
- 최소한 EC2의 제한된 권한 파일 또는 배포 환경 변수

Git에 커밋하지 않습니다.

---

## 8. 인프라/배포 구조

## 8.1 EC2 Application Server

EC2는 애플리케이션 실행 계층입니다.

MVP 배포 방식:

```text
EC2
  - nginx 또는 reverse proxy
  - frontend static files
  - ai-server container
  - backend container
  - CloudWatch agent
```

MVP 추천 실행 방식:

- Docker Compose
- 필요 시 Docker Compose를 systemd service로 등록
- 배포 스크립트는 build/pull/restart 정도로 단순화

MVP에서는 현재 로컬 Docker Compose 구조를 운영용 compose 또는 systemd로 정리해 EC2에서 실행하는 방식이 가장 단순합니다.

운영 EC2에서는 Vite dev server를 실행하지 않습니다.

- Frontend는 `npm run build` 결과물을 nginx로 정적 서빙합니다.
- AI Server는 FastAPI/Uvicorn 컨테이너로 실행합니다.
- Backend는 Spring Boot jar 컨테이너로 실행합니다.
- Backend와 AI Server는 같은 EC2 내부 Docker network에서 통신합니다.

EC2 메모리 제한:

- `t3.micro`급은 메모리 여유가 작습니다.
- Backend JVM은 `JAVA_TOOL_OPTIONS=-Xms128m -Xmx384m` 또는 `-Xms128m -Xmx512m` 수준으로 제한합니다.
- swap 1~2GB 설정을 권장합니다.
- 운영 EC2에서는 Ollama 같은 로컬 LLM runtime을 실행하지 않습니다.

운영에서 분리할 수 있는 항목:

- Frontend: S3 + CloudFront
- AI Server: 별도 EC2 또는 ECS
- Backend: 별도 EC2 또는 ECS
- reverse proxy/TLS: ALB 또는 Nginx + ACM/Let's Encrypt

MVP 비용 절감 관점에서는 위 분리 항목을 초기부터 적용하지 않습니다.

## 8.2 Amazon RDS MySQL

RDS는 운영 DB입니다.

저비용 MVP 권장 설정:

| 항목 | 추천값 |
|---|---|
| Engine | MySQL 8.x |
| Template | Free tier 또는 Dev/Test |
| DB instance | `db.t3.micro` 또는 `db.t4g.micro` |
| Deployment | Single-AZ |
| Storage | 20GB |
| Storage autoscaling | Off |
| Public access | No |
| Backup retention | 1일 또는 최소값 |
| Multi-AZ | Off |
| Read replica | Off |
| Performance Insights | Off |
| Enhanced Monitoring | Off |
| Deletion protection | 포트폴리오 초기에는 Off |

보안 설정:

- RDS public access는 끕니다.
- RDS inbound `3306`은 EC2 Security Group에서만 허용합니다.
- charset/timezone은 애플리케이션 설정과 일치시킵니다.

운영 데이터가 실제로 쌓이기 시작하면 백업 보존 기간과 deletion protection을 다시 검토합니다.

Backend 연결 예시:

```text
SPRING_DATASOURCE_URL=jdbc:mysql://<rds-endpoint>:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8
SPRING_DATASOURCE_USERNAME=<db-user>
SPRING_DATASOURCE_PASSWORD=<db-password>
```

Schema migration:

- Backend 시작 시 Flyway가 RDS에 migration을 적용합니다.
- RDS에 직접 수동 schema 변경을 반복하지 않습니다.

Seed/import:

- 운영 초기 import는 별도 절차로 실행합니다.
- `db-seed` 컨테이너의 자동 import는 로컬 개발 편의 기능으로 봅니다.
- 운영 RDS에 강제 import를 할 때는 기존 데이터 truncate 여부를 명확히 확인해야 합니다.

## 8.3 CloudWatch Logs

CloudWatch Logs는 애플리케이션 로그 중앙화 용도로 사용합니다.

MVP 수집 대상:

- reverse proxy access/error logs
- AI Server logs
- Backend logs
- Docker 또는 systemd service logs

MVP 권장 설정:

- 로그 그룹을 서비스별로 분리
- retention 기간은 7일 또는 최소 운영 확인에 필요한 기간으로 설정
- 기본 로그 레벨은 `INFO`로 제한
- error/fallback 빈도만 우선 확인
- 배포 직후 `/healthz`, `/actuator/health` 호출 실패 로그 확인

초기에는 아래 기능을 사용하지 않습니다.

- CloudWatch RUM
- CloudWatch Synthetics
- Container Insights
- 과도한 custom metrics
- 장기 log retention

## 8.4 Free Tier 고려사항

AWS Free Tier 조건과 제공 범위는 변경될 수 있습니다.

운영 전 확인할 항목:

- EC2 인스턴스 타입과 월 사용 시간
- RDS 인스턴스 클래스와 스토리지
- CloudWatch Logs ingest/storage 비용
- 데이터 전송 비용
- 외부 LLM provider 비용
- public IPv4 비용
- Free Tier 적용 기간과 계정 생성일 기준

MVP에서는 항상 아래 원칙을 둡니다.

- 작은 인스턴스에서 시작합니다.
- 불필요한 상시 실행 리소스를 줄입니다.
- CloudWatch log retention을 무기한으로 두지 않습니다.
- RDS snapshot, backup, storage 증가 비용을 확인합니다.
- EC2 public IPv4는 1개만 사용합니다.
- Elastic IP는 고정 IP가 꼭 필요할 때만 사용합니다.
- AWS Budgets 또는 Billing alert를 설정합니다.

주의:

- Elastic IP를 쓰지 않아도, 실행 중인 EC2의 일반 public IPv4 자체가 과금 대상일 수 있습니다.
- 따라서 비용 절감의 핵심은 Elastic IP 사용 여부보다 public IPv4 개수를 최소화하는 것입니다.
- Free Tier eligible 표시는 계정 생성일, 리전, 인스턴스 타입에 따라 달라질 수 있으므로 콘솔에서 최종 확인합니다.

---

## 9. 외부 연동

## 9.1 LLM API

AI Server는 OpenAI 호환 API 또는 Ollama를 사용할 수 있습니다.

OpenAI 호환 API 사용 시:

```text
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=<secret>
OPENAI_MODEL=<model>
```

로컬 Ollama 사용 시:

```text
AI_PROVIDER=ollama_native
OPENAI_BASE_URL=http://llm-runtime:11434/v1
OPENAI_MODEL=<local-model>
```

배포 환경 권장:

- EC2 micro 인스턴스에서는 LLM을 직접 실행하지 않습니다.
- 운영 배포는 외부 LLM API 호출 구조를 기본값으로 둡니다.
- `llm-runtime`/Ollama는 로컬 개발 또는 별도 실험 환경에서만 사용합니다.

주의:

- 외부 LLM API 장애 시 AI Server가 fallback을 반환해야 합니다.
- API key는 Git에 저장하지 않습니다.
- 운영 로그에 API key나 사용자 민감 입력이 남지 않도록 주의합니다.

## 9.2 AWS Services

사용 예정 AWS 서비스:

| 서비스 | 역할 |
|---|---|
| EC2 | 애플리케이션 실행 |
| RDS MySQL | 운영 DB |
| CloudWatch Logs | 로그 수집/검색 |
| IAM | EC2 권한 관리 |
| Security Group | 네트워크 접근 제어 |

---

## 10. API 명세와 현재 구현 차이

아래 항목은 운영 전 반드시 정리해야 하는 정합성 체크리스트입니다.

| 항목 | API 명세 기준 | 현재 구현 상태 | 판단 |
|---|---|---|---|
| `deal_type=sale` | 허용 | Backend validator/query는 지원, AI Server schema와 FE chip은 미지원 | AI/FE 구현 보완 필요 |
| `monthly_rent_max` | 월세 조건에서 필수 | AI Server schema 미지원, Backend filter 미반영 | 전체 흐름 구현 필요 |
| 서울 내부 추천 제한 | 서울 내부 지역만 반환 | Backend query에 `sido='서울...'` 조건 없음 | DB 데이터 또는 query 기준 명확화 필요 |
| 매매 가격 컬럼 | API 문서 일부는 `deposit_amount` 기준 설명 | 현재 DB/Backend는 `sale_price_amount` 사용 | API 문서 또는 DB 기준 통일 필요 |
| AI Server stateless | DB conditions로 세션 상태 관리 | 대화 step은 AI Server 메모리에 저장 | 운영 전 DB 기반 복원 필요 |
| 내부 API 보안 | 운영에서 `X-Internal-Token` 권장 | `/internal/**` permitAll | 운영 보안 보강 필요 |
| 월세 질문 흐름 | 거래 유형이 월세면 월세 예산 질문 | 현재 대화 단계는 자본금 -> 거래 유형 -> 결과 중심 | dialog policy 보완 필요 |

---

## 11. 주요 설정 결정

## 11.1 API 경계

결정:

- FE는 AI Server만 호출합니다.
- Backend는 내부 API만 제공합니다.

이유:

- FE가 비즈니스 필터링 API를 직접 알 필요가 없습니다.
- 대화 fallback과 LLM 연동 실패를 AI Server에서 흡수할 수 있습니다.
- Backend는 데이터 저장과 조회에 집중할 수 있습니다.

## 11.2 세션 저장 방식

결정:

- `chat_messages`에 매 턴의 `raw`와 누적 `conditions`를 저장합니다.
- 별도 `chat_conditions` 테이블은 두지 않습니다.

이유:

- MVP의 조건 수가 적습니다.
- JSON 기반으로 빠르게 확장할 수 있습니다.
- 세션별 최신 conditions 복원이 단순합니다.

주의:

- 조건이 복잡해지면 JSON 내부 검색/통계가 어려워질 수 있습니다.
- 추천 이력이나 분석 기능이 필요하면 별도 정규화 테이블을 검토합니다.

## 11.3 추천 결과 비저장

결정:

- 추천 결과와 AI 설명 텍스트는 저장하지 않습니다.

이유:

- MVP에서는 추천 결과 이력 기능이 없습니다.
- 거래 데이터가 바뀌면 매 요청마다 최신 기준으로 다시 계산하는 편이 단순합니다.

주의:

- 사용자에게 이전 추천 결과를 다시 보여주는 기능이 필요하면 결과 snapshot 저장이 필요합니다.

## 11.4 단위 변환

결정:

- API는 원 단위를 사용합니다.
- DB 거래 금액은 만원 단위를 사용합니다.
- Backend가 조회 직전에 원 -> 만원 변환을 수행합니다.

이유:

- FE와 AI Server는 사용자 입력에 가까운 원 단위를 유지합니다.
- DB는 공공데이터/시드 데이터 단위에 맞춥니다.

## 11.5 AWS MVP 배포

결정:

- 1차 배포는 EC2 1대 + RDS MySQL 1대 + CloudWatch Logs 최소 사용으로 구성합니다.
- Backend와 AI Server는 같은 EC2 안에서 Docker Compose로 같이 실행합니다.
- LLM은 EC2에서 직접 실행하지 않고 외부 LLM API를 호출합니다.

이유:

- 현재 Docker Compose 구조를 가장 적은 변경으로 배포할 수 있습니다.
- AI Server를 별도 EC2로 분리하면 비용과 운영 복잡도가 증가합니다.
- EC2 micro 인스턴스에서 로컬 LLM 실행은 메모리와 CPU 측면에서 현실적이지 않습니다.
- RDS를 사용하면 DB 백업, 패치, 장애 복구 부담을 줄일 수 있습니다.
- CloudWatch Logs로 서버 로그를 한 곳에서 확인할 수 있습니다.

초기 제외:

- ALB
- NAT Gateway
- Multi-AZ
- Read Replica
- Elastic IP
- Performance Insights
- Enhanced Monitoring

Elastic IP는 초기에는 제외하되, 도메인 연결 후 EC2 재시작 시 IP 변경이 문제가 되면 별도로 검토합니다.

---

## 12. 배포 후 확인 항목

배포 직후 아래 항목을 확인합니다.

```text
1. EC2 security group이 80/443만 외부에 열려 있는가
2. RDS public access가 꺼져 있는가
3. RDS inbound 3306이 EC2 security group에서만 허용되는가
4. Backend가 RDS에 연결되는가
5. Flyway migration이 성공했는가
6. /healthz, /actuator/health가 정상인가
7. Frontend -> AI Server -> Backend -> RDS 요청이 끝까지 성공하는가
8. CloudWatch Logs에 AI Server와 Backend 로그가 들어오는가
9. OPENAI_API_KEY, DB password가 Git 또는 이미지에 포함되지 않았는가
10. fallback 발생 시 원인을 로그에서 추적할 수 있는가
11. EC2 public IPv4가 1개만 사용되는가
12. RDS Multi-AZ, Read Replica, Enhanced Monitoring, Performance Insights가 꺼져 있는가
13. CloudWatch Logs retention이 설정되어 있는가
14. AWS Budgets 또는 Billing alert가 설정되어 있는가
15. Backend JVM 메모리 제한과 swap 설정이 적용되어 있는가
```

---

## 13. 참고 문서

프로젝트 문서:

- [API.md](../api/API.md)
- [ERD.md](../../db/ERD.md)
- [DB seed README](../../db/README.md)

AWS 공식 문서:

- [AWS Free Tier](https://aws.amazon.com/free/)
- [IAM roles for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [Security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- [Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)
- [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [Amazon EC2 instance IP addressing](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-instance-addressing.html)
