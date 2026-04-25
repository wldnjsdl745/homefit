# homefit ERD 문서

- 문서 버전: `v0.1.2`
- 작성일: `2026-04-25`
- 문서 상태: `Draft`
- 적용 범위: `MVP`
- 기준 데이터: `서울시 전월세 실거래 데이터`
- 서비스 형태: `챗봇 기반 거주 지역 추천 서비스`

---

## 0. 버전 이력

| 버전 | 일자 | 상태 | 변경 내용 |
|---|---|---|---|
| `v0.1.0` | 2026-04-25 | Draft | MVP 초기 ERD 작성. `regions`, `housing_transactions`, `chat_messages`, `recommendation_results` 4개 테이블 기준으로 설계 |
| `v0.1.1` | 2026-04-25 | Draft | `recommendation_results`를 제거하고, 사용자 채팅 메시지에서 추출한 예산과 거래 유형을 저장하는 `chat_conditions` 테이블로 변경 |
| `v0.1.2` | 2026-04-25 | Draft | MVP 기준 데이터를 서울시 전월세 실거래 데이터로 한정하고, `regions`를 서울시 시군구 단위 지역 테이블로 단순화 |

---

## 1. 개요

homefit의 MVP 데이터베이스는 **서울시 시군구 지역 정보**, **전월세 실거래 데이터**, **챗봇 메시지**, **사용자 추천 조건**을 중심으로 구성한다.

MVP에서는 별도 전국 지역 데이터를 적재하지 않고, 전월세 실거래 데이터에 포함된 서울시 시군구 정보를 기준으로 `regions`를 구성한다.

MVP에서는 회원 기능을 제외하고, 사용자가 챗봇에 입력한 조건을 기반으로 지역을 추천한다.  
대화는 별도 세션 테이블을 두지 않고 `chat_messages.conversation_key`로 묶는다.

MVP에서는 지도 표시나 좌표 기반 거리 계산을 포함하지 않으므로, `regions` 테이블에 위도/경도 컬럼을 저장하지 않는다.  
추후 지도 기능 또는 거리 기반 추천이 필요해지면 `regions`에 좌표 컬럼을 추가하거나 별도 좌표 테이블로 분리한다.

---

## 2. 테이블 목록

| 테이블명 | 역할 |
|---|---|
| `regions` | 서울시 시군구 단위 지역 정보 저장 |
| `housing_transactions` | 서울시 전월세 및 추후 매매 실거래 데이터 저장 |
| `chat_messages` | 챗봇 사용자/봇 메시지 저장 |
| `chat_conditions` | 사용자 채팅 메시지에서 추출한 예산과 거래 유형 저장 |

---

## 3. 테이블 상세

## 3.1 `regions`

### 역할

서울시 시군구 단위의 지역 정보를 저장하는 테이블이다.  
MVP에서는 별도 전국 지역 데이터를 사용하지 않고, 전월세 실거래 데이터에 포함된 서울시 지역 정보를 기준으로 구성한다.

전월세 실거래 데이터는 `regions`를 기준으로 연결된다.

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 지역 내부 식별자 |
| `sido` | varchar(50) | not null | 시도명 |
| `sigungu` | varchar(50) | not null | 시군구명 |
| `created_at` | datetime | not null | 생성 일시 |
| `updated_at` | datetime | not null | 수정 일시 |

### 설명

- MVP에서는 서울특별시 시군구 단위의 지역 정보만 저장한다.
- `regions`는 전월세 실거래 데이터에 포함된 시군구 정보를 정규화하기 위한 기준 테이블이다.
- 별도 전국 지역 코드 데이터는 사용하지 않는다.
- `sido`, `sigungu` 조합은 중복되지 않아야 한다.
- 읍면동, 위도, 경도 정보는 MVP 추천 로직에서 사용하지 않으므로 제외한다.
- 추후 읍면동 단위 추천, 지도 기능, 거리 기반 추천이 필요해지면 컬럼을 추가하거나 별도 테이블로 분리한다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `(sido, sigungu)` unique | 동일 시도/시군구 중복 저장 방지 |

---

## 3.2 `housing_transactions`

### 역할

주거 실거래 데이터를 저장하는 테이블이다.  
MVP에서는 서울시 전월세 실거래 데이터를 저장한다.

추후 매매 데이터도 함께 저장할 수 있도록 `transaction_type`을 둔다.

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 실거래 데이터 식별자 |
| `region_id` | bigint | not null, FK | 지역 ID |
| `transaction_type` | varchar(30) | not null | 거래 유형 |
| `deal_year_month` | varchar(6) | not null | 계약년월 |
| `deal_day` | int | nullable | 계약일 |
| `housing_type` | varchar(30) | nullable | 주택 유형 |
| `deposit_amount` | bigint | nullable | 보증금 |
| `monthly_rent` | int | nullable | 월세 |
| `sale_price` | bigint | nullable | 매매가 |
| `created_at` | datetime | not null | 생성 일시 |

### `transaction_type` 예시

| 값 | 의미 |
|---|---|
| `JEONSE` | 전세 |
| `MONTHLY_RENT` | 월세 |

### 설명

- MVP에서는 서울시 전월세 실거래 데이터만 적재한다.
- `region_id`는 전월세 데이터의 시도/시군구 정보를 기준으로 `regions`와 매칭한다.
- 현재 MVP에서는 `JEONSE`, `MONTHLY_RENT` 데이터를 중심으로 사용한다.
- 추후 매매 데이터가 추가되면 `transaction_type = SALE`, `sale_price`를 활용한다.
- 전세의 경우 `deposit_amount`는 보증금, `monthly_rent`는 0 또는 null로 저장할 수 있다.
- 월세의 경우 `deposit_amount`와 `monthly_rent`를 함께 저장한다.
- `deal_year_month`는 `YYYYMM` 형식으로 저장한다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `region_id` | 지역별 실거래 조회 |
| `deal_year_month` | 기간별 실거래 조회 |
| `transaction_type` | 전세/월세/매매 유형별 조회 |
| `(region_id, deal_year_month)` | 특정 지역의 월별 실거래 조회 최적화 |

---

## 3.3 `chat_messages`

### 역할

챗봇 대화 메시지를 저장하는 테이블이다.  
사용자 메시지와 봇 메시지를 모두 이 테이블에 저장한다.

별도의 `chat_sessions` 테이블은 두지 않고, `conversation_key`를 통해 같은 대화 흐름을 묶는다.

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 메시지 식별자 |
| `conversation_key` | varchar(36) | not null | 대화 묶음 식별자 |
| `sender_type` | varchar(20) | not null | 메시지 발신자 |
| `message_type` | varchar(30) | not null | 메시지 유형 |
| `content` | text | not null | 메시지 내용 |
| `created_at` | datetime | not null | 생성 일시 |

### `sender_type` 예시

| 값 | 의미 |
|---|---|
| `USER` | 사용자 메시지 |
| `BOT` | 챗봇 메시지 |

### `message_type` 예시

| 값 | 의미 |
|---|---|
| `USER_MESSAGE` | 사용자가 입력한 일반 메시지 |
| `BOT_MESSAGE` | 일반 봇 응답 |
| `CLARIFICATION` | 추가 조건 확인 질문 |
| `RECOMMENDATION` | 지역 추천 결과 메시지 |

### 설명

- `conversation_key`는 하나의 챗봇 대화 흐름을 구분하는 UUID 값이다.
- 회원 기능이 없는 MVP에서는 사용자 식별자 대신 `conversation_key`를 사용한다.
- 추천 조건은 `chat_messages`에 직접 저장하지 않고, 별도 `chat_conditions` 테이블에 구조화하여 저장한다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `conversation_key` | 특정 대화의 메시지 조회 |
| `(conversation_key, created_at)` | 대화 메시지 시간순 조회 |

---

## 3.4 `chat_conditions`

### 역할

사용자 채팅 메시지에서 추출한 추천 조건을 저장하는 테이블이다.  
AI 또는 백엔드가 사용자 메시지에서 예산과 거래 유형을 추출한 뒤, 해당 값을 구조화하여 저장한다.

이 테이블은 추천 결과를 저장하는 테이블이 아니라, **AI에게 전달하거나 백엔드 추천 로직에서 사용할 사용자 조건 데이터를 저장하는 테이블**이다.

예를 들어 사용자가 다음과 같이 입력한 경우:

```text
전세 2억 이하로 서울 근처 추천해줘
```

다음과 같은 값으로 저장할 수 있다.

```json
{
  "budget": 200000000,
  "dealType": "JEONSE"
}
```

### 컬럼

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| `id` | bigint | PK, auto increment | 사용자 조건 데이터 식별자 |
| `chat_message_id` | bigint | not null, FK, unique | 조건이 추출된 사용자 채팅 메시지 ID |
| `budget` | bigint | nullable | 사용자가 입력한 예산 |
| `deal_type` | varchar(30) | nullable | 사용자가 원하는 거래 유형 |

### `deal_type` 예시

| 값 | 의미 |
|---|---|
| `JEONSE` | 전세 |
| `MONTHLY_RENT` | 월세 |

### 설명

- `chat_message_id`는 조건이 추출된 사용자 메시지를 참조한다.
- `budget`은 사용자가 입력한 예산 금액을 숫자 형태로 저장한다.
- `deal_type`은 사용자가 원하는 거래 유형을 저장한다.
- MVP에서는 `budget`, `deal_type`만 저장한다.
- 추후 고도화 시 희망 지역, 월세 한도, 나이대, 제외 조건 등을 추가할 수 있다.

### 인덱스

| 인덱스 | 목적 |
|---|---|
| `chat_message_id` unique | 하나의 사용자 메시지에 대해 하나의 조건 데이터만 저장 |

---

## 4. 테이블 관계

```text
regions 1 : N housing_transactions

chat_messages 1 : 1 chat_conditions
```

### 관계 설명

- 하나의 서울시 시군구 지역은 여러 개의 실거래 데이터를 가질 수 있다.
- 하나의 사용자 채팅 메시지는 하나의 조건 데이터를 가질 수 있다.
- `chat_conditions`는 사용자 메시지에서 추출한 예산과 거래 유형을 저장한다.

---

## 5. 주요 서비스 흐름

## 5.1 챗봇 추천 흐름

```text
1. 사용자가 챗봇에 메시지를 입력한다.
2. 사용자 메시지를 chat_messages에 저장한다.
3. 사용자 메시지에서 예산과 거래 유형을 추출한다.
4. 추출된 budget, deal_type을 chat_conditions에 저장한다.
5. chat_conditions 값을 기반으로 housing_transactions와 regions를 조회한다.
6. 조건에 맞는 서울시 시군구별 평균 보증금, 평균 월세, 거래 수 등을 계산한다.
7. 백엔드 또는 AI 서버가 추천 답변을 생성한다.
8. 프론트엔드에 챗봇 답변과 추천 지역 목록을 반환한다.
```

## 5.2 예시

사용자 입력:

```text
전세 2억 이하로 서울 근처 살만한 지역 추천해줘
```

`chat_messages` 저장 예시:

```json
{
  "conversationKey": "550e8400-e29b-41d4-a716-446655440000",
  "senderType": "USER",
  "messageType": "USER_MESSAGE",
  "content": "전세 2억 이하로 서울 근처 살만한 지역 추천해줘"
}
```

`chat_conditions` 저장 예시:

```json
{
  "chatMessageId": 1,
  "budget": 200000000,
  "dealType": "JEONSE"
}
```

봇 추천 메시지 저장 예시:

```json
{
  "conversationKey": "550e8400-e29b-41d4-a716-446655440000",
  "senderType": "BOT",
  "messageType": "RECOMMENDATION",
  "content": "조건에 맞는 지역으로 관악구, 구로구, 광명시를 추천드려요."
}
```

---

## 6. DBML

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

  transaction_type varchar(30) [not null]
  deal_year_month varchar(6) [not null]
  deal_day int

  housing_type varchar(30)
  deposit_amount bigint
  monthly_rent int
  sale_price bigint

  created_at datetime [not null]

  Indexes {
    region_id
    deal_year_month
    transaction_type
    (region_id, deal_year_month)
  }
}

Table chat_messages {
  id bigint [pk, increment]

  conversation_key varchar(36) [not null]
  sender_type varchar(20) [not null]
  message_type varchar(30) [not null]

  content text [not null]
  created_at datetime [not null]

  Indexes {
    conversation_key
    (conversation_key, created_at)
  }
}

Table chat_conditions {
  id bigint [pk, increment]
  chat_message_id bigint [not null, unique]

  budget bigint
  deal_type varchar(30)

  Indexes {
    chat_message_id
  }
}

Ref: housing_transactions.region_id > regions.id

Ref: chat_conditions.chat_message_id > chat_messages.id
```

---

## 7. MVP 기준 제외한 테이블

MVP에서는 아래 테이블을 제외한다.

| 제외 테이블 | 제외 이유 |
|---|---|
| `users` | 회원 기능이 MVP 핵심이 아님 |
| `chat_sessions` | `chat_messages.conversation_key`로 대화 묶음 처리 가능 |
| `favorite_regions` | 로그인/회원 기능이 없으면 서버 저장 필요성이 낮음 |
| `recommendation_results` | MVP에서는 추천 결과 스냅샷을 저장하지 않고, 사용자 조건 데이터만 저장 |
| `ai_request_logs` | 초기 MVP에서는 디버깅 로그를 애플리케이션 로그로 대체 가능 |
| `ai_explanations` | 추천 설명은 별도 테이블로 분리하지 않고 챗봇 응답 메시지로 저장 |
| `region_access_stats` | 현재 보유 데이터가 서울시 전월세 데이터 중심이므로 제외 |
| `infra_stats` | 인프라 데이터 미보유로 MVP 제외 |
| `safety_stats` | 안전/리스크 데이터 미보유로 MVP 제외 |
| `region_coordinates` | MVP에서는 지도 표시나 거리 기반 추천을 포함하지 않으므로 제외 |

---

## 8. 최종 정리

homefit MVP의 ERD는 다음 4개 테이블로 구성한다.

```text
regions
housing_transactions
chat_messages
chat_conditions
```

이 구조는 현재 보유한 **서울시 전월세 실거래 데이터**만으로 구현 가능하며, 챗봇 형식의 추천 서비스 흐름에도 맞다.

`regions`는 별도 전국 지역 데이터가 아니라, 서울시 전월세 데이터에 포함된 시군구 정보를 정규화한 테이블이다.

`chat_conditions`는 사용자 채팅 메시지에서 추출한 예산과 거래 유형을 구조화하여 저장하는 테이블이다.  
이 값은 AI 서버에 전달하거나 백엔드 추천 로직에서 사용할 수 있다.

추후 고도화 시 매매 데이터는 `housing_transactions.transaction_type = SALE`과 `sale_price`로 확장하고, 추천 결과 스냅샷이 필요해지면 `recommendation_results`를 추가할 수 있다. 회원 기능이 필요해지면 `users`, `favorite_regions`, `chat_sessions`를 추가할 수 있다.
