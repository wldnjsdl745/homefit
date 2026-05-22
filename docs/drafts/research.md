# Homefit 구현 리서치

작성일: 2026-04-25

## 1. 리서치 범위

본 문서는 아래 기획 문서를 기준으로 현재 저장소 구현 상태를 대조한 결과다.

- `plan.md`
- `backend-mvp.md`
- `ai-backend.md`
- `ai-frontend.md`

확인 대상은 다음 네 영역이다.

- 프론트엔드 실제 구현
- AI 서버 실제 구현
- Docker 구성과 실행 방식
- 백엔드 구현 여부와 기획 대비 차이

추가로 테스트와 빌드 검증 결과도 포함했다.

---

## 2. 전체 결론

현재 저장소는 "프론트엔드 + AI 서버 + Docker 개발 환경" 기준으로는 MVP v0 데모가 동작하는 상태다.

실제로 구현된 핵심 범위는 다음과 같다.

- 프론트는 풀스크린 채팅 UI 형태로 동작한다.
- 페이지 진입 시 자동으로 첫 질문을 요청한다.
- 사용자가 숫자를 입력하면 예산으로 해석한다.
- 사용자가 `전세` 또는 `월세`를 입력하면 거래 유형으로 해석한다.
- AI 서버는 `/chat` 단일 진입점으로 동작한다.
- AI 서버는 예산/거래유형 수집 상태를 판단하고 다음 질문 또는 결과 문장을 반환한다.
- Docker로 프론트와 AI 서버를 함께 띄울 수 있다.
- 프론트 lint/test/build, AI 서버 lint/test가 모두 통과한다.

반면, 기획 문서 기준으로 아직 미구현인 핵심 범위도 명확하다.

- Spring Boot 백엔드 내부 API는 사실상 아직 없다.
- MySQL, Flyway, Entity, Repository, 필터링 API, 시드 데이터 적재가 없다.
- 현재 AI 서버의 결과 추천은 실제 백엔드 조회가 아니라 mock backend 규칙 기반이다.
- 기획에 있던 quick reply 칩 중심 UX는 타입과 컴포넌트만 있고 실제 화면 흐름에는 연결되지 않았다.

즉, 지금 구현물은 "완전한 추천 시스템"이라기보다 "기획된 대화 흐름을 프론트와 AI 서버 중심으로 재현한 MVP 데모"로 보는 것이 정확하다.

---

## 3. 아키텍처 구현 상태

기획 의도는 다음 구조였다.

- FE -> AI 서버 -> BE -> DB

현재 실제 구조는 다음에 가깝다.

- FE -> AI 서버 -> MockBackendClient 메모리 세션/더미 추천

근거:

- 프론트는 `frontend/src/api/chat.ts`에서 `/chat`만 호출한다.
- AI 서버는 `ai-server/app/main.py`에서 FE-facing `/chat`과 `/healthz`만 제공한다.
- AI 서버는 `ai-server/app/config.py`의 `AI_BACKEND_MODE`로 `mock` 또는 `http`를 선택한다.
- `docker-compose.yml`에서는 `AI_BACKEND_MODE` 기본값이 `mock`이다.
- 실제 backend 디렉터리에는 `BackendApplication.java`만 있고 컨트롤러, 엔티티, 리포지토리, 내부 API 구현이 없다.

정리하면 "FE가 BE를 직접 호출하지 않는다"는 아키텍처 원칙은 지켜졌지만, "AI 서버가 실제 Spring Boot 백엔드를 오케스트레이션한다"는 단계까지는 아직 도달하지 못했다.

---

## 4. 프론트엔드 상세 분석

### 4.1 UI 구조

프론트는 `frontend/src/components/chat/ChatScreen.tsx` 중심의 단일 채팅 화면으로 구성되어 있다.

구현된 특징:

- 전체 높이를 쓰는 풀스크린 레이아웃
- 상단 헤더에 `HOMEFIT` 로고
- 큰 타이틀 영역과 채팅 패널 분리
- 채팅 상태 표시: `Thinking` / `Ready`
- 메시지 리스트 + 하단 입력창 구조

기획 문서의 "풀스크린 챗봇" 방향성과는 대체로 일치한다.

차이점:

- 기획 문서에 있던 `새 대화` 버튼은 없다.
- 비교 보기, 카드 UI, 모달/슬라이드업, 지역 카드 등은 없다.
- 실제 UI 문구는 한국어 대화이지만 헤더와 입력 placeholder 일부는 영어다.

### 4.2 상태 관리와 대화 흐름

핵심 상태 로직은 `frontend/src/hooks/useChat.ts`에 있다.

구현된 상태 값:

- `sessionId`
- `messages`
- `status`
- `lastRaw`
- `conditions`

구현된 동작:

- 첫 렌더 후 자동 `start()` 호출
- 첫 호출은 빈 raw `{}` 로 전송
- 요청 중에는 중복 전송 차단
- 사용자 입력은 로컬 조건 상태와 합쳐 추적
- 응답 `bot_messages`는 순차적으로 화면에 추가
- 에러 시 fallback 메시지를 채팅에 추가

세부 기능:

- `useEffect`로 최초 1회 자동 부트스트랩
- `BotMessageSequencer`로 다중 봇 메시지를 420ms 간격으로 순차 표시
- `session_id`는 서버 응답에서 받아 다음 요청에 재사용
- 마지막 전송 raw를 `retry` 용도로 저장

주의점:

- `restart`, `retry`, `hasError`는 훅에서 제공되지만 현재 `ChatScreen`에서 실제 사용되지 않는다.
- `ChatMessageFactory.botMessages()`도 현재 사용되지 않는다.

### 4.3 사용자 입력 파싱

`frontend/src/lib/userInputParser.ts` 기준으로 현재 입력 해석 방식은 매우 단순하다.

실제 규칙:

- 아직 예산이 없으면 숫자만 입력 가능
- 예산이 있고 거래 유형이 없으면 `전세` 또는 `월세`만 허용
- 둘 다 있으면 다시 숫자를 예산으로 덮어씀

의미:

- 현재 프론트는 "대화형 자유 입력"이 아니라 "현재 단계에 맞는 제한 입력" 방식이다.
- 기획 문서의 MVP v0 가정과는 맞지만, 자연어 입력이나 문장형 입력은 지원하지 않는다.

제약:

- `2억`, `20000만원`, `2억 정도`, `월세 원해요` 같은 입력은 실패한다.
- 숫자 외 문자는 예산으로 인정되지 않는다.
- `sale`은 프론트 타입 레벨에서도 없다.

### 4.4 메시지 렌더링

현재 실제 화면 렌더는 `bot.text` 중심이다.

구성:

- `MessageList.tsx`: 메시지 목록 + 자동 스크롤 + 대기 인디케이터
- `MessageBubble.tsx`: 사용자/봇 말풍선 렌더
- `ChatInput.tsx`: 입력과 전송 버튼

세부 특징:

- 대기 중에는 `생각 중` 인디케이터를 보여준다.
- 봇/사용자 아바타는 단순 `AI` / `ME` 텍스트 박스다.
- 사용자 메시지는 오른쪽, 봇 메시지는 왼쪽 정렬이다.

중요한 구현 한계:

- `bot.quick_replies` 타입은 존재하지만 현재 말풍선 렌더에서 사실상 무시된다.
- `MessageBubble.tsx`는 `bot.text`가 아니면 빈 문자열로 처리하고 렌더하지 않는다.
- `QuickReplyChips.tsx` 컴포넌트는 존재하지만 `ChatScreen`에 연결되어 있지 않다.

따라서 문서 스키마상 quick reply를 지원하는 것처럼 보이지만, 실제 사용자 경험은 "텍스트 입력 전용 채팅"이다.

### 4.5 Mock/Remote 전환 구조

`frontend/src/api/chat.ts` 기준으로 프론트는 두 가지 채팅 게이트웨이를 가진다.

- `RemoteChatGateway`: 실제 AI 서버 `/chat` 호출
- `MockChatGateway`: 프론트 내부 mock 서버 사용

환경 변수:

- `VITE_USE_MOCK_CHAT !== "false"` 이면 mock 사용
- 아니면 `VITE_API_BASE_URL` 기반 원격 호출

현재 `docker-compose.yml` 기본값은 `VITE_USE_MOCK_CHAT=false` 이므로 Docker 실행 시에는 AI 서버를 실제로 호출한다.

### 4.6 프론트 UX 완성도 평가

잘 된 점:

- 채팅 흐름이 단순하고 사용법이 명확하다.
- 자동 시작, 순차 메시지 출력, 로딩 표시가 있어 데모 완성도가 있다.
- 테스트로 핵심 대화 흐름이 고정되어 있다.

아쉬운 점:

- 기획 문서에 언급된 칩 중심 입력 UX와 실제 구현이 다르다.
- 에러 후 재시도 UX가 화면에 노출되지 않는다.
- 장문의 답변, 카드형 결과, 비교 UI는 없다.
- 현재 예산 입력 경험이 너무 엄격하다.

---

## 5. AI 서버 상세 분석

### 5.1 엔드포인트와 역할

AI 서버는 `ai-server/app/main.py`에서 FastAPI 앱으로 구현되어 있다.

구현된 엔드포인트:

- `GET /healthz`
- `POST /chat`

추가 동작:

- CORS 허용
- Pydantic 요청 검증
- 요청 검증 실패 시 422가 아니라 200 + `"다시 알려주세요."` fallback 응답 반환

이 구조는 "FE는 실패 분기 없이 `bot_messages`만 렌더한다"는 기획 방향과 잘 맞는다.

### 5.2 스키마 설계

`ai-server/app/schemas.py` 기준으로 다음 스키마가 구현되어 있다.

- `Conditions`
- `ChatRequest`
- `ChatResponse`
- `BotTextMessage`
- `BotQuickRepliesMessage`
- `UpsertConditionsRequest/Response`
- `FilterRegionsRequest/Response`

유효성 제약:

- `budget_max`: 양수, 최대 100억
- `deal_type`: `jeonse` 또는 `monthly_rent`

의미:

- 서버 레벨에서 `sale`을 막고 있다.
- 프론트 파싱을 우회하는 잘못된 입력도 서버에서 한 번 더 방어한다.

### 5.3 대화 정책

`ai-server/app/services/dialog_policy.py`는 매우 단순한 상태 머신이다.

규칙:

- `budget_max` 없으면 예산 질문
- `deal_type` 없으면 거래 유형 질문
- 둘 다 있으면 결과 단계

장점:

- MVP v0 목적에는 충분하다.
- 예측 가능하고 테스트하기 쉽다.

한계:

- 질문 순서가 고정이다.
- 추가 슬롯이 생기면 정책 확장이 필요하다.
- 자유 텍스트 의도 추출은 아직 없다.

### 5.4 조건 머지와 세션 흐름

`ChatService`는 요청을 받으면 먼저 backend client에 `upsert_conditions`를 호출한다.

현재 흐름:

1. FE가 `session_id`와 `raw` 전송
2. AI 서버가 backend client에 upsert 요청
3. backend client가 누적 conditions를 반환
4. AI 서버가 다음 질문 또는 결과를 결정
5. 필요 시 `filter_regions` 호출

현재 mock backend 기준 세션 저장 방식:

- 메모리 딕셔너리 사용
- `session_id` 없으면 UUID 생성
- 이전 조건 + 새 raw를 merge

중요한 점:

- 이 "세션 누적"은 현재 Spring Boot 백엔드가 아니라 `MockBackendClient` 내부에서 처리된다.
- 따라서 서버 재시작 시 세션이 유지되지 않는다.
- 여러 인스턴스 환경도 고려되지 않았다.

### 5.5 결과 생성 방식

`ai-server/app/services/message_builder.py`와 `result_formatter.py` 기준으로 결과는 템플릿 문자열이다.

구현된 메시지:

- 첫 질문: 자본금 질문
- 두 번째 질문: 거래 유형 질문
- 결과 전 안내: `잠시만요...`
- 결과 본문: 거래 유형 + 예산 + 지역 목록
- 빈 결과 문구
- fallback 문구

예산 포맷:

- 1억 이상은 `2억`, `3.5억` 같은 형식
- 그 미만은 `6000만원` 형식

이 부분은 기획 문서의 v0 템플릿 요구와 잘 맞는다.

### 5.6 backend client 구성

`ai-server/app/services/backend_client.py`에는 두 가지 구현체가 있다.

- `HttpBackendClient`
- `MockBackendClient`

`HttpBackendClient` 기능:

- `/internal/upsert-conditions` POST
- `/internal/filter` POST
- timeout 적용
- 최대 2회 재시도

`MockBackendClient` 기능:

- 메모리 세션 저장
- 조건 merge
- 예산과 거래 유형에 따라 하드코딩된 지역 반환

현재 더미 추천 규칙:

- `budget_max < 60000000` 이면 빈 결과
- `deal_type == "jeonse"` 이면 `분당, 성남, 경기도`
- 나머지는 `봉천동, 신림동, 사당동`

즉, 현재 추천 결과는 데이터 기반 계산이 아니라 규칙 기반 데모 응답이다.

### 5.7 오류 처리와 fallback

구현된 fallback 정책:

- `AI_DUMMY_FAIL=true` 이면 강제 fallback
- backend client 호출 실패 시 fallback
- 요청 검증 실패 시 `"다시 알려주세요."`

장점:

- FE는 예외 처리 복잡도를 거의 갖지 않아도 된다.
- 사용자 경험이 끊기지 않는다.

차이점:

- 프론트 로컬 에러 문구와 AI 서버 fallback 문구가 완전히 같지는 않다.
- 프론트는 `"잠시 문제가 있어요. 다시 추천을 받아볼까요?"`
- AI 서버는 `"잠시 문제가 있어요. 다시 입력해주세요."`

문구 정책을 하나로 맞추면 더 깔끔하다.

---

## 6. Docker 및 실행 환경 분석

### 6.1 docker-compose 구성

현재 `docker-compose.yml`에는 두 서비스만 있다.

- `frontend`
- `ai-server`

구현된 내용:

- 프론트는 Vite dev server를 Docker에서 실행
- AI 서버는 Uvicorn reload 모드로 실행
- 두 서비스 모두 소스 볼륨 마운트
- 프론트 `5173`, AI 서버 `8000` 포트 노출

좋은 점:

- 개발 중 코드 수정 반영이 쉽다.
- 프론트와 AI 서버를 함께 바로 띄울 수 있다.

기획 대비 미구현:

- `backend` 서비스 없음
- `mysql` 서비스 없음
- `.env.example` 기반 다중 서비스 운영 예시 없음

즉, "도커로 프론트+AI 개발 데모"는 가능하지만, "전체 FE+AI+BE+DB 통합 스택"은 아직 아니다.

### 6.2 Dockerfile 상태

프론트:

- `frontend/Dockerfile`은 `deps`, `dev`, `build`, `prod` 멀티스테이지
- dev 모드와 nginx 프로덕션 모드를 모두 고려했다

AI 서버:

- `ai-server/Dockerfile`은 Python 3.11 slim 기반
- `pyproject.toml` 설치 후 앱/테스트 복사

평가:

- 프론트 Dockerfile은 비교적 잘 정리되어 있다.
- AI 서버 Dockerfile도 MVP 용도로 충분하다.
- 다만 전체 시스템 기준으로는 backend/mysql 이미지가 없어 통합 배포 단위는 완성되지 않았다.

---

## 7. 백엔드 구현 상태

### 7.1 현재 상태

`backend/src/main/java`에는 현재 `BackendApplication.java`만 있다.

없는 것:

- Controller
- Service
- Entity
- Repository
- DTO
- 내부 API
- Health API
- Security 설정
- Flyway migration

`application.yaml`에는 로컬 MySQL datasource 일부만 있고, 실제 동작 가능한 백엔드 기능은 없다.

### 7.2 기획 대비 누락 항목

`backend-mvp.md` 기준으로 아직 미구현인 항목은 사실상 대부분이다.

- `POST /internal/upsert-conditions`
- `POST /internal/filter`
- `GET /healthz`
- `chat_messages` 테이블 및 JSON 컬럼 설계
- `regions`, `housing_transactions` 엔티티/적재
- MySQL 시드 적재
- 정렬 정책
- CORS/보안 정책
- Swagger/OpenAPI
- 글로벌 예외 처리
- Dockerfile
- docker-compose 통합

따라서 현재 저장소에서 "백엔드가 구현되었다"고 보기 어렵다. AI 서버의 `http` 모드는 인터페이스만 준비된 상태다.

---

## 8. 문서 대비 구현 매핑

### 8.1 plan.md 대비

구현된 것:

- FE의 유일한 진입점이 AI 서버인 구조
- 풀스크린 채팅 UI 방향
- 첫 진입 자동 질문
- 자본금 -> 거래 유형 -> 결과의 2단계 대화 흐름
- AI 서버 fallback 흡수 구조

부분 구현:

- `bot_messages` 스키마는 구현했지만 실제 렌더는 `bot.text` 중심
- quick replies 타입은 있으나 실제 UX로는 미사용

미구현:

- 지역 카드/비교 UI
- 추가 질문 확장 버전
- 자유 텍스트 해석
- 실제 BE/DB 기반 추천

### 8.2 ai-frontend.md 대비

구현된 것:

- FE는 `/chat`만 호출
- 입력을 단계별 raw로 구조화
- 정상/실패를 큰 분기 없이 렌더
- 페이지 로드 시 자동 호출

부분 구현:

- `bot.quick_replies` 타입은 정의됨
- 하지만 현재 화면 렌더에는 연결되지 않음

미구현:

- 긴 텍스트 QA
- streaming 수신
- 카드 타입 확장

### 8.3 ai-backend.md 대비

구현된 것:

- `/chat`, `/healthz`
- Conditions/ChatResponse 스키마
- MergeService
- DialogPolicy
- ResultFormatter
- fallback 정책
- mock backend 모드
- pytest

부분 구현:

- `HttpBackendClient`는 있으나 실제 BE 미구현으로 실사용 불가
- logging은 거의 없다

미구현:

- Phase 2 LLM
- 자연어 의도 추출
- LLM 응답 검증 체계

### 8.4 backend-mvp.md 대비

구현된 것:

- 사실상 Spring Boot 앱 부트스트랩만 존재

미구현:

- 체크리스트 대부분 전체

---

## 9. 테스트 및 검증 결과

실행 일자: 2026-04-25

### 9.1 프론트

실행 명령:

- `make docker-frontend-check`

결과:

- eslint 통과
- vitest 통과
- build 통과

확인된 테스트 범위:

- `UserInputParser` 숫자/거래유형 파싱
- `MockChatServer` 대화 플로우
- `ChatScreen` 렌더 플로우
- `chipMapper` 테스트

요약:

- 프론트의 현재 MVP 흐름은 테스트로 고정되어 있다.
- 다만 quick reply 렌더, 재시도 UI, 실서버 연동 오류 시나리오 등은 충분히 검증되지 않았다.

### 9.2 AI 서버

실행 명령:

- `make docker-ai-check`

결과:

- `ruff check` 통과
- `pytest` 9개 모두 통과

확인된 테스트 범위:

- `/healthz`
- `/chat` 기본 흐름
- 예산+거래유형 동시 입력
- invalid raw 재질문
- backend 실패 fallback
- dummy fail fallback
- dialog policy
- merge service
- result formatter

요약:

- AI 서버의 MVP 로직은 현재 범위 내에서 안정적이다.
- 다만 실제 Spring Boot 백엔드와의 통합 테스트는 불가능하다.

---

## 10. 기능별 세부 판정

### 10.1 실제로 사용할 수 있는 기능

- 홈 화면 진입 후 자동 첫 질문
- 숫자 예산 입력
- 전세/월세 입력
- 세션 기반 멀티턴 상태 유지
- 결과 텍스트 출력
- 빈 결과 처리
- fallback 처리
- Docker 기반 개발 실행

### 10.2 코드상 존재하지만 사용자 기능으로는 미완성인 항목

- `bot.quick_replies`
- `QuickReplyChips` 컴포넌트
- `restart`, `retry`, `hasError`
- `HttpBackendClient`

### 10.3 아직 구현되지 않은 핵심 기능

- 실제 백엔드 API
- 데이터베이스 저장
- 공공데이터 기반 추천 계산
- 추천 근거/점수 상세
- 결과 카드 UI
- 비교 UI
- 자유 텍스트 해석
- LLM 도입
- 전체 서비스 통합 Docker 스택

---

## 11. 현재 구현의 강점

- MVP 범위를 과도하게 넓히지 않고, 대화 흐름 데모를 먼저 완성했다.
- FE -> AI 단일 진입점 구조가 이미 잡혀 있어 이후 확장 방향이 선명하다.
- mock backend와 실제 http backend 인터페이스를 분리해 두어 교체 여지가 있다.
- 프론트와 AI 서버 모두 최소한의 테스트가 확보되어 있다.
- Docker 기반 개발 진입 장벽이 낮다.

---

## 12. 현재 구현의 리스크와 보완 우선순위

### 우선순위 1

실제 Spring Boot 백엔드를 구현해야 한다.

이유:

- 지금 결과는 추천 엔진이 아니라 더미 규칙 응답이다.
- 서비스 핵심 가치인 "데이터 기반 지역 추천"이 아직 없다.

### 우선순위 2

quick reply UX 방향을 하나로 정해야 한다.

선택지는 두 가지다.

- 현재처럼 텍스트 입력 중심으로 간다
- 아니면 기획 문서대로 칩 UX를 실제 연결한다

지금은 타입/컴포넌트/문서/실제 UX가 서로 다르다.

### 우선순위 3

프론트 입력 파서를 현실적인 한국어 입력에 맞게 확장해야 한다.

예:

- `2억`
- `2억 정도`
- `월세`
- `월세 원해요`

### 우선순위 4

에러/재시도/새 대화 UX를 실제 화면에서 제공해야 한다.

현재 관련 로직 일부는 훅에 있지만 UI에는 거의 노출되지 않는다.

### 우선순위 5

통합 Docker 구성을 완성해야 한다.

- `backend`
- `mysql`
- 필요시 migration/seed

이 단계가 되어야 문서상 전체 아키텍처와 실제 구현이 일치한다.

---

## 13. 최종 평가

현재 구현물은 기획 문서의 전체 범위를 모두 구현한 상태는 아니다. 다만 MVP v0의 "프론트 채팅 경험"과 "AI 서버 오케스트레이션 형태"는 잘 잡혀 있고, Docker 기반 실행과 테스트까지 갖춘 데모 단계로는 충분히 의미가 있다.

정확한 표현으로는 다음이 가장 적절하다.

- 프론트: 구현됨
- AI 서버: MVP 수준 구현됨
- Docker: 프론트+AI 개발 환경 구현됨
- 백엔드: 미구현
- 실제 추천 엔진: 미구현

따라서 다음 개발 단계의 핵심은 "현재 데모 아키텍처를 실제 데이터 기반 추천 시스템으로 연결하는 백엔드 완성"이다.
