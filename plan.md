# Homefit — Frontend 설계 문서 (MVP)

> 국토교통부 공공데이터 기반 **주거 지역 추천 챗봇 사이트** 의 MVP 설계.
> 본 문서는 **Frontend** 영역만 다룬다.
> 관련 문서:
> - Backend 구현: [backend-mvp.md](backend-mvp.md)
> - AI (FE 관점): [ai-frontend.md](ai-frontend.md)
> - AI (BE 관점): [ai-backend.md](ai-backend.md)

---

## 0. 역할 분담 / 본 문서 범위

| 영역 | 담당 | 본 문서 |
|------|------|---------|
| **Frontend** (UI/UX, 상태, API 연동, 챗봇 인터페이스) | 이안 | ✅ |
| AI (프롬프트, Provider, JSON 검증, fallback) | 이안 | ❌ ([ai-frontend.md](ai-frontend.md) / [ai-backend.md](ai-backend.md)) |
| Backend (API, 데이터 적재, 점수식, Docker) | 주니어 | ❌ ([backend-mvp.md](backend-mvp.md)) |

**원칙 (AI 중심 파이프라인)**
- **FE의 진입점은 AI 서버** (BE 직접 호출 ❌)
- 흐름: `FE → AI 서버 → BE → AI 서버 → FE`
- AI 서버 = 의미 추출 + 설명 텍스트 생성 + FE-facing 진입점
- BE = conditions 저장 + DB 필터링 (내부 API만)
- FE는 AI 서버 응답(`bot_messages[]`)을 그대로 렌더
- **AI 정상/실패 분기 없음.** AI 서버가 fallback으로 흡수
- **MVP는 LLM 실호출 없음.** AI 서버는 양방향 통과 + 텍스트 템플릿

---

## 1. 시스템 아키텍처

```
┌──────────┐  POST /chat (public)   ┌──────────────┐  internal call  ┌──────────────┐
│ Frontend │ ──────────────────────▶│   AI 서버    │ ───────────────▶│   Backend    │
│  (SPA)   │ ◀──────────────────────│  (FastAPI)   │ ◀───────────────│ (Spring Boot)│
└──────────┘  { state, bot_messages}│ - 통과/추출  │ conditions/     │ - conditions │
                                    │ - 텍스트 가공│ regions         │ - DB 필터링  │
                                    └──────────────┘                 └──────┬───────┘
                                                                            ▼
                                                                       ┌──────────┐
                                                                       │  MySQL   │
                                                                       │ (단일 테이블)│
                                                                       └──────────┘
```

**핵심**
- AI 서버가 **FE의 유일한 진입점**.
- BE는 **AI 서버에서만 호출**되는 내부 API. FE에 직접 노출 ❌.

**책임**
- **FE**: 폼/칩 입력 + `bot_messages[]` 렌더만.
- **AI 서버 (Python FastAPI)**:
  - FE-facing `POST /chat` 엔드포인트
  - MVP: 양방향 통과 + 충족 시 BE 결과를 텍스트 템플릿으로 가공
  - Phase 2: 자유 텍스트 → 의도 추출 (LLM)
  - fallback도 AI 서버가 흡수
- **BE (Spring Boot)**: 내부 API. conditions 저장 + DB 필터링.
- **DB (MySQL)**: conditions만 영속화. AI 텍스트 / regions 결과는 미저장.

**왜 AI 서버가 진입점인가**
- AI가 "의미 추출 + 설명 생성"을 책임지는 AI 중심 파이프라인 의도
- Phase 2 LLM 도입 시 인터페이스/구조 변경 불필요
- BE 책임이 명확 (계산 + 저장만)

---

## 2. 데이터 흐름

### 2.1 부족 필드 케이스 (조건 더 받아야 함)
```
FE: POST /chat { session_id?, raw }
   ▼
AI 서버: (MVP) raw 그대로 통과 → BE 호출
   ▼
BE: 1) session_id 발급 또는 조회
    2) chat_messages INSERT (raw + 머지된 conditions 저장)
    3) 충족 판정 → 부족 → next_field 반환
   ▼
AI 서버: BE 결과 → bot_messages 구성 (next_field에 맞는 질문 + 칩)
   ▼
FE: bot_messages 렌더
```

### 2.2 충족 케이스 (추천 결과 생성)
```
FE: POST /chat { session_id, raw }
   ▼
AI 서버: (MVP) raw 통과 → BE 호출
   ▼
BE: 1) chat_messages INSERT (조건 누적)
    2) 충족 → DB 필터링 → regions 리스트 반환 (저장 ❌)
   ▼
AI 서버: regions를 텍스트로 가공 (MVP는 템플릿)
   "전세 2억 예산에 맞는 지역은 분당, 성남, 경기도입니다."
   bot_messages = [bot.text(텍스트), bot.quick_replies([다시 추천])]
   ▼
FE: 텍스트 말풍선 + 후속 칩 렌더
```

### 2.3 추가 질문 케이스 (Phase 2)
```
FE: POST /chat { session_id, raw_message: "예산 좀 더 늘려서..." }
   ▼
AI 서버: LLM 의도 추출 → raw 추출
   ▼
BE: chat_messages INSERT (merge 후 conditions UPDATE) + 재필터
   ▼
AI 서버: 새 regions를 텍스트로 가공
   ▼
FE
```

---

## 3. UI 구성 — 풀스크린 챗봇

### 3.1 결정

**풀스크린 챗봇 (지도/사이드 패널 없음).** ChatGPT/Claude artifact 스타일.

**근거**
- 최종 목적("한 줄 입력 → 동네 추천")과 가장 잘 맞음
- 지도 없이 시각화만으로 좌측 패널 정당성이 약함
- 모바일/데스크톱 동일 레이아웃 → 반응형 단순
- 차후 RAG/멀티턴/Tool Use 강화 시 자연스러운 진화

### 3.2 레이아웃 (모든 브레이크포인트 공통)

```
┌─────────────────────────────────────┐
│ Header: 로고 / 새 대화              │
├─────────────────────────────────────┤
│                                     │
│ AI: 안녕하세요! 어떤 동네 찾으세요? │
│     예산이 어느 정도 되세요?        │
│     [50만↓][50–80][80↑][직접입력]   │
│                                     │
│ 나: 70만원                          │
│                                     │
│ AI: 분석했습니다.                   │
│   ┌───────────────────────────────┐ │
│   │ ★1위 봉천동                   │ │
│   │ 평균 월세 65만 / 점수 86      │ │
│   │ AI: 예산 적합도가 높은 지역.. │ │
│   └───────────────────────────────┘ │
│   ┌───────────────────────────────┐ │
│   │ ★2위 신림동                   │ │
│   └───────────────────────────────┘ │
│   ┌───────────────────────────────┐ │
│   │ ★3위 사당동                   │ │
│   └───────────────────────────────┘ │
│   [비교 보기] [다시 추천]           │
│                                     │
│ ─────────────────────────────────── │
│ [입력창]                     [전송] │
└─────────────────────────────────────┘
```

- **데스크톱**: 가운데 컬럼 max-width 720px (가독성), 양옆 여백
- **모바일**: 전체 폭. 카드도 메시지 폭에 맞춤
- 비교 표는 `[비교 보기]` 칩 → 하단 슬라이드업 시트(모바일) / 모달(데스크톱)
- 카드 클릭 → 인라인 펼침(accordion) — 점수 상세, AI reason 전체

### 3.3 첫 진입 UX (2질문 MVP v0)

> MVP v0은 **자본금 + 거래 유형** 두 질문으로 추천. 매매는 v0 제외 (전세/월세만).
> 페이지 로드 시 자동으로 첫 호출 → 환영 메시지 + 첫 질문 도착.

**대화 시나리오**
```
[페이지 로드 시 자동]
FE → AI 서버: POST /chat { session_id: null, raw: {} }

[AI 서버 → BE → AI 서버 → FE]
bot.text: "원하시는 조건에 맞는 집을 찾아드릴게요."
bot.text: "출퇴근과 예산에 맞는 집을 추천해드릴게요."
bot.text: "먼저 자본금이 어느 정도인지 알려주세요."
bot.quick_replies: [1억 미만][1–3억][3–5억][5억 이상]

[사용자 칩 클릭]
FE → AI 서버: POST /chat { session_id, raw: { budget_max: 200000000 } }

[AI 서버 → BE → AI 서버 → FE]
bot.text: "전세/월세 중 어떤 걸 원하시는지 알려주세요."
bot.quick_replies: [전세][월세]

[사용자 칩 클릭]
FE → AI 서버: POST /chat { session_id, raw: { deal_type: "jeonse" } }

[AI 서버 → BE: 충족 → DB 필터링 → regions]
[AI 서버: 텍스트 가공]
bot.text: "잠시만요..."   (선택 — 클라이언트 typing indicator로 대체 가능)
bot.text: "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다."
bot.quick_replies: [다시 추천]
```

### 3.4 점진 확장 경로

| 버전 | 추가 질문 | 변화 |
|------|-----------|------|
| **v0 (MVP)** | 자본금 + 거래 유형 (전세/월세) | 가격 필터 + 평균 매물 가격 정렬 |
| v1 | + 출퇴근 목적지 | transit 점수 |
| v2 | + 출퇴근 시간 | transit 필터 |
| v3 | + 매매 추가 | sale 거래 유형 활성화 |
| v4 | + 자유 텍스트 입력 (Phase 2 LLM) | AI 서버 의도 추출 활성화 |
| v5 | + 카드/구조화 결과 | bot.cards 메시지 타입 추가 |

각 버전이 **그 자체로 동작하는 추천 시스템**.

### 3.5 챗봇 메시지 타입 (v0)

```ts
type BotMessage =
  | { type: "bot.text";          content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };
```

> v0은 2종만 사용. 카드/요약/주의 박스 등은 v1+에서 추가.

### 3.6 라우팅

| Path | 화면 |
|------|------|
| `/` | 풀스크린 챗봇 (단일 화면) |

> SPA 단일 라우트. 챗봇 상태 + 결과 상태가 컴포넌트 state.

---

## 4. API 계약 (Frontend ↔ AI 서버)

> FE는 **AI 서버**의 `/chat` 엔드포인트만 호출. BE는 AI 서버가 내부에서 호출.
> AI 서버 ↔ BE 계약은 [ai-backend.md](ai-backend.md) / [backend-mvp.md](backend-mvp.md) 참고.

### 4.1 POST /chat — 단일 대화 엔드포인트 (FE → AI 서버)

**Request**
```json
{
  "session_id": "sess_abc123",         // 첫 호출에선 생략 또는 null
  "raw":        { "budget_max": 700000 }
}
```

> MVP는 FE가 구조화된 `raw`만 보낸다. Phase 2에 `raw_message` 필드 추가.
> 자유 텍스트 입력 / 정규식 / 의도 추출은 FE 책임이 아님.

**Response 200 — ASKING (다음 질문 필요)**
```json
{
  "session_id": "sess_abc123",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "거래 유형이 어떻게 되세요?" },
    { "type": "bot.quick_replies", "chips": [
        { "id": "deal_monthly_rent", "label": "월세" },
        { "id": "deal_jeonse",       "label": "전세" },
        { "id": "deal_sale",         "label": "매매" }
      ]
    }
  ]
}
```

**Response 200 — RESULT (모든 필드 충족, 추천 완료)**
```json
{
  "session_id": "sess_abc123",
  "state": "result",
  "bot_messages": [
    { "type": "bot.text", "content": "전세 2억 예산에 맞는 지역은 분당, 성남, 경기도입니다." },
    { "type": "bot.quick_replies", "chips": [
        { "id": "restart", "label": "다시 추천" }
      ]
    }
  ]
}
```

> v0 결과 = **플레인 텍스트 + 후속 칩**. 카드/시트 없음. result 객체 없음.
> Phase 2에 카드/구조화 결과 추가 가능 (스키마 확장).

**Response 200 — REPROMPT (입력 인식 실패)**
```json
{
  "session_id": "sess_abc123",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "예산을 다시 알려주세요." },
    { "type": "bot.quick_replies", "chips": [ /* 동일 칩 재제시 */ ] }
  ]
}
```

**Error 정책**
| error_code | HTTP | FE 처리 |
|------------|------|---------|
| INVALID_SESSION | 400 | 세션 만료 안내 + 새로 시작 |
| NO_CANDIDATES   | 200 (`state="result"`, "조건에 맞는 지역이 없어요" 텍스트) | 텍스트 표시 + 예산 조정 칩 |
| AI_UNAVAILABLE  | 200 (fallback 텍스트) | 분기 없음 |
| INTERNAL_ERROR  | 500 | 토스트 + 재시도 칩 |

### 4.2 BotMessage 타입 (v0 = 2종)

```ts
type BotMessage =
  | { type: "bot.text";          content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };
```

> v0에서는 `bot.text` + `bot.quick_replies` 2개만 사용. v1+에 `bot.cards` 등 추가.

---

## 5. AI 연동 (FE 관점 요약)

> AI 설계 본문은 별도 문서:
> - **FE 관점** → [ai-frontend.md](ai-frontend.md)
> - 서버 구현 (Python FastAPI) → [ai-backend.md](ai-backend.md)

FE가 기억할 핵심:
- **FE는 AI 서버만 호출.** BE는 AI 서버가 내부에서 호출 (FE는 BE URL 모름).
- AI 산출물은 `bot_messages` 안에 이미 텍스트로 가공되어 옴 (`bot.text` 위주).
- AI 실패는 AI 서버가 fallback으로 흡수 → **FE는 분기하지 않음**
- MVP는 LLM 미호출 (양방향 통과 + 텍스트 템플릿).

---

## 6. Frontend 설계

### 6.1 기술 스택

| 항목 | 선택 | 비고 |
|------|------|------|
| 프레임워크 | **React 18 + TypeScript** | |
| 빌드 | **Vite** | 빠른 HMR |
| 라우팅 | (단일 화면이라 불필요) | 추후 결과 공유 URL 필요 시 도입 |
| 상태 | `useState` + `useReducer` (chat) + `@tanstack/react-query` | 단순화 |
| HTTP | fetch wrapper | axios 미도입 |
| 스타일 | **Tailwind CSS** | 디자인보다 동작 우선 |
| 차트 | **Recharts** | v1+에서 카드 인라인 미니 차트용 |
| 아이콘 | **lucide-react** | 가벼움 |

> 지도/Kakao/Recharts 미사용. v0은 텍스트 기반 챗봇만.

### 6.2 폴더 구조

```
frontend/
├── src/
│   ├── App.tsx                       # 풀스크린 챗봇 단일 화면
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatScreen.tsx        # 메인 컨테이너
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx    # bot.text / user.text 렌더
│   │   │   ├── QuickReplyChips.tsx  # bot.quick_replies 렌더
│   │   │   └── ChatInput.tsx        # 자유 입력창 (MVP는 비활성/비표시 가능)
│   │   └── common/
│   │       ├── Loading.tsx
│   │       └── ErrorBoundary.tsx
│   ├── api/
│   │   ├── client.ts                 # fetch wrapper (base URL = AI 서버)
│   │   └── chat.ts                   # POST /chat
│   ├── hooks/
│   │   └── useChat.ts                # 세션 + 메시지 누적
│   ├── lib/
│   │   └── messageRenderer.ts        # bot_messages → 컴포넌트 매핑
│   ├── types/                        # API 응답 타입 (§7)
│   └── styles/
```

> **FE에 정규식/룰베이스 없음**. 모든 의미 처리는 AI 서버.
> **카드/시트 컴포넌트도 v0에 없음** (텍스트 응답만).

### 6.3 챗봇 상태 (FE 단순화)

> AI 서버가 대화를 주도. FE는 thin client.

```
[FE 상태]
  - sessionId: string | null
  - messages: ChatMessage[] (사용자 + 봇 메시지 누적)
  - isWaiting: boolean (요청 진행 중)

[흐름]
  최초 진입 → POST /chat { session_id: null, raw: {} } → 첫 봇 메시지
  사용자 답 → POST /chat { session_id, raw: { ... } }
  응답 도착 → bot_messages를 messages에 append
  사용자가 [다시 추천] → sessionId 초기화, 새 세션
```

> FE에 별도 상태머신 없음. "보내고 받고 누적".

### 6.4 사용자 입력 처리 (v0)

- 칩 클릭: `POST /chat { session_id, raw: { /* 칩에 매핑된 값 */ } }`
- 자유 입력: MVP **비활성** (또는 입력창 미표시). Phase 2 활성화.
- AI 서버가 인식 실패 응답(`state=asking` + 재질문) → FE는 그대로 렌더

### 6.5 화면 구성 (v0)

| 요소 | 카피 / 동작 |
|------|------------|
| 환영 메시지 (자동 도착) | "원하시는 조건에 맞는 집을 찾아드릴게요." + "출퇴근과 예산에 맞는 집을 추천해드릴게요." |
| Q1 자본금 질문 | "먼저 자본금이 어느 정도인지 알려주세요." |
| 자본금 칩 (deal-agnostic) | `[1억 미만=50000000][1–3억=200000000][3–5억=400000000][5억 이상=700000000]` |
| Q2 거래 유형 질문 | "전세/월세 중 어떤 걸 원하시는지 알려주세요." |
| 거래 유형 칩 | `[전세=jeonse][월세=monthly_rent]` (매매 v0 제외) |
| 추천 진행 중 | "잠시만요..." 봇 메시지 또는 typing indicator |
| 결과 메시지 | "{deal_type 한글} {budget_max 한글} 예산에 맞는 지역은 {regions join '·'}입니다." |
| 후속 칩 | `[다시 추천]` |

### 6.6 로딩 / 에러

- 추천 진행 중: "잠시만요..." 봇 메시지 (또는 typing indicator)
- 에러: 봇 메시지로 안내 + `[재시도]` 칩
- AI 실패는 AI 서버가 fallback 흡수 → FE는 분기 없음
- 빈 결과: AI 서버가 "조건에 맞는 지역을 찾지 못했어요. 다시 시도해볼까요?" + `[자본금 다시][다시 추천]` 칩

### 6.7 접근성

- 입력창 라벨 / 칩 button role
- 키보드 only 흐름 가능
- 챗봇 메시지: `aria-live="polite"`
- 색상만으로 정보 전달 금지

---

## 7. 공통 타입 정의 (v0)

```ts
// ─── conditions (MVP v0) ─────────────────────────────────
type DealType = "monthly_rent" | "jeonse";   // v0은 매매 제외
type Conditions = {
  budget_max?: number;     // 정수, 원 단위
  deal_type?: DealType;
};

// ─── FE → AI 서버 요청 ────────────────────────────────────
interface ChatRequest {
  session_id?: string | null;       // 첫 호출엔 null
  raw: Conditions;                  // 이번 턴 입력 (빈 객체 가능)
}

type ChatState = "asking" | "result";

// ─── AI 서버 → FE 응답 ────────────────────────────────────
interface ChatResponse {
  session_id: string;
  state: ChatState;
  bot_messages: BotMessage[];
}

// ─── 봇 메시지 (v0은 2종) ─────────────────────────────────
type BotMessage =
  | { type: "bot.text"; content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };

// ─── FE 내부 메시지 누적용 ─────────────────────────────────
type ChatMessage =
  | { id: string; ts: number; role: "user"; raw: Conditions; chipId?: string }
  | { id: string; ts: number; role: "bot";  body: BotMessage };
```

> AI 서버 ↔ BE 내부 계약은 [ai-backend.md](ai-backend.md) / [backend-mvp.md](backend-mvp.md) 참고.

---

## 8. 마일스톤 (v0)

| 단계 | 산출물 | 검증 |
|------|--------|------|
| **M0. 합의** | 4개 MD sign-off + ERD 갱신 | FE/BE/AI 동의 |
| **M1. FE 부트스트랩** | Vite + React + TS + Tailwind, 풀스크린 챗봇 빈 화면 | localhost 접속 시 환영 메시지 보임 |
| **M2. Mock 기반 FE 단독 구동** | mock `/chat` 응답으로 2질문 wizard + 텍스트 결과 | 자본금 → 거래유형 → 결과 텍스트 흐름 OK |
| **M3. BE 부트스트랩** | DB 마이그레이션 + 단일 chat_messages 테이블 + 내부 API + 점수식 | 단위 테스트 통과 |
| **M4. AI 서버 부트스트랩** | Python FastAPI + `/chat` (FE-facing) + BE 내부 호출 | 단위 테스트 통과 |
| **M5. AI 서버 ↔ BE 통합** | AI 서버에서 BE 호출 → 응답 가공 | `AI_DUMMY_FAIL=true` 시각 확인 |
| **M6. FE ↔ AI 서버 통합** | FE가 실제 AI 서버 호출 | E2E 정상 / 빈 결과 / 에러 |
| **M7. QA & 반응형** | 모바일/데스크톱, 에러 케이스 | 양쪽 정상 |
| **M8. 배포** | docker-compose (FE / AI / BE / DB) | 외부 URL E2E |

> M2는 BE/AI 진척과 무관 → FE 작업의 의존성 차단.
> M3, M4는 병렬 진행 가능.
> v1+ 확장(출퇴근 등)은 별도 마일스톤.

---

## 9. TODO 체크포인트 (v0)

> 마일스톤별 세부 체크. 작업 시작 시 해당 섹션을 활성화하여 사용.

### M0. 합의 / 준비
- [ ] plan.md 시니어 sign-off
- [ ] [backend-mvp.md](backend-mvp.md) 주니어 sign-off
- [ ] [ai-frontend.md](ai-frontend.md) / [ai-backend.md](ai-backend.md) sign-off
- [ ] §4 API 계약 fixture JSON 합의 (mock 데이터)
- [ ] `frontend/` 디렉토리 위치 합의

### M1. FE 부트스트랩
- [ ] `frontend/` 디렉토리 생성
- [ ] Vite + React + TS 프로젝트 초기화
- [ ] Tailwind 설정
- [ ] 기본 폴더 구조 생성 (§6.2)
- [ ] `.env` 템플릿 (`VITE_API_BASE_URL`)
- [ ] `App.tsx` 풀스크린 챗봇 빈 화면 (환영 메시지만)
- [ ] CI 빌드 통과 확인

### M2. Mock 기반 FE 단독 구동 (FE 작업)
- [ ] `useChat` 훅: 세션 + 메시지 누적
- [ ] `ChatScreen` + `MessageList` + `MessageBubble`
- [ ] `QuickReplyChips` 컴포넌트 (자본금/거래 유형)
- [ ] `messageRenderer` (BotMessage → 컴포넌트 매핑)
- [ ] mock `/chat` 응답 fixture (`mocks/chat.v0.json`)
  - [ ] 첫 호출 → 환영 메시지 2줄 + 자본금 질문 + 칩 4개
  - [ ] 자본금 답 → 거래 유형 질문 + 칩 2개
  - [ ] 거래 유형 답 → "잠시만요..." + 결과 텍스트 + `[다시 추천]` 칩
  - [ ] 빈 결과 응답
- [ ] 2질문 wizard 흐름 E2E 수동 확인
- [ ] 자유 입력창은 v0에서 비활성/비표시

### M3. BE 부트스트랩 (BE 작업)
> 체크리스트는 [backend-mvp.md](backend-mvp.md) 참고.

### M4. AI 서버 부트스트랩 (AI 서버 작업)
> 체크리스트는 [ai-backend.md](ai-backend.md) 참고.

### M5. AI 서버 ↔ BE 통합 (AI 서버 작업)
> 체크리스트는 [ai-backend.md](ai-backend.md) / [backend-mvp.md](backend-mvp.md) 참고.

### M6. FE ↔ AI 서버 통합
- [ ] FE `api/client.ts` 작성 (base URL = AI 서버)
- [ ] `api/chat.ts`: `POST /chat` 함수
- [ ] `useChat`을 mock에서 실제 호출로 전환
- [ ] CORS 동작 확인 (AI 서버 책임)
- [ ] E2E 시나리오: 정상 / 빈 결과 / 에러
- [ ] 페이지 로드 시 자동 첫 호출 → 환영 메시지 도착 확인

### M7. QA & 반응형
- [ ] 모바일 (<768px) 풀스크린 챗봇 정상
- [ ] 데스크톱 가운데 컬럼 max-width
- [ ] 빈 결과 안내 메시지 + 칩
- [ ] 에러 메시지 + `[재시도]` 칩
- [ ] aria 속성 / 키보드 흐름 점검
- [ ] 색상 외 정보 전달 점검

### M8. 배포
- [ ] FE 빌드 산출물 호스팅 (Vercel/Netlify 중 결정)
- [ ] 환경변수 주입 (배포 환경)
- [ ] AI 서버 + BE 도커 + DB 배포
- [ ] 도메인 / HTTPS
- [ ] 외부 URL E2E 시나리오 1회

---

## 10. MVP v0 완료 기준

- [ ] 풀스크린 챗봇 화면이 단일 화면으로 동작한다
- [ ] 첫 진입 시 자동으로 환영 메시지 2줄 + 자본금 질문이 도착한다
- [ ] 사용자가 자본금 칩(4개)을 클릭해서 답할 수 있다
- [ ] AI 서버가 거래 유형 질문(전세/월세)을 자동으로 보낸다
- [ ] 거래 유형 칩 클릭 후 "잠시만요..." 표시되고 결과 텍스트가 도착한다
- [ ] 결과 텍스트는 "{거래유형} {예산} 예산에 맞는 지역은 {regions} 입니다." 형식
- [ ] AI 실패 시 fallback 문구가 자연스럽게 표시된다
- [ ] `[다시 추천]` 칩이 새 세션을 시작한다
- [ ] 모바일/데스크톱 양쪽 정상 동작
- [ ] 로딩 / 에러 / 빈 결과 상태가 모두 자연스럽다
- [ ] AI 서버 Provider 교체 한 줄로 실 LLM 전환 가능 (Phase 2)

---

## 11. MVP 제외 (FE)

- 로그인 / 회원가입 / 마이페이지
- 즐겨찾기 / 추천 히스토리
- 결과 URL 공유 (선택)
- 시계열 가격 차트
- 다국어
- 다크모드

> AI 측 제외 항목은 [ai-frontend.md](ai-frontend.md) / [ai-backend.md](ai-backend.md) 참고.

---

## 12. 열린 이슈 (FE)

1. **Frontend 호스팅**: Vercel / Netlify / S3+CloudFront — M9 전까지 결정.
2. **결과 URL 공유**: `recommendation_id` 기반 공유 URL — 차기 마일스톤.
3. **mock fixture 관리**: M2 진입 전 `frontend/src/mocks/chat.v0.json` 작성, 본 문서 §4 예시와 일치.
4. **세션 만료 정책**: BE가 세션 TTL 운영 시 FE의 만료 안내 UX 합의 필요.
5. **v1 진입 시점**: v0 사용성 검증 후 통근 목적지 등 추가 질문 도입 시점.

> AI 관련 이슈는 [ai-backend.md](ai-backend.md) / [ai-frontend.md](ai-frontend.md) 참고.
> BE 측 이슈는 [backend-mvp.md](backend-mvp.md) 참고.
