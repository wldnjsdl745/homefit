# homefit API 명세서

- 문서 버전: `v0.2.0`
- 작성일: `2026-05-16`
- 문서 상태: `Draft`
- 적용 범위: `MVP v0 - 매매/월세 상한/서울 내부 추천 반영`
- 기준 문서:
  - [plan.md](../../plan.md)
  - [backend-mvp.md](../../backend-mvp.md)
  - [ai-backend.md](../../ai-backend.md)
  - [ai-frontend.md](../../ai-frontend.md)
  - [ERD.md](../data/ERD.md)

---

## 0. 문서 목적

본 문서는 homefit MVP v0에서 사용하는 API 계약을 한 곳에 정리한 문서입니다.

대상 범위:

- FE -> AI 서버 공개 API
- AI 서버 -> BE 내부 API
- 헬스체크 API

문서 원칙:

- FE는 AI 서버만 호출합니다.
- BE는 내부 API만 제공합니다.
- 추천 대상 지역은 서울 내부로 한정합니다.
- 추천 결과와 AI 설명 텍스트는 DB에 저장하지 않습니다.
- 세션 상태는 `chat_messages` 테이블의 `session_id`와 `conditions` JSON으로 관리합니다.

---

## 1. 시스템 구조

```text
Frontend -> AI Server -> Backend -> MySQL
```

역할 분리:

- FE: 사용자 입력 전송, `bot_messages` 렌더
- AI 서버: 공개 진입점, raw 검증, conditions 머지, BE 호출, 텍스트 가공, fallback 처리
- BE: conditions 저장, 거래 데이터 필터링, 서울 내부 지역 목록 반환

---

## 2. 공통 규칙

## 2.1 Content-Type

모든 POST 요청은 아래 헤더를 사용합니다.

```http
Content-Type: application/json
```

## 2.2 식별자 규칙

| 필드 | 타입 | 설명 |
|---|---|---|
| `session_id` | string(UUID) | 대화 세션 식별자 |
| `id` | string(UUID) | 개별 row 또는 메시지 식별자 |

## 2.3 상태값 규칙

AI 서버 응답의 `state`는 MVP v0에서 아래 값만 사용합니다.

| 값 | 의미 |
|---|---|
| `asking` | 다음 질문이 필요한 상태 |
| `result` | 추천 결과 또는 빈 결과를 반환한 상태 |

## 2.4 조건 키 규칙

MVP v0에서 사용하는 구조화 입력 키:

| 키 | 타입 | 설명 |
|---|---|---|
| `budget_max` | number | 최대 예산 |
| `deal_type` | string | `jeonse`, `monthly_rent`, `sale` 중 하나 |
| `monthly_rent_max` | number or null | 월세 선택 시 월마다 지출 가능한 월세 상한 |

완성된 condition item 규칙:

| 키 | 타입 | 설명 |
|---|---|---|
| `budget_max` | number | 원 단위 최대 예산 |
| `deal_type` | string | `jeonse`, `monthly_rent`, `sale` 중 하나 |
| `monthly_rent_max` | number or null | `deal_type="monthly_rent"`이면 원 단위 월세 상한, 그 외 거래 유형은 `null` |

## 2.5 추천 지역 범위

추천 지역은 서울 내부로 한정합니다.

- BE는 서울 지역 거래 데이터만 필터링 대상에 포함합니다.
- `regions`에는 서울 내부 지역명만 반환합니다.
- 추천 후보는 서울 지역 데이터로만 구성합니다.

## 2.6 Phase 2 확장 예정 키

| 키 | 설명 |
|---|---|
| `raw_message` | 자유 입력 원문 |
| `commute_destination` | 출퇴근 목적지 |
| `commute_limit_minutes` | 출퇴근 허용 시간 |

---

## 3. BotMessage 스키마

FE는 AI 서버 응답의 `bot_messages`만 렌더합니다.

MVP v0에서 사용하는 메시지 타입:

```ts
type BotMessage =
  | { type: "bot.text"; content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };
```

### `bot.text`

| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | string | `"bot.text"` 고정 |
| `content` | string | 사용자에게 보여줄 텍스트 |

### `bot.quick_replies`

| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | string | `"bot.quick_replies"` 고정 |
| `chips` | array | 후속 선택지 |

`chips` 내부 항목:

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | string | 칩 식별자 |
| `label` | string | 화면 표시용 라벨 |

---

## 4. FE -> AI 서버 공개 API

AI 서버는 FE의 유일한 공개 진입점입니다.

Base URL 예시:

```text
http://localhost:8000
```

## 4.1 `POST /chat`

### 목적

- 첫 진입 시 환영 메시지와 첫 질문 반환
- 사용자 입력 수신
- 누적 conditions 기반 다음 질문 또는 추천 결과 반환

### Request Body

```json
{
  "session_id": "uuid | null",
  "raw": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  }
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `session_id` | string or null | 아니오 | 첫 호출이면 `null` 또는 생략 가능 |
| `raw` | object | 예 | 이번 턴 입력값 |

### 요청 예시 1. 첫 진입

```json
{
  "session_id": null,
  "raw": {}
}
```

### 요청 예시 2. 자본금 선택

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": {
    "budget_max": 200000000
  }
}
```

### 요청 예시 3. 거래 유형 선택

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": {
    "deal_type": "monthly_rent"
  }
}
```

### 요청 예시 4. 월세 예산 입력

월세를 거래 유형으로 선택한 경우에만 추가로 전송합니다.

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": {
    "monthly_rent_max": 800000
  }
}
```

### Response 200: Asking Deal Type

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "전세, 월세, 매매 중 어떤 걸 원하시는지 알려주세요." },
    {
      "type": "bot.quick_replies",
      "chips": [
        { "id": "deal_jeonse", "label": "전세" },
        { "id": "deal_monthly_rent", "label": "월세" },
        { "id": "deal_sale", "label": "매매" }
      ]
    }
  ]
}
```

### Response 200: Asking Monthly Rent

거래 유형이 `monthly_rent`이면 월세 예산을 추가로 질문합니다.

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "월마다 나가는 월세 예산을 얼마로 생각하시나요?" }
  ]
}
```

FE는 사용자가 입력한 월세 금액을 원 단위 숫자로 변환해 다음 턴에 `monthly_rent_max`로 전송합니다.

### Response 200: Result

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "result",
  "bot_messages": [
    { "type": "bot.text", "content": "월세 보증금 2억, 월세 80만원 이하 조건에 맞는 서울 지역은 관악구·동작구·영등포구입니다." },
    {
      "type": "bot.quick_replies",
      "chips": [
        { "id": "restart", "label": "다시 추천" }
      ]
    }
  ]
}
```

### Response 200: Reprompt

잘못된 입력 또는 지원하지 않는 값이 들어오면 재질문 형태로 응답합니다.

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "다시 한번 알려주세요." },
    {
      "type": "bot.quick_replies",
      "chips": [
        { "id": "deal_jeonse", "label": "전세" },
        { "id": "deal_monthly_rent", "label": "월세" },
        { "id": "deal_sale", "label": "매매" }
      ]
    }
  ]
}
```

### Response 200: Empty Result

조건에 맞는 서울 지역이 없을 때도 정상 응답 형태를 유지합니다.

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "result",
  "bot_messages": [
    { "type": "bot.text", "content": "입력한 조건에 맞는 서울 지역을 찾지 못했어요. 자본금을 다시 입력해볼까요?" },
    {
      "type": "bot.quick_replies",
      "chips": [
        { "id": "retry_budget", "label": "자본금 다시" },
        { "id": "restart", "label": "다시 추천" }
      ]
    }
  ]
}
```

### Response 200: Fallback

BE 호출 실패 등 서버 내부 문제는 fallback 응답으로 흡수합니다.

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "죄송해요, 다시 시도해주세요." },
    {
      "type": "bot.quick_replies",
      "chips": [
        { "id": "retry", "label": "재시도" }
      ]
    }
  ]
}
```

### 처리 규칙

- 첫 호출에서는 `session_id`가 없으면 새 세션을 생성합니다.
- AI 서버는 `raw`를 검증한 뒤 conditions를 머지합니다.
- 필요한 값이 부족하면 `state="asking"`으로 다음 질문을 반환합니다.
- 질문 순서는 자본금, 거래 유형, 월세 예산 순서입니다.
- 월세 예산 질문은 `deal_type="monthly_rent"`인 경우에만 사용합니다.
- `budget_max`, `deal_type`, 월세 선택 시 `monthly_rent_max`가 모두 있으면 BE를 호출해 추천 결과를 생성합니다.
- 전세와 매매 condition의 `monthly_rent_max`는 `null`로 전달합니다.
- 결과가 비어 있어도 `state="result"`를 사용합니다.
- FE는 실패 분기를 별도로 두지 않고 `bot_messages`를 그대로 렌더합니다.

### 검증 규칙

| 필드 | 규칙 |
|---|---|
| `budget_max` | 양수 정수, 상한 검증 필요 |
| `deal_type` | `jeonse`, `monthly_rent`, `sale`만 허용 |
| `monthly_rent_max` | `monthly_rent` 선택 시 양수 정수 필수. 그 외에는 `null` 또는 생략 가능 |

---

## 5. AI 서버 -> BE 내부 API

BE API는 내부 전용입니다. FE는 직접 호출하지 않습니다.

Base URL 예시:

```text
http://backend:8080
```

인증 정책:

- MVP에서는 같은 내부 네트워크 전제를 둡니다.
- 운영 단계에서는 `X-Internal-Token` 도입을 권장합니다.

## 5.1 `POST /internal/upsert-conditions`

### 목적

- 세션 생성 또는 기존 세션 업데이트
- `chat_messages`에 raw + conditions 저장
- 저장된 누적 conditions 반환

### Request Body

```json
{
  "session_id": "uuid | null",
  "raw": {
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  },
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  }
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `session_id` | string or null | 아니오 | 없으면 BE가 새 UUID 생성 |
| `raw` | object | 예 | 이번 턴 입력 |
| `conditions` | object | 예 | AI 서버가 머지한 누적 조건 |

### Response 200

```json
{
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  }
}
```

### 처리 규칙

- `session_id`가 `null`이면 새 UUID를 생성합니다.
- `chat_messages` 테이블에 새 row를 INSERT 합니다.
- DB 저장 컬럼은 `session_id`, `raw`, `conditions`, `created_at` 입니다.
- 응답에는 최종 `session_id`와 저장된 `conditions`를 그대로 반환합니다.

### DB 반영 예시

```json
{
  "id": "3294cbcc-d0e8-4587-91f6-f3b96f6040d1",
  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
  "raw": {
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  },
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  },
  "created_at": "2026-04-25T14:00:08"
}
```

## 5.2 `POST /internal/filter`

### 목적

- 누적 conditions를 기준으로 거래 데이터를 필터링
- 서울 내부 추천 지역 이름 목록 반환

### Request Body

```json
{
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "monthly_rent",
    "monthly_rent_max": 800000
  }
}
```

### Response 200

```json
{
  "regions": ["관악구", "동작구", "영등포구"]
}
```

### 결과 없음 예시

```json
{
  "regions": []
}
```

### 처리 규칙

- `deal_type` 일치 조건으로 필터링합니다.
- `budget_max`는 API에서 원 단위로 받습니다.
- DB의 `deposit_amount`는 만원 단위이므로 BE에서 `budget_max / 10000`으로 변환한 뒤 비교합니다.
- 전세 기준은 `deposit_amount <= budget_max_in_manwon`를 사용합니다.
- 매매 데이터도 `deposit_amount` 컬럼에 매매가를 만원 단위로 저장하며, 매매 기준은 `deposit_amount <= budget_max_in_manwon`를 사용합니다.
- 월세 기준은 `deposit_amount <= budget_max_in_manwon`와 `monthly_rent <= monthly_rent_max_in_manwon`를 함께 사용합니다.
- DB의 `monthly_rent`는 만원 단위이므로 BE에서 `monthly_rent_max / 10000`으로 변환한 뒤 비교합니다.
- 서울 지역 거래 데이터만 필터링 대상에 포함합니다.
- 서울 내부 지역 기준으로 그룹화합니다.
- 평균 거래가 또는 거래량 기준으로 정렬합니다.
- 상위 3개 지역명을 반환합니다.
- 결과는 저장하지 않습니다.

---

## 6. 헬스체크 API

## 6.1 AI 서버 `GET /healthz`

### 목적

- AI 서버 프로세스 생존 확인

### Response 200 예시

```json
{
  "status": "ok"
}
```

## 6.2 BE `GET /healthz` 또는 `GET /actuator/health`

### 목적

- Backend 애플리케이션 및 내부 상태 점검

### Response 200 예시

```json
{
  "status": "UP"
}
```

---

## 7. 에러 및 fallback 정책

## 7.1 FE 관점 정책

- FE는 AI 서버 응답을 그대로 렌더합니다.
- AI 실패와 BE 실패는 AI 서버가 fallback 응답으로 흡수합니다.
- 즉, FE는 `bot_messages` 기준으로만 동작합니다.

## 7.2 에러 코드 가이드

아래는 문서상 권장 가이드입니다.

| error_code | HTTP | 설명 | FE 처리 |
|---|---|---|---|
| `INVALID_SESSION` | 400 | 유효하지 않은 세션 | 새 세션 시작 유도 |
| `INVALID_RAW` | 400 | 입력 스키마 오류 | 재질문 또는 새로 시작 |
| `NO_CANDIDATES` | 200 | 조건 일치 지역 없음 | 빈 결과 텍스트 렌더 |
| `AI_UNAVAILABLE` | 200 | AI fallback 응답 | 분기 없이 렌더 |
| `INTERNAL_ERROR` | 500 | 예기치 않은 장애 | 재시도 유도 |

실제 MVP v0에서는 가능한 한 AI 서버가 `200 + fallback bot_messages`로 흡수하는 방향을 우선합니다.

---

## 8. 세션 및 상태 관리 규칙

세션 관련 원칙:

- 세션 상태는 BE DB가 보유합니다.
- AI 서버는 stateless 오케스트레이터입니다.
- 최신 세션 상태는 `chat_messages`의 최신 `conditions`로 복원합니다.

저장 모델:

```text
chat_messages
- id
- session_id
- raw
- conditions
- created_at
```

비저장 항목:

- 추천 결과 리스트
- AI 설명 텍스트
- 봇 메시지 전문

---

## 9. 칩 매핑 가이드

FE는 칩 클릭을 구조화된 `raw`로 변환해서 AI 서버에 전달합니다.

### 자본금 칩

| 칩 라벨 | 전송값 |
|---|---|
| `1억 미만` | `{ "budget_max": 50000000 }` |
| `1–3억` | `{ "budget_max": 200000000 }` |
| `3–5억` | `{ "budget_max": 400000000 }` |
| `5억 이상` | `{ "budget_max": 700000000 }` |

### 거래 유형 칩

| 칩 라벨 | 전송값 |
|---|---|
| `전세` | `{ "deal_type": "jeonse" }` |
| `월세` | `{ "deal_type": "monthly_rent" }` |
| `매매` | `{ "deal_type": "sale" }` |

### 월세 예산 입력

월세를 선택한 경우에만 일반 입력으로 받습니다. FE는 사용자가 입력한 값을 원 단위 숫자로 변환해 AI 서버에 전달합니다.

| 사용자 입력 예시 | 전송값 |
|---|---|
| `50만원` | `{ "monthly_rent_max": 500000 }` |
| `80만원` | `{ "monthly_rent_max": 800000 }` |
| `100만원` | `{ "monthly_rent_max": 1000000 }` |

---

## 10. Phase 2 확장 포인트

현재 API는 MVP v0 기준이며, 아래와 같이 확장 가능합니다.

| 항목 | 확장 방향 |
|---|---|
| 사용자 입력 | `raw_message` 필드 추가 |
| AI 설명 | 더 자연스러운 LLM 설명 생성 |
| 결과 형식 | `bot.cards` 등 구조화 메시지 추가 |
| streaming | SSE 또는 chunked response 도입 |
| 조건 필드 | 출퇴근 목적지, 통근 시간 등 추가 |

중요 원칙:

- `POST /chat` 엔드포인트는 유지합니다.
- FE 인터페이스는 가능한 한 깨지지 않게 확장합니다.
- 추천 순위는 여전히 BE가 결정하고 AI는 설명만 담당합니다.

---

## 11. 최종 요약

MVP v0의 API 구조는 아래 세 줄로 정리할 수 있습니다.

1. FE는 `POST /chat`만 호출합니다.
2. AI 서버는 `POST /internal/upsert-conditions`, `POST /internal/filter`를 호출합니다.
3. DB에는 `chat_messages`의 `raw`와 `conditions`만 저장하고 추천 결과는 저장하지 않습니다.
