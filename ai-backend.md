# AI 서버 — 구현 체크리스트 (MVP v0)

> AI 서버는 **FE의 진입점**이자 BE를 내부 호출하는 오케스트레이터.
> FE 측 관점은 [ai-frontend.md](ai-frontend.md), BE 내부 API는 [backend-mvp.md](backend-mvp.md), 전체 설계는 [plan.md](plan.md).
> **MVP v0: LLM 미호출.** 양방향 통과 + 텍스트 템플릿.
> Phase 2: 자유 텍스트 의도 추출 + LLM 설명 생성 (Hermes / Qwen / EXAONE 등).

---

## 위치

```
homefit/
├── frontend/
├── backend/      (Spring Boot)
└── ai-server/    ← 본 문서 대상 (FastAPI)
```

---

## 책임

- **FE-facing 진입점**: `POST /chat`
- 양방향 통과 (raw 검증 + BE 호출 + 응답 가공)
- conditions 머지 (raw 키를 직전 conditions 위에 덮어쓰기)
- 결과 텍스트 템플릿 가공 (regions → 한국어 문장)
- fallback 흡수 (BE 실패 시 정상 응답 형태로 변환)
- Phase 2: LLM 의도 추출 (`raw_message` 파싱) + LLM 설명 생성

**원칙**
- AI는 추천 순위를 바꾸지 않는다 (BE의 regions 순서 그대로 사용).
- AI는 입력에 없는 사실을 만들지 않는다.
- AI 서버는 stateless. 세션/이력은 BE만 보유.

---

## 기술 스택

- **Python 3.11+**
- **FastAPI** (OpenAPI 자동 + Pydantic 검증)
- **Pydantic v2**
- **Uvicorn** (ASGI)
- **httpx** (BE 호출)
- **pytest**

> Phase 2 모델 도입 시 추가: `transformers`, `vllm`, `ollama`, `anthropic`, `openai`.

---

## 구현 체크리스트

### A0. 부트스트랩
- [x] `ai-server/` 디렉토리 생성
- [x] `pyproject.toml` 또는 `requirements.txt`
- [x] `app/main.py` FastAPI 앱
- [x] Dockerfile
- [x] `.env.example`

### A1. 입출력 스키마 (Pydantic)
- [x] `ChatRequest` (`session_id`, `raw`)
- [x] `ChatResponse` (`session_id`, `state`, `bot_messages`)
- [x] `BotMessage` 유니온 (text / quick_replies)
- [x] `Conditions` (`budget_max`, `deal_type`)

### A2. CORS
- [x] FE 도메인 허용 (개발: `http://localhost:5173`)
- [ ] 운영 도메인 추가는 배포 시점

### A3. `POST /chat` 엔드포인트 (FE-facing)
- [x] 첫 호출 (session_id=null) → 새 세션 → 자본금 질문
- [x] 자본금 받음 → 거래 유형 질문
- [x] 거래 유형 받음 → BE 호출 → 결과 텍스트
- [x] 예산 + 거래 유형을 한 요청으로 받아 결과 텍스트 반환
- [x] 인식 실패 → 재질문
- [x] BE 호출 실패 → fallback 응답

### A4. raw 머지 로직 (`MergeService`)
- [x] raw 키를 직전 conditions 위에 덮어쓰기
- [x] **MVP 동작**: 단순 dict merge
- [ ] **Phase 2 확장**: `raw_message` 추가 시 LLM이 텍스트 → raw 추출 후 동일 머지
- [x] 단위 테스트

### A5. raw 검증 가드
- [x] `budget_max`: 양수 정수, 상한 (예: 100억) 체크
- [x] `deal_type`: enum 외 거부 (`jeonse` / `monthly_rent`만 허용. `sale`은 v0 거부)
- [x] 위반 시 `bot.text("다시 알려주세요")`

### A6. BE 호출 (`BackendClient`)
- [x] httpx async 클라이언트
- [x] 환경변수 `BACKEND_URL` (예: `http://backend:8080`)
- [x] `POST /internal/upsert-conditions` (session 조회/생성 + 메시지 저장 + 머지된 conditions 저장)
- [x] `POST /internal/filter` (conditions → regions 리스트, 미저장)
- [x] 타임아웃 5초 / 재시도 1회
- [x] 실패 시 fallback 응답 반환
- [x] BE 미구현 상태를 위한 mock backend 모드

### A7. 다음 질문 결정 로직 (`DialogPolicy`)
- [x] conditions 충족 여부 판정
  - [x] `budget_max` 없음 → 자본금 질문
  - [x] `deal_type` 없음 → 거래 유형 질문
  - [x] 둘 다 있음 → BE 필터링 → 결과
- [x] 질문 순서: **자본금 → 거래 유형** 고정
- [x] 단위 테스트

### A8. 봇 메시지 빌더 (`MessageBuilder`)
- [x] 자본금 질문 메시지
- [x] Q2 메시지 (거래 유형 질문)
- [x] 결과 메시지 (텍스트 템플릿)
- [x] 빈 결과 메시지
- [x] 인식 실패 메시지
- [x] Fallback 메시지

### A9. 결과 텍스트 템플릿 (`ResultFormatter`)
- [x] 템플릿: `"{deal_type 한글} {budget_max 한글} 예산에 맞는 지역은 {regions join '·'}입니다."`
- [x] `deal_type` 매핑: `jeonse` → "전세", `monthly_rent` → "월세"
- [x] `budget_max` 매핑:
  - [x] 0–9999만 → "{n}만원"
  - [x] 1억+ → "{n.n}억"
- [x] regions가 비어있으면 빈 결과 메시지 사용
- [ ] **Phase 2**: LLM이 자연스럽게 풀어 씀 + 추천 이유 추가

### A10. Fallback 정책
- [x] BE 호출 실패 → fallback 텍스트
- [x] 환경변수 `AI_DUMMY_FAIL=true` → 의도적 fallback (QA용)
- [ ] **Phase 2 LLM 도입 시**: LLM 응답 검증 5단계 추가
  - [ ] JSON 파싱
  - [ ] 스키마 검증
  - [ ] region_id 일치
  - [ ] 순위 강제 정렬
  - [ ] 금칙어 가드

### A11. `GET /healthz`
- [x] 단순 200 OK

### A12. 로깅
- [ ] 요청/응답 시간
- [ ] BE 호출 결과
- [ ] 개인정보 미포함 (raw 단순 dict 정도는 OK)

### A13. 단위 테스트 (pytest)
- [x] 첫 호출 → 자본금 질문
- [x] 자본금만 받음 → 거래 유형 질문
- [x] 둘 다 받음 → BE 호출 → 결과 텍스트
- [x] 잘못된 raw → 재질문
- [x] BE 실패 → fallback
- [x] `AI_DUMMY_FAIL=true` → fallback

### A14. Docker
- [x] Dockerfile (Python 3.11 slim + FastAPI)
- [x] docker-compose에 `ai-server` 서비스 추가
- [x] BE와 같은 네트워크

---

## API 계약

### `POST /chat` (FE → AI 서버)

**Request**
```json
{
  "session_id": "uuid | null",
  "raw": { "budget_max": 200000000 }
}
```

**Response — asking (다음 질문 필요)**
```json
{
  "session_id": "uuid",
  "state": "asking",
  "bot_messages": [
    { "type": "bot.text", "content": "전세/월세 중 어떤 걸 원하시는지 알려주세요." }
  ]
}
```

**Response — result (충족, 추천 완료)**
```json
{
  "session_id": "uuid",
  "state": "result",
  "bot_messages": [
    { "type": "bot.text", "content": "잠시만요..." },
    { "type": "bot.text", "content": "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다." }
  ]
}
```

### 내부 호출: BE → 단일 진실은 [backend-mvp.md](backend-mvp.md)

```
POST /internal/upsert-conditions
{ session_id, raw, conditions }
→ { session_id, conditions }   // 머지된 누적 conditions

POST /internal/filter
{ conditions }
→ { regions: ["분당", "성남", "경기도"] }
```

---

## 환경변수

| 키 | 값 | 의미 |
|----|---|------|
| `BACKEND_URL` | `http://backend:8080` | BE 내부 API base URL |
| `AI_BACKEND_MODE` | `mock` (default) / `http` | BE 미구현 시 mock backend 사용 |
| `AI_PROVIDER` | `dummy` (MVP) / `claude` / `local` (Phase 2) | LLM Provider |
| `AI_DUMMY_FAIL` | `false` (default) / `true` | 강제 실패 (QA) |
| `AI_TIMEOUT_MS` | `5000` | BE 호출 타임아웃 |
| `AI_PORT` | `8000` | 서비스 포트 |
| `CORS_ALLOW_ORIGINS` | `http://localhost:5173` | FE 도메인 |

---

## 정책 요약

- AI 서버 = stateless 오케스트레이터.
- 세션/이력 = BE DB. AI는 매 호출마다 BE에서 conditions 받아옴.
- LLM 미호출 (MVP). Provider 추상화는 그대로 유지 → Phase 2에 한 줄 교체.

---

## Phase 2 진입 가이드

> 본 섹션은 MVP 출시 후 활성화.

### 진입 트리거 (1주 안에 합의)
- [ ] (a) MVP 출시 후 N주 (예: 8주)
- [ ] (b) 사용자 피드백 시그널 누적
- [ ] (c) 시니어가 한계 합의

### 모델 후보 (1주 안에 합의)
- [ ] EXAONE 3.5 2.4B (한국어 특화) — 1순위
- [ ] Qwen 2.5 3B — 2순위
- [ ] Kanana Nano 2.1B — 3순위
- [ ] Hermes 3 Llama 3.2 3B — 후순위
- [ ] Claude Sonnet/Haiku 4.x (외부 API)

### 외부 API 허용 여부
- [ ] (a) 로컬만 / (b) 외부 OK / (c) 비용 합의 후

### 개인정보 정책
- [ ] 사용자 입력 = 비식별
- [ ] 로그에 PII 미포함

### Phase 2 진입 시 결정
- [ ] 최종 모델 선정
- [ ] 평가 메트릭
- [ ] 호스팅 (로컬 GPU / AWS GPU / Ollama / vLLM / API)
- [ ] 응답 시간 SLA
- [ ] 비용 한도
- [ ] 장애 fallback (LLM 실패 → MVP 텍스트 템플릿으로 회귀)
- [ ] 롤아웃 (일괄 / A/B / 셰도우)

### Phase 2 구현 체크리스트
- [ ] `LlmExtractor`: `raw_message` → `raw` 추출
- [ ] `LlmExplainer`: regions + conditions → 자연스러운 한국어 설명
- [ ] System prompt 작성 (순위 변경 금지 / 입력 외 사실 금지 / 부동산 조언 금지 등)
- [ ] structured output / JSON 모드 강제
- [ ] prompt caching (외부 API)
- [ ] 호스팅 인프라 (Ollama / vLLM 컨테이너)
- [ ] 비용/응답시간 모니터링
- [ ] 셰도우 모드 1주
- [ ] 환경변수 `AI_PROVIDER` 전환

### Phase 2 추가 엔드포인트 (선택)
- [ ] `POST /chat`은 그대로 유지 (FE 인터페이스 변경 없음)
- [ ] 내부 모듈로 `LlmExtractor` / `LlmExplainer` 추가
