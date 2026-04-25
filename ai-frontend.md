# AI — Frontend 관점 설계 (MVP v0)

> 본 문서는 **AI를 FE 관점에서 어떻게 다룰지** 정리한다.
> AI 서버 자체 구현은 [ai-backend.md](ai-backend.md), BE는 [backend-mvp.md](backend-mvp.md), 전체 FE 설계는 [plan.md](plan.md).
> **MVP v0: LLM 미호출.** AI 서버는 양방향 통과 + 텍스트 템플릿만 수행.
> Phase 2: 자유 텍스트 의도 추출 + LLM 설명 생성 (Hermes/Qwen/EXAONE 등).

---

## 1. FE 관점 — AI 서버는 무엇인가

- **AI 서버가 FE의 유일한 진입점**. FE는 BE URL을 모른다.
- FE → `POST /chat` → AI 서버 → (내부에서 BE 호출) → AI 서버 → FE
- FE는 응답 `bot_messages[]`만 받아서 그대로 렌더한다. 분기 없음.

```
[FE]  ──POST /chat──▶  [AI 서버]  ──internal──▶  [BE]
[FE]  ◀──bot_messages── [AI 서버]  ◀──conditions/regions── [BE]
```

---

## 2. 응답 메시지 타입 (v0 = 2종)

```ts
type BotMessage =
  | { type: "bot.text";          content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };
```

- v0은 텍스트 + 칩 두 가지만 존재. 카드/요약 박스/주의 글씨 없음.
- v1+에서 `bot.cards`, `bot.summary`, `bot.caution` 추가 가능.

---

## 3. AI가 만드는 메시지 (v0)

### 3.1 환영 (첫 호출 시)
```
bot.text:        "원하시는 조건에 맞는 집을 찾아드릴게요."
bot.text:        "출퇴근과 예산에 맞는 집을 추천해드릴게요."
bot.text:        "먼저 자본금이 어느 정도인지 알려주세요."
bot.quick_replies: [1억 미만][1–3억][3–5억][5억 이상]
```

### 3.2 거래 유형 질문 (자본금 받은 후)
```
bot.text:        "전세/월세 중 어떤 걸 원하시는지 알려주세요."
bot.quick_replies: [전세][월세]
```

### 3.3 결과 (거래 유형 받은 후)
```
bot.text:        "잠시만요..."   (선택)
bot.text:        "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다."
bot.quick_replies: [다시 추천]
```

### 3.4 빈 결과
```
bot.text:        "조건에 맞는 지역을 찾지 못했어요. 자본금을 다시 입력해볼까요?"
bot.quick_replies: [자본금 다시][다시 추천]
```

### 3.5 인식 실패 (방어용)
```
bot.text:        "다시 한번 알려주세요."
bot.quick_replies: [동일 칩 재제시]
```

---

## 4. AI 실패 처리 (FE 무관)

- **FE는 분기하지 않는다.** AI 서버가 항상 200 + 정상 또는 fallback 응답.
- Fallback 응답도 `bot_messages` 형태가 동일하므로 FE는 그대로 렌더.
- 사용자 입장에서 정상/fallback 구분 불가하도록 카피 자연스럽게 설계.

### Fallback 카피 예 (FE에 노출됨)
| 상황 | 카피 |
|------|------|
| AI 서버 내부 오류 | `"죄송해요, 다시 시도해주세요."` + `[다시 추천]` 칩 |
| BE 호출 실패 | `"잠시 문제가 있어요. 다시 추천을 받아볼까요?"` + `[재시도]` 칩 |

> 이 문구는 사용자에게 노출됨. **FE/PM 검토 영역**. 어색하면 AI 서버 코드에서 변경 요청.

---

## 5. MVP에서 FE는 정규식/룰베이스 없음

- 사용자 입력은 **칩 클릭만** (자유 입력 v0 비활성).
- 칩 클릭 시 매핑된 값을 `raw`로 그대로 보냄.
  - 예: `[1–3억]` 클릭 → `raw: { budget_max: 200000000 }`
  - 예: `[전세]` 클릭 → `raw: { deal_type: "jeonse" }`
- AI 서버가 raw + 누적 conditions 머지 (의미 작업).

```ts
// FE 칩 → raw 매핑
const BUDGET_CHIPS = [
  { id: "budget_under_1",   label: "1억 미만",  value: 50000000 },
  { id: "budget_1_3",       label: "1–3억",    value: 200000000 },
  { id: "budget_3_5",       label: "3–5억",    value: 400000000 },
  { id: "budget_5_above",   label: "5억 이상", value: 700000000 },
];

const DEAL_CHIPS = [
  { id: "deal_jeonse",        label: "전세", value: "jeonse" },
  { id: "deal_monthly_rent",  label: "월세", value: "monthly_rent" },
];
```

> 매매(`sale`)는 v0 제외.

---

## 6. Phase 2 변경 사항 미리보기

| 변경 | FE 영향 |
|------|---------|
| 자유 텍스트 입력 | `ChatInput` 컴포넌트 활성화 + `raw_message` 필드 추가 |
| LLM 의도 추출 | **영향 없음** (서버 내부 변경) |
| LLM 설명 생성 | **영향 없음** (응답 스키마 동일) |
| streaming 응답 | `useChat`이 SSE 수신 + 점진 렌더 필요 |
| 카드/구조화 결과 | `BotMessage` union 확장 + 카드 컴포넌트 추가 |

> v0 `useChat`은 메시지 추가형 아키텍처라 streaming 도입을 막지 않음.

---

## 7. FE의 AI 관련 책임

| 책임 | 담당 | 비고 |
|------|------|------|
| AI 응답을 챗봇 메시지로 렌더 | FE | `messageRenderer` |
| 칩 매핑 (chip → value) | FE | 위 6.x 매핑 테이블 |
| Dummy 텍스트 시각 검증 | FE | M6 단계 |
| Fallback 카피 검토 | FE/PM | 어색하면 AI 서버 변경 요청 |
| AI 정상/실패 분기 | ❌ 없음 | AI 서버가 흡수 |
| AI 모델/Provider 선택 | ❌ 없음 | AI 서버 책임 |
| 의도 추출 / 룰베이스 | ❌ 없음 | AI 서버 책임 (Phase 2 LLM) |

---

## 8. FE 체크리스트 — AI 관련 작업

> 다른 FE 작업은 [plan.md §9](plan.md) 참고.

### M2. Mock fixture 준비 (AI 응답 영역)
- [ ] mock `/chat` 응답에 §3 카피 그대로 채우기
- [ ] 환영 메시지 2줄 / Q1 / Q2 / 결과 / 빈 결과 / 에러 케이스
- [ ] mock 응답을 자연스러운 한국어로 작성

### M6. FE ↔ AI 서버 통합
- [ ] 페이지 로드 시 자동 `POST /chat { session_id: null, raw: {} }` 발사
- [ ] 응답 도착 → `bot_messages` 누적 렌더
- [ ] 칩 매핑 테이블 (위 §5) 적용
- [ ] 정상/실패 차이를 사용자가 인지할 수 없는지 확인
- [ ] "잠시만요..." 표시 적절한 타이밍 확인

### M7. QA — AI 관련
- [ ] 모바일에서 `bot.text` 줄바꿈 깨짐 없는지
- [ ] 매우 긴 결과 텍스트 (3줄 이상) 케이스 검증
- [ ] 칩이 많을 때 줄바꿈 처리

### Phase 2 진입 시 (참고)
- [ ] 자유 텍스트 입력창 활성화
- [ ] 응답 streaming 수신 검토
- [ ] `BotMessage` union 확장 (카드 추가 등)

---

## 9. FE의 AI 관련 작업이 아닌 항목

- ❌ AI Provider 선택 / 모델 결정
- ❌ 프롬프트 작성
- ❌ 응답 검증 / Fallback 로직
- ❌ AI 호출 / 환경변수 관리
- ❌ 의도 추출 / 정규식 / 룰베이스
- ❌ AI 비용/한도 모니터링

위는 모두 AI 서버 책임 ([ai-backend.md](ai-backend.md) 참고).
