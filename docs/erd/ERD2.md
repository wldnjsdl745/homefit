# homefit ERD 문서 v2

- 문서 버전: `v0.2.0`
- 작성일: `2026-04-25`
- 문서 상태: `Draft`
- 적용 범위: `MVP v0`
- 기준 문서:
  - [plan.md](../../plan.md)
  - [backend-mvp.md](../../backend-mvp.md)
  - [ai-backend.md](../../ai-backend.md)
  - [ai-frontend.md](../../ai-frontend.md)

---

## 0. 문서 목적

기존 [ERD.md](./ERD.md)는 `chat_conditions` 분리 모델과 봇 메시지 저장 전제를 포함하고 있어, 현재 합의된 MVP 설계와 맞지 않는 부분이 있습니다.

본 문서는 아래 합의 사항을 반영한 **수정 ERD 초안**입니다.

- FE의 진입점은 AI 서버
- AI 서버는 stateless 오케스트레이터
- BE는 내부 API와 DB 저장/필터링만 담당
- DB에는 **추천 결과와 AI 설명 텍스트를 저장하지 않음**
- DB에는 **conditions만 영속화**
- `chat_messages` 단일 테이블에 `raw` + `conditions` JSON을 저장

---

## 1. MVP 데이터 모델 요약

MVP v0의 DB는 아래 3개 핵심 테이블로 구성합니다.

| 테이블명 | 역할 |
|---|---|
| `regions` | 추천 대상 지역 기준 정보 |
| `housing_transactions` | 지역별 전월세 실거래 데이터 |
| `chat_messages` | 세션 단위 사용자 입력과 누적 조건 저장 |

핵심 원칙:

- `chat_conditions` 테이블은 두지 않습니다.
- `recommendation_results` 테이블은 두지 않습니다.
- 봇 응답 메시지, AI 설명 문장, 추천 결과 리스트는 저장하지 않습니다.
- 세션 상태는 `chat_messages.session_id` 기준으로 추적합니다.

---

## 2. 시스템 관점에서 본 데이터 흐름

```text
FE -> AI 서버 -> Backend -> MySQL
```

DB 저장 흐름은 아래와 같습니다.

```text
1. FE가 AI 서버에 raw 입력 전송
2. AI 서버가 raw를 검증하고 conditions를 머지
3. BE가 chat_messages에 raw + merge된 conditions를 INSERT
4. 조건이 충족되면 BE가 housing_transactions / regions를 조회
5. regions 결과는 AI 서버로 반환되지만 DB에는 저장하지 않음
6. AI 서버가 bot_messages를 생성하여 FE로 반환
```

즉, DB의 책임은 아래 두 가지입니다.

- 사용자 입력 턴별 조건 이력 저장
- 조건 기반 지역 필터링을 위한 원천 데이터 보관

---

## 3. 테이블 상세

## 3.1 `regions`

### 역할

추천 결과에 사용되는 시군구 단위 지역 기준 테이블입니다.

문서 합의상 적재 범위는 MVP 시연용으로 아래를 포함할 수 있습니다.

- 서울 25개 구
- 경기 일부 시군구
- 예: 분당, 성남 등

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 지역 식별자 |
| `sido` | varchar(50) | not null | 시도명 |
| `sigungu` | varchar(50) | not null | 시군구명 |
| `created_at` | datetime | not null | 생성 일시 |
| `updated_at` | datetime | not null | 수정 일시 |

### 설명

- `regions`는 추천 결과 표시용 지역 기준 테이블입니다.
- MVP에서는 읍면동, 좌표, 행정코드 상세값은 제외합니다.
- `sido`, `sigungu` 조합은 유일해야 합니다.
- 향후 지도 기능이 필요해지면 좌표 또는 지역 코드 컬럼을 추가할 수 있습니다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `(sido, sigungu)` unique | 지역 중복 방지 |

---

## 3.2 `housing_transactions`

### 역할

국토교통부 실거래 기반 주거 거래 데이터를 저장하는 테이블입니다.

MVP v0에서는 전세와 월세만 사용합니다.

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 거래 데이터 식별자 |
| `region_id` | bigint | not null, FK | 지역 ID |
| `deal_type` | varchar(30) | not null | 거래 유형 |
| `deposit_amount` | bigint | nullable | 보증금 |
| `monthly_rent` | int | nullable | 월세 |
| `contract_date` | date | not null | 계약일 |
| `created_at` | datetime | not null | 적재 일시 |

### `deal_type` 예시

| 값 | 의미 |
|---|---|
| `jeonse` | 전세 |
| `monthly_rent` | 월세 |

### 설명

- BE 필터링의 핵심 원천 데이터입니다.
- v0에서는 `sale`을 적재하지 않습니다.
- 전세는 주로 `deposit_amount`를 사용합니다.
- 월세는 `deposit_amount`와 `monthly_rent`를 함께 사용할 수 있습니다.
- 정렬 기준은 평균 거래가 또는 거래량 기준으로 결정할 수 있습니다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `region_id` | 지역별 실거래 조회 |
| `deal_type` | 거래 유형별 조회 |
| `contract_date` | 기간 기준 조회 |
| `(deal_type, deposit_amount)` | 예산 기반 필터링 보조 |
| `(region_id, deal_type)` | 지역별 거래 유형 집계 최적화 |

---

## 3.3 `chat_messages`

### 역할

MVP의 세션 이력과 누적 조건을 저장하는 핵심 테이블입니다.

이 테이블은 기존 ERD의 `chat_messages` + `chat_conditions` 역할을 합친 단일 테이블입니다.

각 row는 "한 번의 사용자 입력 턴"을 의미합니다.

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | char(36) 또는 uuid | PK | 메시지/턴 식별자 |
| `session_id` | char(36) 또는 uuid | not null | 대화 세션 식별자 |
| `raw` | json | not null | 이번 턴 입력값 |
| `conditions` | json | not null | 누적 머지된 조건 |
| `created_at` | datetime | not null | 생성 일시 |

### `raw` 예시

```json
{ "budget_max": 200000000 }
```

```json
{ "deal_type": "jeonse" }
```

### `conditions` 예시

```json
{ "budget_max": 200000000, "deal_type": "jeonse" }
```

### 설명

- `raw`는 이번 턴에 새로 들어온 입력입니다.
- `conditions`는 AI 서버가 머지한 누적 상태입니다.
- AI 서버는 stateless이므로, 세션 상태는 이 테이블을 통해 복원합니다.
- 봇 응답 텍스트와 추천 결과는 이 테이블에 저장하지 않습니다.
- `raw_message` 자유 텍스트 입력은 Phase 2에서 `raw` JSON 내부 확장 필드로 다룰 수 있습니다.

### JSON 스키마 가이드

`raw`와 `conditions`에서 MVP v0 기준으로 사용하는 키는 아래와 같습니다.

| 키 | 타입 | 의미 |
|---|---|---|
| `budget_max` | bigint | 최대 예산 |
| `deal_type` | string | `jeonse` 또는 `monthly_rent` |

Phase 2 이후 확장 가능 예시:

| 키 | 의미 |
|---|---|
| `raw_message` | 자유 입력 원문 |
| `commute_destination` | 출퇴근 목적지 |
| `commute_limit_minutes` | 출퇴근 허용 시간 |

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `session_id` | 세션별 이력 조회 |
| `(session_id, created_at)` | 최신 conditions 복원 |
| `created_at` | 로그성 조회 |

---

## 4. 테이블 관계

```text
regions 1 : N housing_transactions

chat_messages는 별도 FK 없이 session_id 기준으로 세션 이력을 관리
```

### 관계 설명

- 하나의 지역은 여러 거래 데이터를 가질 수 있습니다.
- `chat_messages`는 지역 테이블과 직접 FK로 연결되지 않습니다.
- 추천 결과는 매 요청마다 계산되며 저장하지 않습니다.

---

## 5. 저장 예시

## 5.1 첫 질문 직후

사용자가 자본금 칩을 누른 경우:

```json
{
  "id": "8e13c7b2-7b2c-4b80-9a8e-0db6b2fd96aa",
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": { "budget_max": 200000000 },
  "conditions": { "budget_max": 200000000 },
  "created_at": "2026-04-25T14:00:00"
}
```

## 5.2 거래 유형까지 받은 후

```json
{
  "id": "3294cbcc-d0e8-4587-91f6-f3b96f6040d1",
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": { "deal_type": "jeonse" },
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "jeonse"
  },
  "created_at": "2026-04-25T14:00:08"
}
```

이후 BE는 위 `conditions`를 기준으로 `housing_transactions`를 필터링하고, `regions` 이름 목록을 반환합니다.

---

## 6. 추천 조회 관점 쿼리 모델

MVP v0의 주요 조회는 아래 형태를 가정합니다.

### 조건 저장

- `POST /internal/upsert-conditions`
- `session_id`가 없으면 새 UUID 발급
- `chat_messages`에 row INSERT

### 추천 조회

- `POST /internal/filter`
- 입력: `conditions`
- 처리:
  - `deal_type` 일치
  - 전세 기준 `deposit_amount <= budget_max`
  - 시군구 그룹화
  - 평균 거래가 또는 거래량 기준 정렬
  - 상위 3개 지역명 반환

즉, DB 관점의 출력은 저장용 테이블이 아니라 조회 결과 집합입니다.

---

## 7. DBML

```dbml
Table regions {
  id bigint [pk, increment]
  sido varchar(50) [not null]
  sigungu varchar(50) [not null]
  created_at datetime [not null]
  updated_at datetime [not null]

  Indexes {
    (sido, sigungu) [unique]
  }
}

Table housing_transactions {
  id bigint [pk, increment]
  region_id bigint [not null]
  deal_type varchar(30) [not null]
  deposit_amount bigint
  monthly_rent int
  contract_date date [not null]
  created_at datetime [not null]

  Indexes {
    region_id
    deal_type
    contract_date
    (deal_type, deposit_amount)
    (region_id, deal_type)
  }
}

Table chat_messages {
  id varchar(36) [pk]
  session_id varchar(36) [not null]
  raw json [not null]
  conditions json [not null]
  created_at datetime [not null]

  Indexes {
    session_id
    (session_id, created_at)
    created_at
  }
}

Ref: housing_transactions.region_id > regions.id
```

---

## 8. MVP에서 제외하는 항목

현재 설계에서는 아래를 의도적으로 제외합니다.

| 제외 항목 | 제외 이유 |
|---|---|
| `chat_conditions` | `chat_messages`의 `conditions` JSON으로 대체 |
| `recommendation_results` | 추천 결과는 계산 후 반환만 하고 저장하지 않음 |
| 봇 메시지 저장 테이블 | FE 렌더용 응답이며 MVP에서 영속화 불필요 |
| `users` | 회원 기능이 MVP 범위 아님 |
| `chat_sessions` | `session_id`로 충분 |
| 좌표/지도 전용 테이블 | MVP는 풀스크린 챗봇 중심, 지도 기능 제외 |

---

## 9. 기존 ERD 대비 변경점

기존 [ERD.md](./ERD.md) 대비 핵심 변경은 아래와 같습니다.

1. `chat_conditions` 제거
2. `chat_messages`에 `raw`, `conditions` JSON 추가
3. `conversation_key` 대신 `session_id` 사용
4. 봇 메시지 저장 전제 제거
5. `recommendation_results` 저장 모델 제거 유지
6. `housing_transactions.transaction_type`를 현재 합의된 `deal_type` 명칭으로 정리
7. 적재 범위를 "서울시만" 고정하지 않고 시연용 경기 일부 확장 가능하도록 정리

---

## 10. 최종 정리

현재 합의된 MVP 기준에서 DB는 "채팅형 추천 시스템의 상태 저장소"이지, "대화 전문과 추천 결과를 모두 저장하는 로그 DB"가 아닙니다.

따라서 가장 중요한 설계 포인트는 아래 두 가지입니다.

- `chat_messages` 단일 테이블로 세션별 입력 이력과 누적 조건을 저장한다.
- 추천 결과 텍스트와 지역 리스트는 저장하지 않고 요청 시 계산해서 반환한다.

이 기준이 `plan.md`, `backend-mvp.md`, `ai-backend.md`, `ai-frontend.md`와 가장 잘 일치합니다.
