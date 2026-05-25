# Homefit 구현 리서치

작성일: 2026-05-25

## 1. 분석 범위

현재 `homefit/` 저장소는 이전 리서치 문서 작성 시점보다 크게 리팩터링되어 있다. 본 문서는 현재 파일 기준으로 아래 영역을 다시 확인한 결과다.

- Frontend: React, TypeScript, Vite, Tailwind 채팅 UI
- AI Server: FastAPI, 대화 오케스트레이션, LLM 의미 추출, BE 내부 API 연동
- Backend: Spring Boot, 내부 API, JPA, Flyway, MySQL
- Docker/Makefile: 전체 스택 실행, DB seed import, 검증 명령
- 문서: `README.md`, `docs/api/API.md`, `docs/data/ERD.md`
- 데이터셋: 작업 루트 `files/2015.csv` ~ `files/2024.csv`

주의: IDE 탭에 보이는 `아파트(매매)_실거래가_20260524170217.csv` 파일은 현재 작업 트리에서 찾지 못했다. 실제 존재하는 CSV는 `/Users/ian/Documents/koreadeep/help_j/project/files/*.csv`이며, 이 데이터는 아파트 실거래가가 아니라 거래처/제품/수량/금액 중심의 영업 또는 재고성 데이터다.

## 2. 전체 결론

현재 구현은 더 이상 "프론트 + AI 서버 mock 데모" 수준이 아니다. 실제 구조는 다음 단계까지 올라와 있다.

```text
Frontend -> AI Server -> Backend -> MySQL
```

구현된 핵심 변화:

- `docker-compose.yml`에 `frontend`, `ai-server`, `backend`, `db`, `db-seed`가 모두 포함됐다.
- Backend에 `/internal/upsert-conditions`, `/internal/filter`, `/healthz`가 구현됐다.
- Flyway 마이그레이션으로 `regions`, `housing_transactions`, `chat_messages`, 교통/통근/전세안전 보조 테이블이 만들어진다.
- `deal_type`은 `jeonse`, `monthly_rent`, `sale`까지 확장됐다.
- AI 서버는 OpenAI-compatible/Ollama-compatible LLM provider를 통해 자유 텍스트에서 조건을 추출할 수 있다.
- Frontend는 quick reply 칩을 실제 렌더링하고 클릭을 raw conditions로 매핑한다.
- 매매 CSV 적재용 `scripts/load_sale_transactions.py`가 추가됐다.

다만 현재 완성도는 "전체 통합 구현의 초안"에 가깝다. 바로 정리해야 할 리스크도 있다.

- Backend 테스트 1개가 실패한다. 서울 한정 필터 구현과 경기 지역을 기대하는 테스트가 충돌한다.
- `db-seed`는 seed SQL 파일이 없으면 실패하며, `ai-server`가 `db-seed` 완료를 기다리므로 기본 `docker compose up`이 데이터 파일 유무에 민감하다.
- 작업 루트의 `files/*.csv` 데이터셋은 Homefit 부동산 도메인과 스키마가 맞지 않아 현재 DB seed로 직접 사용할 수 없다.
- AI 서버는 BE에 conditions를 저장하면서도 대화 step은 여전히 in-memory로 들고 있어 재시작/다중 인스턴스에서 대화 단계가 복원되지 않는다.
- 문서 일부(`ERD.md`, `README.md`)는 최신 구현과 어긋난 내용이 남아 있다.

## 3. 현재 아키텍처

### 3.1 런타임 구조

현재 기본 실행 구조:

```text
React FE
  -> POST /chat
FastAPI AI Server
  -> POST /internal/upsert-conditions
  -> POST /internal/filter
Spring Boot Backend
  -> MySQL
```

구성 근거:

- FE API 진입점: `frontend/src/api/chat.ts`
- AI 공개 API: `ai-server/app/main.py`
- AI -> BE client: `ai-server/app/services/backend_client.py`
- BE 내부 API: `backend/src/main/java/com/homefit/internal/api/InternalApiController.java`
- DB schema: `backend/src/main/resources/db/migration/*.sql`
- Compose: `docker-compose.yml`

### 3.2 책임 분리

현재 책임 분리는 비교적 명확하다.

| 영역 | 현재 책임 |
|---|---|
| Frontend | 입력 파싱, raw/raw_message 전송, bot message 렌더, chip click 처리 |
| AI Server | 대화 단계 제어, LLM 의미 추출, workplace -> commute_destination 매핑, BE 호출, 결과 문장 생성 |
| Backend | 조건 이력 저장, DB 기반 지역 필터링, 가격/통근/교통/전세안전 점수 계산 |
| MySQL | 지역/거래/세션 조건/보조 점수 데이터 저장 |

중요한 예외:

- AI 서버가 `_session_state`로 step과 누적 텍스트를 메모리에 보관한다.
- 따라서 DB가 conditions를 저장해도 AI 서버 재시작 후 "현재 몇 번째 질문인지"는 복원되지 않는다.

## 4. Frontend 분석

### 4.1 구현 상태

Frontend는 `ChatScreen` 중심의 단일 채팅 UI다.

주요 구현:

- 첫 진입 시 자동 `/chat` 호출
- 사용자 텍스트 입력
- quick reply 렌더링 및 클릭 처리
- `raw`와 `raw_message`를 함께 전송
- 응답의 `bot_messages`를 순차적으로 출력
- Remote/Mock gateway 전환 구조

이전 리서치에서 "quick reply 타입만 있고 화면에 연결되지 않았다"고 적힌 부분은 더 이상 맞지 않는다. 현재 `MessageBubble.tsx`는 `bot.quick_replies`를 `QuickReplyChips`로 렌더하고, `ChatScreen.tsx`는 `submitChip`을 `MessageList`에 넘긴다.

### 4.2 입력 파싱

`frontend/src/lib/userInputParser.ts` 기준:

- 예산 미입력 상태에서는 숫자, `2억`, `2억5000만`, `5000만` 등을 원 단위 숫자로 변환한다.
- 거래 유형 미입력 상태에서는 `월세`, `전세`, `매매/구매/분양`을 감지한다.
- 필수 조건 이후 텍스트는 `preference_text`와 `raw_message`로 전송한다.

개선된 점:

- `2억 정도` 같은 자연스러운 금액 표현을 일부 처리한다.
- `sale`이 FE 타입과 파서에 들어왔다.
- 이후 단계 자유 텍스트를 LLM 추출 대상으로 보낼 수 있다.

남은 한계:

- 첫 예산 질문에서 예산 quick reply는 서버 카탈로그에 정의되어 있지만 실제 `ask_budget()` 응답에는 포함되지 않는다.
- `commute_destination`은 AI 스키마에는 있지만 FE `Conditions` 타입에는 아직 없다. 현재는 `workplace`/LLM 경로로만 처리된다.
- 월세 상한 입력은 FE에서 구조화하지 않고, 후속 텍스트를 LLM이 추출하는 흐름에 기대고 있다.

### 4.3 UX 평가

현재 UX는 MVP 대화 흐름으로는 충분히 동작한다.

- 예산 -> 거래 유형 -> 통근지 -> 필요 시 월세 상한 -> 결과
- 결과/빈 결과/fallback에 다시 추천, 자본금 다시, 재시도 칩 제공

다만 아직 결과는 텍스트 중심이다. 지역 카드, 비교 테이블, 지도, 조건 수정 UI는 없다.

## 5. AI Server 분석

### 5.1 주요 변화

AI 서버는 단순 상태 머신에서 "대화 오케스트레이터 + 의미 추출기"로 확장됐다.

구현된 요소:

- `Conditions`에 `sale`, `monthly_rent_max`, `workplace`, `commute_destination`, `preference_text` 추가
- `ChatRequest.raw_message` 추가
- `OpenAICompatibleLlmProvider`
- `OllamaNativeLlmProvider`
- `SafeLlmProvider`
- workplace 키워드 기반 업무지구 매핑
- BE HTTP client의 2회 retry와 backend error 변환

### 5.2 대화 정책

`ChatService` 기준 현재 흐름:

1. 첫 호출: 자본금 질문
2. 응답 1회: 거래 유형 질문
3. 응답 2회: 통근 목적지 질문
4. 월세인데 `monthly_rent_max`가 없으면 월세 상한 질문
5. 누적 텍스트가 있으면 LLM을 1회 호출해 조건 추출
6. 필수 조건을 다시 확인한 뒤 BE 필터 호출
7. 결과를 텍스트와 칩으로 반환

좋은 점:

- LLM을 매 턴 호출하지 않고 완료 시점에 1회만 호출한다.
- 구조화 입력과 자유 텍스트를 함께 다룰 수 있다.
- LLM 실패는 빈 conditions로 흡수하는 방어막이 있다.

리스크:

- step 관리가 in-memory라 서버 재시작 시 세션 단계가 손실된다.
- step은 응답 횟수 기반이라, 사용자가 한 문장에 예산/거래유형/직장을 모두 말해도 대화 단계를 압축하지 않는다.
- BE가 conditions를 저장하지만 AI 서버가 최신 conditions를 DB에서 직접 복원하는 구조는 아니다.

## 6. Backend 분석

### 6.1 구현된 API

Backend는 Spring Boot 내부 API를 제공한다.

| API | 역할 |
|---|---|
| `POST /internal/upsert-conditions` | session_id 생성/검증, 최신 conditions 조회, 이번 턴 조건 머지, `chat_messages` 저장 |
| `POST /internal/filter` | 조건 기반 지역 필터링과 점수 계산 |
| `GET /healthz` | public health check |

조건 검증:

- `budget_max`: 양수 정수, 최대 100억 원
- `deal_type`: `jeonse`, `monthly_rent`, `sale`

### 6.2 DB 모델

핵심 테이블:

- `regions`
- `housing_transactions`
- `chat_messages`
- `region_transit`
- `region_commute`
- `region_jeonse_safety`

`housing_transactions`는 V3에서 `sale_price_amount`가 추가되어 매매를 지원한다.

중요한 점:

- V1의 check constraint는 전세/월세만 허용했지만 V3에서 `sale`까지 허용하도록 변경한다.
- `scripts/load_sale_transactions.py`는 매매 CSV를 `deal_type='sale'`, `sale_price_amount`로 적재하도록 되어 있다.

### 6.3 필터링/랭킹

`RegionFilterService`는 다음 기준으로 후보를 만든다.

- 전세: `deposit_amount <= budget_max / 10000`
- 월세: `deposit_amount <= budget_max / 10000` 및 `monthly_rent <= monthly_rent_max / 10000`
- 매매: `sale_price_amount <= budget_max / 10000`

점수:

- 통근 목적지가 없으면 `0.7 * 가격 후보 거래량 점수 + 0.3 * 교통 점수`
- 통근 목적지가 있으면 `0.5 * 가격 후보 거래량 점수 + 0.3 * 통근 점수 + 0.2 * 교통 점수`
- 전세는 `region_jeonse_safety`의 등급도 상세 응답에 포함한다.
- 결과는 최대 5개다.

도메인상 유의할 점:

- 거래량이 많을수록 추천 점수가 올라간다. "저렴한 평균가"가 아니라 "예산 이하 거래가 많이 존재하는 지역" 중심이다.
- 현재 쿼리는 서울특별시로 한정한다.
- `monthly_rent_max`가 없을 때 월세 필터가 전세 쿼리로 fallback되는 로직이 있는데, AI 흐름상 월세 상한을 묻도록 되어 있어 정상 경로에서는 잘 드러나지 않는다.

## 7. Docker/실행 환경 분석

현재 `docker-compose.yml`은 전체 스택을 포함한다.

서비스:

- `frontend`: Vite dev server, `5173`
- `ai-server`: Uvicorn reload, `8000`
- `backend`: Spring Boot, `8080`
- `db`: MySQL 8.4, host port 기본 `3307`
- `db-seed`: seed SQL import one-shot job

Makefile도 전체 스택 중심으로 정리되어 있다.

- `make up`
- `make down`
- `make logs`
- `make docker-frontend-check`
- `make ai-check`
- `make docker-db-pack`
- `make docker-db-import`
- `make docker-db-refresh-from-local`

주의할 점:

- `AI_BACKEND_MODE` 기본값은 `http`다. 예전 README의 "mock backend 모드" 설명은 최신 기본 compose와 다르다.
- `db-seed`는 `db/seed/seed-data.sql.gz` 또는 `db/seed/seed-data.sql`이 없으면 실패한다.
- `ai-server`는 `db-seed`의 `service_completed_successfully`를 기다린다. seed 파일이 없으면 AI 서버까지 올라오지 않을 수 있다.
- 개발 편의성을 위해 "seed 없이 빈 DB로 실행" 모드와 "seed 필수 실행" 모드를 분리하는 편이 좋다.

## 8. 데이터셋 분석

### 8.1 현재 존재하는 CSV

현재 작업 루트에는 아래 CSV가 있다.

| 파일 | 행 수 | 컬럼 수 |
|---|---:|---:|
| `files/2015.csv` | 3,364 | 16 |
| `files/2016.csv` | 4,644 | 18 |
| `files/2017.csv` | 5,023 | 18 |
| `files/2018.csv` | 6,053 | 18 |
| `files/2019.csv` | 6,356 | 18 |
| `files/2020.csv` | 6,849 | 18 |
| `files/2021.csv` | 8,564 | 18 |
| `files/2022.csv` | 10,392 | 18 |
| `files/2023.csv` | 12,381 | 20 |
| `files/2024.csv` | 12,436 | 20 |

총계:

- 총 행 수: 76,062
- 총 수량: 4,926,283
- 총 합계: 116,913,842,705

연도별 합계:

| 연도 | 행 수 | 합계 |
|---|---:|---:|
| 2015 | 3,364 | 4,413,401,610 |
| 2016 | 4,644 | 3,422,002,137 |
| 2017 | 5,023 | 6,984,214,420 |
| 2018 | 6,053 | 8,437,001,008 |
| 2019 | 6,356 | 9,408,482,776 |
| 2020 | 6,849 | 9,714,992,866 |
| 2021 | 8,564 | 14,426,503,162 |
| 2022 | 10,392 | 17,595,343,894 |
| 2023 | 12,381 | 22,432,317,242 |
| 2024 | 12,436 | 20,079,583,590 |

### 8.2 데이터 성격

컬럼은 다음 계열이다.

- `월`, `날짜`
- `구분`, `거래처`
- `제품`, `규격`, `품목`, `사용`, `Type`
- `수량`, `단가`, `합계`, `공급가액`
- `팀`, `담당자`
- `재입고방법`, `출고방법`, `교환,반품 상태`, `최초출고일`, `패널티 적용 금액`, `비고`

상위 제품:

- `STENT`: 33,381행
- `NEURO`: 12,257행
- `FORCEP`: 7,619행
- `SNARE`: 6,261행
- `INJECTOR`: 3,873행

상위 거래처:

- `가온메디칼`: 7,452행
- `바스코`: 6,662행
- `포스메디케어`: 4,369행
- `메디포스`: 4,323행
- `씨에이치메디텍`: 3,966행

### 8.3 Homefit과의 적합성

이 데이터셋은 Homefit의 부동산 추천 DB에 바로 사용할 수 없다.

이유:

- `regions`에 필요한 `sido`, `sigungu_code`, `sigungu`, `legal_dong_code`, `legal_dong_name`이 없다.
- `housing_transactions`에 필요한 `deal_type`, `deposit_amount`, `monthly_rent`, `sale_price_amount`, `contract_date`, `rental_area`가 없다.
- `scripts/load_sale_transactions.py`가 기대하는 국토부 매매 CSV 컬럼과 맞지 않는다.
- 현재 CSV는 의료기기 또는 제품 거래 데이터에 가깝다.

따라서 Homefit 데이터로 쓰려면 아래 중 하나가 필요하다.

1. 국토부 아파트 매매/전월세 실거래 CSV를 실제 작업 트리에 추가한다.
2. 현재 `files/*.csv`는 Homefit과 별도 프로젝트 데이터로 분리한다.
3. 만약 이 데이터가 Homefit 추천과 연결되어야 한다면 도메인 모델 자체를 다시 정의해야 한다.

### 8.4 매매 CSV 적재 스크립트 검토

`scripts/load_sale_transactions.py`는 국토부 아파트 매매 실거래 CSV를 대상으로 한다.

기대 형식:

- cp949 인코딩
- 앞 15줄 메타데이터
- 컬럼 예: `시군구`, `본번`, `부번`, `단지명`, `전용면적(㎡)`, `계약년월`, `계약일`, `거래금액(만원)`, `층`, `건축년도`

적재 방식:

- `시군구`에서 구/동을 분리한다.
- `regions`의 서울특별시 지역과 매칭한다.
- 매칭 실패 시 시군구 단위 fallback을 사용한다.
- `거래금액(만원)`을 `sale_price_amount`에 저장한다.

주의점:

- `regions`가 먼저 seed되어 있어야 한다.
- 현재 스크립트는 서울특별시 region cache만 조회한다.
- 중복 적재 방지 로직이 없다. 같은 CSV를 여러 번 실행하면 중복 row가 들어갈 수 있다.
- `day = min(계약일, 28)`로 처리해 실제 29~31일 계약일이 28일로 축소된다. 날짜 파싱 안정성 목적이라면 문서화가 필요하고, 정확성이 중요하면 실제 월 말일 계산으로 바꾸는 편이 낫다.

## 9. 문서와 구현의 불일치

### 9.1 `docs/data/ERD.md`

현재 ERD 문서는 오래된 내용이 남아 있다.

- `housing_transactions`가 전세/월세만 사용한다고 설명한다.
- `sale_price_amount`가 빠져 있다.
- `regions` 컬럼 설명이 실제 V1 마이그레이션보다 단순하다.
- 현재 구현된 `region_transit`, `region_commute`, `region_jeonse_safety`가 충분히 반영되지 않았다.

### 9.2 `README.md`

README에는 "AI 서버는 mock backend 모드로 `/chat` 응답을 생성"한다고 되어 있지만, 현재 compose 기본값은 `AI_BACKEND_MODE=http`다.

또한 README의 LLM 기본 모델 설명은 `Qwen/Qwen3.5-2B`를 언급하지만, compose 기본값은 `qwen/qwen-2.5-72b-instruct:free`다.

### 9.3 기존 `research.md`

기존 research 내용 중 아래는 더 이상 맞지 않는다.

- backend가 사실상 없다는 설명
- docker-compose에 backend/mysql이 없다는 설명
- quick replies가 실제 화면에 연결되지 않았다는 설명
- 서버가 `sale`을 막고 있다는 설명
- 추천이 mock 규칙 기반이라는 일반화

이제 mock client는 남아 있지만 기본 compose 경로는 실제 Backend HTTP 연동이다.

## 10. 검증 결과

실행한 명령:

```bash
cd /Users/ian/Documents/koreadeep/help_j/project/homefit/backend
./gradlew test
```

결과:

- 7 tests completed
- 1 failed
- 실패 테스트: `InternalApiTests > filterReturnsTopThreeRegionsByTransactionCountWithinBudgetInManwon`

원인 분석:

- `RegionFilterService.findJeonseRegions()` 쿼리는 `ht.region.sido = '서울특별시'`로 서울만 조회한다.
- 실패 테스트는 `분당`, `성남`, `수원`을 `경기도`로 insert하고, 이 3개가 결과로 나오길 기대한다.
- 현재 API 문서도 추천 지역 범위를 서울 내부로 한정한다고 되어 있다.

판단:

- 구현이 맞고 테스트가 오래된 것인지, 아니면 서울 한정을 풀어야 하는지 정책 결정이 필요하다.
- `docs/api/API.md` 기준으로는 테스트를 서울 데이터로 고치는 쪽이 일관적이다.

추가로 Frontend/AI 테스트는 이번 리서치 작성 과정에서 실행하지 않았다.

## 11. 우선순위 제안

### P0. 테스트와 정책 불일치 정리

`InternalApiTests.filterReturnsTopThreeRegionsByTransactionCountWithinBudgetInManwon`을 서울 지역 fixture로 수정하거나, 서울 한정 정책을 철회해야 한다.

현재 문서와 repository query 기준으로는 테스트 수정이 맞다.

### P0. seed 없는 compose 실행 경로 정리

현재 `db-seed`가 seed 파일 부재 시 실패한다. 전체 스택을 처음 실행하는 사용자는 여기서 막힐 가능성이 높다.

권장:

- 기본 `make up`: 빈 DB라도 서비스가 뜨도록 구성
- 별도 `make docker-db-import`: seed 파일 있을 때만 수동 import
- 또는 `db-seed`가 seed 파일 없을 때 성공 종료하도록 정책 변경

### P1. ERD/API/README 최신화

문서에 반드시 반영할 내용:

- `sale_price_amount`
- `deal_type=sale`
- 서울 내부 추천 범위
- 보조 점수 테이블 3종
- AI 서버 기본 backend mode
- LLM provider 기본값
- seed 파일 요구사항

### P1. 대화 상태 영속화 개선

현재 BE는 conditions를 저장하지만 AI 서버 step은 메모리다.

선택지:

- step을 conditions 또는 chat_messages raw에 저장
- AI 서버가 latest conditions만 보고 다음 질문을 결정하도록 step 의존을 줄임
- 자유 텍스트 누적도 DB에 저장해 재시작 후 복원 가능하게 함

### P1. 데이터 적재 파이프라인 보강

매매 CSV 적재는 시작점으로 충분하지만 다음이 필요하다.

- 중복 적재 방지 키
- 서울 region seed와 CSV 법정동 매칭 검증 리포트
- skipped row 사유별 집계
- 실제 29~31일 계약일 보존
- 전월세 데이터 적재 스크립트와 매매 스크립트의 공통화

### P2. 추천 설명 품질 개선

현재 추천은 점수 계산은 BE에서 하지만 사용자에게 보이는 설명은 지역명/통근/안전 등급 중심이다.

추가하면 좋은 정보:

- 예산 이하 거래 수
- 대표 거래 가격 범위
- 통근 목적지 기준 평균 시간
- 교통 점수
- 전세 안전 등급 설명

## 12. 목표 방향: 인프라/인구 기반 아파트 추천

사용자가 원하는 최종 형태는 단순한 "어느 구가 괜찮다"가 아니라 "어느 아파트 단지가 조건에 맞다"에 가깝다.

목표 추천 예시는 다음 형태다.

```text
2억 예산, 매매, 직장 강남, 초등학교 가까운 곳, 유흥시설은 적은 곳, 병원 접근성 좋은 곳
-> 노원구 A아파트 59㎡
-> 강북구 B아파트 84㎡
-> 도봉구 C아파트 59㎡
```

이 목표를 구현하려면 추천 단위를 아래처럼 바꿔야 한다.

```text
현재: regions(sigungu) 추천
목표: apartment_complexes + unit/area band 추천
```

### 12.1 필요한 데이터 축

| 축 | 필요한 데이터 | 용도 |
|---|---|---|
| 아파트 단지 | 단지명, 주소, 좌표, 세대수, 준공연도, 난방, 관리방식, 주차 등 | 추천 대상 master |
| 실거래 | 매매/전월세 거래금액, 계약월, 면적, 층, 건축연도 | 예산 필터와 가격 안정성 |
| 학교 | 초/중/고 위치, 학교급, 운영상태 | 학군/자녀 친화 점수 |
| 병원/약국 | 병원, 의원, 치과, 한의원, 약국 위치와 영업상태 | 의료 접근성 |
| 체육시설 | 헬스장, 체육도장, 골프연습장, 수영장 등 | 생활 편의 점수 |
| 유흥/소음 후보 | 유흥주점, 단란주점, 노래연습장, 게임장, 숙박업 등 | 회피/감점 점수 |
| 인구/연령층 | 행정동 또는 격자 단위 연령대별 인구 | 동네 성향, 가족/청년/고령 친화도 |
| 교통/통근 | 지하철역, 버스, 업무지구별 소요시간 | 출퇴근 점수 |

### 12.2 공식 데이터 후보

현재 기준으로 우선 검토할 공식 데이터 소스는 다음이다.

| 목적 | 후보 데이터 |
|---|---|
| 아파트 단지 master | 공공데이터포털 `국토교통부_공동주택 단지 목록제공 서비스`, `국토교통부_공동주택 기본 정보제공 서비스` |
| 아파트 실거래 | 공공데이터포털 `국토교통부_아파트 매매 실거래가 자료`, 전월세 실거래가 자료 |
| 학교 위치 | 공공데이터포털 `전국초중등학교위치표준데이터`, 필요 시 `전국초등학교통학구역표준데이터` |
| 병원/약국 | 건강보험심사평가원 병의원/약국 현황, 또는 지방행정인허가/표준데이터 약국 데이터 |
| 유흥시설/체육시설 | LOCALDATA 지방행정인허가데이터개방의 유흥주점/단란주점/노래연습장/체육시설 업소정보 |
| 상권/편의시설 보강 | 소상공인시장진흥공단 상가(상권)정보 |
| 연령층/인구 | KOSIS 주민등록인구현황, SGIS 소지역/격자 인구 통계, 서울 한정이면 서울 열린데이터광장 생활인구 |

핵심은 API를 실시간으로 매번 때리는 것이 아니라, 주기적으로 수집해서 내부 DB에 정규화하는 것이다. 추천 요청 시에는 이미 계산된 단지별 feature를 조회해야 응답 시간이 안정된다.

### 12.3 권장 DB 모델

기존 `regions`, `housing_transactions`만으로는 부족하다. 아래 테이블을 추가하는 방향이 적절하다.

```text
apartment_complexes
- id
- kapt_code or external_id
- name
- sido
- sigungu
- legal_dong_name
- road_address
- lat
- lng
- household_count
- built_year
- parking_count
- heating_type
- source

apartment_transactions
- id
- complex_id
- deal_type
- contract_date
- area_m2
- floor_no
- sale_price_amount
- deposit_amount
- monthly_rent
- source

nearby_facilities
- id
- facility_type
- subtype
- name
- road_address
- lat
- lng
- status
- source

complex_feature_scores
- complex_id
- school_count_500m
- elementary_distance_m
- hospital_count_1000m
- pharmacy_count_1000m
- gym_count_1000m
- nightlife_count_500m
- transit_score
- commute_minutes
- youth_ratio
- child_ratio
- senior_ratio
- updated_at
```

운영 관점에서는 `nearby_facilities`를 직접 매번 거리 계산하지 않고, ETL 단계에서 `complex_feature_scores`를 미리 계산하는 편이 낫다.

### 12.4 점수화 방식

단지 추천은 hard filter와 weighted score를 분리해야 한다.

Hard filter:

- 거래 유형: 매매/전세/월세
- 예산 상한
- 최소 면적 또는 면적대
- 서울/경기 등 서비스 범위
- 최근 거래 존재 여부

Weighted score:

| 점수 | 예시 |
|---|---|
| 가격 적합도 | 예산 대비 최근 실거래 중앙값이 낮을수록 가점 |
| 거래 신뢰도 | 최근 12개월 거래 수가 충분하면 가점 |
| 통근 | 사용자의 직장 목적지까지 짧을수록 가점 |
| 학교 | 초등학교 거리/통학구역/중고등학교 수 |
| 의료 | 병원/약국 접근성 |
| 생활 | 체육시설/상권/편의시설 |
| 조용함 | 유흥시설/노래방/숙박업 밀집도 낮을수록 가점 |
| 동네 성향 | 자녀가 있으면 child_ratio, 1인가구/청년이면 youth_ratio 등 선호와 매칭 |

예시 공식:

```text
final_score =
  0.30 * price_score
+ 0.20 * commute_score
+ 0.15 * school_score
+ 0.10 * medical_score
+ 0.10 * lifestyle_score
+ 0.10 * quiet_score
+ 0.05 * demographic_match_score
```

가중치는 사용자 조건에 따라 달라져야 한다.

- "아이 학교가 중요해요" -> school 가중치 상승
- "조용한 동네 원해요" -> nightlife 감점 강화
- "병원 가까운 곳" -> medical 가중치 상승
- "20-30대 많은 동네" -> youth_ratio 가중치 상승

### 12.5 AI 서버 역할 변경

AI 서버는 추천 점수를 직접 계산하지 않는 편이 좋다.

AI 서버가 해야 할 일:

- 사용자 자연어에서 선호 조건 추출
- `preference_weights` 생성
- 결과를 사람이 이해하기 좋은 문장으로 설명

Backend가 해야 할 일:

- 단지/거래/시설/인구 데이터를 조회
- hard filter 적용
- weighted score 계산
- 추천 후보와 점수 근거 반환

추가할 conditions 예시:

```json
{
  "budget_max": 700000000,
  "deal_type": "sale",
  "workplace": "강남",
  "commute_destination": "gangnam",
  "school_importance": "high",
  "avoid_nightlife": true,
  "medical_importance": "medium",
  "gym_importance": "medium",
  "preferred_age_group": "30_40_family",
  "min_area_m2": 59
}
```

### 12.6 MVP로 자르는 방법

한 번에 모든 데이터를 붙이면 범위가 너무 크다. 추천 순서는 아래가 현실적이다.

1. `apartment_complexes`와 매매 실거래를 먼저 연결한다.
2. 추천 결과를 `구`가 아니라 `아파트 단지명 + 면적대 + 최근 거래가`로 바꾼다.
3. 학교/병원/유흥시설 3개만 먼저 거리 기반 feature로 추가한다.
4. 그 다음 체육시설, 상권, 연령층을 붙인다.
5. 마지막에 사용자별 가중치 조정과 설명 품질을 개선한다.

최소 MVP 결과 응답:

```json
{
  "apartments": [
    {
      "complex_name": "상계주공...",
      "sigungu": "노원구",
      "legal_dong": "상계동",
      "area_m2": 59.4,
      "recent_median_price": 620000000,
      "score": 82.5,
      "reasons": [
        "예산 7억 이하 최근 거래가 있습니다.",
        "초등학교가 400m 이내입니다.",
        "반경 500m 유흥시설 밀도가 낮습니다.",
        "강남 업무지구 통근 점수가 양호합니다."
      ]
    }
  ]
}
```

## 13. 현재 상태 한 줄 평가

Homefit은 이제 FE-AI-BE-DB가 실제로 연결되는 통합 MVP 초안까지 왔다. 다음 병목은 기능 부재가 아니라 정책/테스트/데이터/문서의 정합성이다. 특히 서울 한정 정책, seed 실행 방식, 실제 국토부 데이터 파일 확보를 먼저 정리해야 이후 추천 품질 개선이 의미 있게 진행된다.
