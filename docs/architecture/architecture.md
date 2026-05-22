# homefit 아키텍처

- 문서 버전: `v0.1.0`
- 작성일: `2026-05-22`
- 문서 상태: `Draft`
- 적용 범위: `MVP v0`
- 기준 문서:
  - [API.md](../api/API.md)
  - [ERD.md](../data/ERD.md)
  - [convention.md](../convention/convention.md)

---

## 0. 문서 목적

본 문서는 homefit의 전체 요청 흐름과 서버 구성을 설명합니다.

다루는 내용:

- 전체 시스템 구조
- 컴포넌트별 역할
- 주요 요청 흐름
- 데이터 흐름
- 인증/보안 구조
- 인프라/배포 구조
- 외부 연동
- 주요 설정 결정
- 현재 구현상 주의사항

---

## 1. 전체 시스템 구조

homefit MVP의 논리 구조는 아래와 같습니다.

```text
Frontend -> AI Server -> Backend -> MySQL
```

역할 분리:

| 컴포넌트 | 역할 |
|---|---|
| Frontend | 채팅 UI, 사용자 입력 수집, `bot_messages` 렌더링 |
| AI Server | 공개 API, 대화 흐름 제어, Backend 호출, LLM 연동, fallback 처리 |
| Backend | 내부 API, 조건 저장, 거래 데이터 필터링, DB migration |
| MySQL | 지역/거래 데이터와 세션 조건 저장 |

핵심 원칙:

- Frontend는 AI Server만 호출합니다.
- Backend는 내부 API만 제공합니다.
- 추천 대상 지역은 서울 내부로 한정합니다.
- 추천 결과와 AI 설명 텍스트는 DB에 저장하지 않습니다.
- 세션 상태는 `chat_messages.session_id`와 `conditions` JSON으로 관리합니다.

---

## 2. 로컬 개발 구성

현재 로컬 개발 환경은 Docker Compose 중심입니다.

```text
localhost:5173
  |
  v
frontend
  |
  | POST /chat
  v
ai-server:8000
  |
  | POST /internal/upsert-conditions
  | POST /internal/filter
  v
backend:8080
  |
  v
db:3306(container) / 3307(host)
```

보조 컴포넌트:

| 컴포넌트 | 역할 |
|---|---|
| `db-seed` | `db/seed/seed-data.sql.gz`를 Docker MySQL에 import |
| `llm-runtime` | 로컬 Ollama 실험용 LLM runtime |

로컬에서 전체 앱을 실행할 때는 아래 명령을 사용합니다.

```sh
docker compose up frontend ai-server
```

또는:

```sh
make docker-up-detached
```

---

## 3. 컴포넌트별 역할

## 3.1 Frontend

Frontend는 사용자와 직접 만나는 채팅 UI입니다.

주요 책임:

- 사용자 입력 수집
- quick reply chip 렌더링
- chip click을 구조화된 `raw`로 변환
- AI Server의 `POST /chat` 호출
- `bot_messages` 렌더링

환경변수:

| 변수 | 설명 |
|---|---|
| `VITE_API_BASE_URL` | AI Server base URL |
| `VITE_USE_MOCK_CHAT` | mock 사용 여부 |

Frontend는 Backend를 직접 호출하지 않습니다.

## 3.2 AI Server

AI Server는 Frontend의 유일한 API 진입점입니다.

주요 API:

- `POST /chat`
- `GET /healthz`

주요 책임:

- request validation
- 세션 기반 대화 흐름 제어
- conditions 구성
- Backend 내부 API 호출
- LLM provider 호출
- fallback 응답 생성

Backend 호출:

- `POST /internal/upsert-conditions`
- `POST /internal/filter`

LLM provider:

- `openai_compatible`
- `ollama_native`
- `dummy`

운영에서는 `ollama_native`를 기본으로 사용하지 않습니다. EC2 micro 인스턴스에서는 로컬 LLM 실행이 현실적이지 않으므로 외부 OpenAI-compatible API 호출을 기본 구조로 둡니다.

## 3.3 Backend

Backend는 내부 API와 DB 접근을 담당합니다.

기술 스택:

- Java 21
- Spring Boot 3.5.14
- Gradle
- Spring Web
- Spring Data JPA
- Spring Security
- Spring Validation
- Spring Boot Actuator
- Flyway
- MySQL Driver
- Lombok

주요 API:

- `POST /internal/upsert-conditions`
- `POST /internal/filter`
- `GET /healthz`
- `GET /actuator/health`

주요 책임:

- `session_id` 생성 및 검증
- 최신 conditions 조회
- raw + conditions 저장
- 조건 검증
- 거래 데이터 조회
- 상위 지역명 반환

## 3.4 MySQL

MySQL은 세션 조건과 거래 원천 데이터를 저장합니다.

핵심 테이블:

| 테이블 | 역할 |
|---|---|
| `regions` | 지역 기준 정보 |
| `housing_transactions` | 전세/월세/매매 거래 데이터 |
| `chat_messages` | 사용자 입력과 누적 조건 |

Schema 변경은 Flyway migration으로 관리합니다.

---

## 4. 주요 요청 흐름

## 4.1 첫 진입

```text
1. Frontend가 POST /chat 호출
   - session_id: null
   - raw: {}
2. AI Server가 Backend에 /internal/upsert-conditions 호출
3. Backend가 session_id 생성
4. Backend가 chat_messages에 raw + conditions 저장
5. AI Server가 첫 질문 반환
6. Frontend가 bot_messages 렌더링
```

## 4.2 조건 입력

```text
1. 사용자가 자본금 또는 거래 유형 입력
2. Frontend가 입력을 raw로 변환
3. AI Server가 Backend에 conditions 저장 요청
4. Backend가 기존 session의 최신 conditions를 읽고 병합
5. AI Server가 다음 질문 또는 결과 요청을 결정
```

조건 키:

| 키 | 설명 |
|---|---|
| `budget_max` | 원 단위 최대 예산 |
| `deal_type` | `jeonse`, `monthly_rent`, `sale` |
| `monthly_rent_max` | 월세 상한. 월세 조건에서만 사용 |

## 4.3 지역 추천

```text
1. AI Server가 POST /internal/filter 호출
2. Backend가 conditions 검증
3. Backend가 원 단위 예산을 만원 단위로 변환
4. Backend가 housing_transactions 조회
5. Backend가 지역별로 group by
6. Backend가 상위 3개 지역명 반환
7. AI Server가 bot_messages 생성
8. Frontend가 추천 결과 렌더링
```

결과는 DB에 저장하지 않습니다.

## 4.4 Fallback

Backend 또는 LLM 호출에 실패하면 AI Server가 fallback 메시지를 반환합니다.

Frontend는 오류 분기를 직접 해석하지 않고 `bot_messages`를 그대로 렌더링합니다.

---

## 5. 데이터 흐름

## 5.1 저장 데이터

`chat_messages`에는 매 턴 아래 데이터가 저장됩니다.

| 컬럼 | 설명 |
|---|---|
| `id` | 메시지 row ID |
| `session_id` | 대화 세션 ID |
| `raw` | 이번 턴 입력 |
| `conditions` | 누적 조건 |
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

## 5.2 비저장 데이터

아래 데이터는 MVP 기준으로 저장하지 않습니다.

- 추천 결과 지역 목록
- AI 설명 텍스트
- bot message 전문
- 최종 추천 결과 snapshot

## 5.3 금액 단위

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

---

## 6. 인증/보안 구조

현재 Backend 보안 설정은 MVP 내부 API 구조를 기준으로 합니다.

허용 경로:

- `/internal/**`
- `/healthz`
- `/actuator/health`

그 외 요청은 인증이 필요합니다.

운영 보안 원칙:

- Backend port를 외부에 직접 노출하지 않습니다.
- RDS는 public access를 끕니다.
- RDS `3306` inbound는 EC2 Security Group에서만 허용합니다.
- 실제 secret은 `.env`, AWS Parameter Store, Secrets Manager 등에서 관리합니다.
- `.env`는 Git에 커밋하지 않습니다.

운영 전 보강 후보:

- AI Server -> Backend `X-Internal-Token`
- Backend 내부 token 검증 filter
- HTTPS 적용
- SSH 대신 SSM 사용

---

## 7. 인프라/배포 구조

## 7.1 목표 구성

초기 배포는 AWS Free Tier와 비용 절감을 우선합니다.

```text
Internet
  |
  v
EC2 1대
  - nginx 또는 reverse proxy
  - frontend static files
  - ai-server
  - backend
  - CloudWatch agent
  |
  v
RDS MySQL 1대
```

로그:

```text
EC2 / app logs -> CloudWatch Logs
```

## 7.2 EC2 추천값

| 항목 | 추천값 |
|---|---|
| Region | `ap-northeast-2` 서울 |
| OS | Ubuntu 24.04 LTS 또는 Amazon Linux 2023 |
| Instance type | `t3.micro` 또는 Free tier eligible micro |
| Storage | 20~30GB |
| Public IP | 1개만 사용 |
| Elastic IP | 초기에는 사용하지 않음 |
| 실행 방식 | Docker Compose |
| Java memory | `-Xms128m -Xmx384m~512m` |

운영 EC2에서는 Vite dev server를 실행하지 않습니다.

- Frontend는 build 결과물을 nginx로 정적 서빙합니다.
- AI Server와 Backend는 같은 Docker Compose 안에서 실행합니다.
- Ollama 같은 로컬 LLM runtime은 실행하지 않습니다.
- LLM은 외부 API를 호출합니다.

## 7.3 RDS MySQL 추천값

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

운영 데이터가 실제로 쌓이면 backup retention과 deletion protection을 다시 검토합니다.

## 7.4 CloudWatch Logs

초기에는 최소 로그만 수집합니다.

수집 대상:

- reverse proxy access/error logs
- AI Server logs
- Backend logs
- Docker 또는 systemd logs

권장:

- retention 7일 또는 최소 기간 설정
- 기본 log level은 `INFO`
- 장기 retention, Container Insights, custom metrics는 초기 제외

## 7.5 초기 제외 항목

비용 절감을 위해 초기에는 아래 항목을 사용하지 않습니다.

- ALB
- NAT Gateway
- Multi-AZ
- Read Replica
- Performance Insights
- Enhanced Monitoring
- Container Insights
- CloudWatch RUM/Synthetics

주의:

- Elastic IP를 사용하지 않아도 public IPv4 자체가 과금 대상일 수 있습니다.
- 비용 절감 핵심은 public IPv4 개수를 1개로 제한하는 것입니다.
- AWS Free Tier 적용 여부는 계정 생성일과 콘솔 표시를 기준으로 최종 확인합니다.

---

## 8. 외부 연동

## 8.1 OpenAI-compatible LLM API

운영 LLM 연동은 외부 OpenAI-compatible API 호출을 기본으로 합니다.

주요 환경변수:

| 변수 | 설명 |
|---|---|
| `AI_PROVIDER` | `openai_compatible` |
| `OPENAI_BASE_URL` | LLM API base URL |
| `OPENAI_API_KEY` | API key |
| `OPENAI_MODEL` | model name |

## 8.2 Local Ollama

Ollama는 로컬 개발 또는 실험용입니다.

운영 EC2 micro 인스턴스에서는 사용하지 않습니다.

---

## 9. 현재 구현 주의사항

아래 항목은 API 명세와 실제 구현이 계속 맞는지 확인해야 합니다.

| 항목 | 현재 주의사항 |
|---|---|
| `deal_type=sale` | Backend validator/query는 지원. AI Server schema와 FE chip 지원 상태 확인 필요 |
| `monthly_rent_max` | API 명세에는 있으나 전체 구현 반영 상태 확인 필요 |
| 서울 내부 추천 제한 | DB 데이터 또는 Backend query 중 어디서 보장할지 명확히 해야 함 |
| 매매 가격 컬럼 | 현재 Backend는 `sale_price_amount` 기준 조회 |
| AI Server 세션 상태 | 일부 대화 step이 메모리에 남을 수 있음 |
| 내부 API 보안 | 운영에서는 네트워크 제한 또는 내부 token 필요 |

---

## 10. 배포 후 확인 체크리스트

```text
1. EC2 security group이 80/443만 외부에 열려 있는가
2. Backend port 8080이 외부에 직접 열려 있지 않은가
3. RDS public access가 꺼져 있는가
4. RDS inbound 3306이 EC2 security group에서만 허용되는가
5. Backend가 RDS에 연결되는가
6. Flyway migration이 성공했는가
7. /healthz, /actuator/health가 정상인가
8. Frontend -> AI Server -> Backend -> RDS 흐름이 성공하는가
9. CloudWatch Logs에 app log가 들어오는가
10. OPENAI_API_KEY, DB password가 Git에 포함되지 않았는가
11. RDS Multi-AZ, Read Replica, Enhanced Monitoring, Performance Insights가 꺼져 있는가
12. CloudWatch Logs retention이 설정되어 있는가
13. Billing alert가 설정되어 있는가
14. Backend JVM memory limit과 swap 설정이 적용되어 있는가
```
