# Homefit — Backend MVP 체크리스트 (v0)

> BE는 **AI 서버에서만 호출되는 내부 API**. FE에 직접 노출 ❌.
> 책임: conditions 영속화 + DB 필터링 (계산).
> AI 서버 측 호출자는 [ai-backend.md](ai-backend.md), 전체 설계는 [plan.md](plan.md).

---

## 책임 분리 (꼭 숙지)

- **FE**: 채팅 UI. AI 서버만 호출.
- **AI 서버**: FE 진입점. 의미 작업 + BE 내부 호출 + 텍스트 가공.
- **BE = 데이터 계층**: conditions 저장 + DB 필터링. **FE에 직접 노출 안 됨**.
- **DB**: conditions만 영속화. AI 텍스트 / regions 결과는 미저장.

**원칙**
- AI 서버에서만 BE를 호출 (내부 네트워크).
- BE는 의미 추출 / 텍스트 가공을 하지 않음.
- 추천 결과(텍스트, regions 리스트) 는 **저장하지 않음**. conditions만 저장.

---

## 기술 스택 (이미 scaffold 됨)

- Java 21 / Spring Boot 3.5.14
- Spring Data JPA / MySQL 8 / Flyway
- Spring Security (MVP는 permitAll, 단 IP/네트워크 제한 권장)
- Spring Validation
- Gradle / Lombok

---

## 데이터 모델 (단일 테이블 중심)

> 단일 테이블 `chat_messages`에 raw + conditions JSON 저장.
> ERD([docs/erd/ERD.md](docs/erd/ERD.md))는 우리 설계로 갱신 필요 (별도 PR).

```
chat_messages
- id (UUID)
- session_id (UUID)
- raw (JSON)         -- 이번 턴 입력: { budget_max?, deal_type? }
- conditions (JSON)  -- 머지 후 누적: { budget_max?, deal_type? }
- created_at

regions             (시군구 단위)
- id, sido, sigungu

housing_transactions  (MOLIT #11848613)
- region_id, deal_type (jeonse/monthly_rent), deposit_amount, monthly_rent, contract_date
```

> v0은 매매(`sale`) 제외. 전세 + 월세만 적재.

---

## 구현 체크리스트

### B0. 합의
- [ ] [plan.md §4](plan.md) FE↔AI 계약 확인
- [ ] [ai-backend.md](ai-backend.md) AI↔BE 내부 계약 확인
- [ ] [docs/erd/ERD.md](docs/erd/ERD.md) 우리 설계로 갱신

### B1. DB / Entity
- [ ] `application.yaml` MySQL 설정
- [ ] Flyway 마이그레이션
- [ ] Entity: `ChatMessage` (raw/conditions를 JSON 컬럼으로)
- [ ] Entity: `Region` / `HousingTransaction`
- [ ] Repository

### B2. 시드 적재
- [ ] MOLIT #11848613 데이터셋 다운로드
- [ ] CSV → DB 적재 로직 (CommandLineRunner)
- [ ] 적재 범위: 서울 25개 구 + 경기 일부 (분당, 성남 등 시연용)
- [ ] 거래 유형: 전세 + 월세만

### B3. 내부 API — `POST /internal/upsert-conditions`
> AI 서버가 호출. raw + 직전 conditions를 받아 머지된 conditions 반환 + 저장.
>
> *대안*: AI 서버가 머지 책임을 가지면 BE는 단순 INSERT/UPSERT만. (`MergeService`가 AI 서버 측에 있음)
> → 본 문서는 **AI 서버가 머지**하고 BE는 **저장만** 한다는 합의 채택.

**Request**
```json
{
  "session_id": "uuid | null",
  "raw": { "budget_max": 200000000 },
  "conditions": { "deal_type": "jeonse" }
}
```

**Response**
```json
{
  "session_id": "uuid",
  "conditions": { "budget_max": 200000000, "deal_type": "jeonse" }
}
```

체크:
- [ ] session_id null이면 새 UUID 발급
- [ ] chat_messages INSERT (raw + 머지된 conditions, AI 서버에서 받은 그대로)
- [ ] 응답에 session_id + 머지된 conditions echo

### B4. 내부 API — `POST /internal/filter`
> AI 서버가 호출. conditions로 DB 필터링 후 regions 리스트 반환.

**Request**
```json
{
  "conditions": { "budget_max": 200000000, "deal_type": "jeonse" }
}
```

**Response**
```json
{
  "regions": ["분당", "성남", "경기도"]
}
```

체크:
- [ ] `housing_transactions` 조회
- [ ] `deal_type` 일치
- [ ] `budget_max` 이내 매물 (전세: deposit_amount ≤ budget_max)
- [ ] 시군구별 그룹화 + 평균 또는 거래량 기준 정렬
- [ ] **상위 3개 시군구 이름 반환** (저장 ❌)
- [ ] 결과 없음 → `regions: []`

### B5. 점수식 / 정렬 정책 (단순)
- [ ] 필터링: `deposit_amount ≤ budget_max` AND `deal_type = ?`
- [ ] 정렬: 평균 거래가 오름차순 또는 거래 건수 내림차순 (BE 결정)
- [ ] 상위 3개 시군구 반환

### B6. 보안 / CORS
- [ ] **FE 직접 호출 차단**: CORS 미허용 (또는 AI 서버 IP만 허용)
- [ ] AI 서버 ↔ BE는 같은 docker-compose 네트워크 → 인증 생략 가능 (MVP)
- [ ] 운영 단계: 내부 토큰 (`X-Internal-Token`) 권장

### B7. 운영 기본기
- [ ] springdoc-openapi 추가 (내부 API용 Swagger)
- [ ] `/healthz` 또는 `/actuator/health`
- [ ] 글로벌 예외 핸들러

### B8. Docker / 배포
- [ ] Dockerfile (multi-stage, JRE 21)
- [ ] docker-compose에 `mysql` + `backend` 추가
- [ ] AI 서버와 같은 네트워크
- [ ] `.env.example`

---

## API 명세 요약

> 모든 BE 엔드포인트는 **내부 전용**. FE는 호출하지 않음.

| Method | Path | 호출자 | 용도 |
|--------|------|-------|------|
| POST | `/internal/upsert-conditions` | AI 서버 | 세션 생성/업데이트 + chat_message 저장 |
| POST | `/internal/filter` | AI 서버 | conditions로 regions 필터링 |
| GET | `/healthz` | (내부) | 헬스체크 |
| GET | `/swagger-ui.html` | 개발자 | API 문서 |

---

## 환경변수

| 키 | 값 (예시) | 의미 |
|----|----------|------|
| `SPRING_DATASOURCE_URL` | `jdbc:mysql://mysql:3306/homefit` | DB |
| `SPRING_DATASOURCE_USERNAME` | `homefit` | |
| `SPRING_DATASOURCE_PASSWORD` | `***` | |
| `SERVER_PORT` | `8080` | |

---

## 자주 하는 실수

- BE에서 의미 추출 / 텍스트 가공하지 말 것 (AI 서버 책임)
- 추천 결과(regions, AI 텍스트) 저장하지 말 것
- FE에 CORS 허용하지 말 것 (AI 서버만)
- 매매(`sale`) 적재하지 말 것 (v0 미사용)
- secret을 코드에 커밋하지 말 것

---

## 변경 관리

- API 응답 스키마 변경 → [ai-backend.md](ai-backend.md) 동시 갱신
- 점수식 / 정렬 / 시드 데이터 → BE 단독 결정
- ERD 변경 → 시니어 검토 (FE/AI에 영향 가능)
