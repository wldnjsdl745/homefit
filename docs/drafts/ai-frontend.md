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

## 2. 응답 메시지 타입 (v0 = 텍스트 중심)

```ts
type BotMessage =
  | { type: "bot.text";          content: string }
  | { type: "bot.quick_replies"; chips: { id: string; label: string }[] };
```

- v0 스키마는 텍스트 + 칩 두 가지를 허용한다.
- 현재 구현은 사용자가 채팅 입력으로 답하는 UX이므로 `bot.text`만 렌더 흐름에 사용한다.
- 카드/요약 박스/주의 글씨 없음.
- v1+에서 `bot.cards`, `bot.summary`, `bot.caution` 추가 가능.

---

## 3. AI가 만드는 메시지 (v0)

### 3.1 환영 (첫 호출 시)
```
bot.text:        "먼저 자본금이 어느 정도인지 알려주세요."
```

### 3.2 거래 유형 질문 (자본금 받은 후)
```
bot.text:        "전세/월세 중 어떤 걸 원하시는지 알려주세요."
```

### 3.3 결과 (거래 유형 받은 후)
```
bot.text:        "잠시만요..."   (선택)
bot.text:        "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다."
```

### 3.4 빈 결과
```
bot.text:        "조건에 맞는 지역을 찾지 못했어요. 새 대화로 다시 입력해볼까요?"
```

### 3.5 인식 실패 (방어용)
```
bot.text:        "다시 알려주세요."
```

---

## 4. AI 실패 처리 (FE 무관)

- **FE는 분기하지 않는다.** AI 서버가 항상 200 + 정상 또는 fallback 응답.
- Fallback 응답도 `bot_messages` 형태가 동일하므로 FE는 그대로 렌더.
- 사용자 입장에서 정상/fallback 구분 불가하도록 카피 자연스럽게 설계.

### Fallback 카피 예 (FE에 노출됨)
| 상황 | 카피 |
|------|------|
| AI 서버 내부 오류 | `"잠시 문제가 있어요. 다시 입력해주세요."` |
| BE 호출 실패 | `"잠시 문제가 있어요. 다시 입력해주세요."` |

> 이 문구는 사용자에게 노출됨. **FE/PM 검토 영역**. 어색하면 AI 서버 코드에서 변경 요청.

---

## 5. MVP에서 FE 입력 처리

- 사용자 입력은 채팅 입력창으로 받는다.
- FE는 현재 대화 단계에 맞춰 명확히 알 수 있는 값만 구조화된 `raw`로 보내고, 원문은 `raw_message`로 함께 보낸다.
  - 예: `200000000` 입력 → `raw: { budget_max: 200000000 }`
  - 예: `전세` 입력 → `raw: { deal_type: "jeonse" }`
- 예산/거래유형을 문장으로 입력한 경우 → `raw: {}`, `raw_message: "2억 정도 있어요"` 형태로 AI 서버 의미 추출에 맡긴다.
- 예산/거래유형 이후 추가 희망사항은 `raw: { preference_text: "..." }`, `raw_message: "..."`로 보낸다.
- AI 서버가 raw + 의미 추출 결과 + 누적 conditions 머지.

```ts
// FE 입력 → raw 매핑
"200000000" → { budget_max: 200000000 }
"전세"      → { deal_type: "jeonse" }
"월세"      → { deal_type: "monthly_rent" }
```

> 매매(`sale`)는 v0 제외.

---

## 6. Phase 2 변경 사항 미리보기

| 변경 | FE 영향 |
|------|---------|
| 자유 텍스트 입력 | `raw_message` 필드 추가 |
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
| 입력 매핑 (text → raw) | FE | `UserInputParser` |
| Dummy 텍스트 시각 검증 | FE | M6 단계 |
| Fallback 카피 검토 | FE/PM | 어색하면 AI 서버 변경 요청 |
| AI 정상/실패 분기 | ❌ 없음 | AI 서버가 흡수 |
| AI 모델/Provider 선택 | ❌ 없음 | AI 서버 책임 |
| 의도 추출 / 룰베이스 | ❌ 없음 | AI 서버 책임 (Phase 2 LLM) |

---

## 8. FE 체크리스트 — AI 관련 작업

> 다른 FE 작업은 [plan.md §9](plan.md) 참고.

### M2. Mock fixture 준비 (AI 응답 영역)
- [x] mock `/chat` 응답에 §3 카피 채우기
- [x] Q1 / Q2 / 결과 / 빈 결과 / 에러 케이스
- [x] mock 응답을 자연스러운 한국어로 작성

### M6. FE ↔ AI 서버 통합
- [x] 페이지 로드 시 자동 `POST /chat { session_id: null, raw: {} }` 발사
- [x] 응답 도착 → `bot_messages` 누적 렌더
- [x] 텍스트 입력 매핑 (`UserInputParser`) 적용
- [x] 정상/실패 차이를 사용자가 인지할 수 없는지 확인
- [x] "잠시만요..." 표시 적절한 타이밍 확인

### M7. QA — AI 관련
- [x] 모바일에서 `bot.text` 줄바꿈 깨짐 없는지
- [ ] 매우 긴 결과 텍스트 (3줄 이상) 케이스 검증
- [x] 칩 미사용 UX로 정리

### Phase 2 진입 시 (참고)
- [x] 채팅 입력창 활성화
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
