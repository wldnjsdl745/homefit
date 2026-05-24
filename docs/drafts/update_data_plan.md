# Homefit 데이터 고도화 계획

- 작성일: 2026-05-24
- 상태: In Progress
- 목표: 교통 접근성 + 전세 안전도 데이터를 추가해 서울 지역 추천 품질 향상

---

## 0. 배경

현재 추천 기준은 **실거래가(가격)** 단일 지표.
아래 두 가지를 추가해 추천 정확도를 높인다.

1. **지하철 접근성** — GTFS 파싱으로 구별 역 수 계산
2. **출퇴근 목적지 통근 시간** — GTFS 최단경로로 구×목적지 사전 계산
3. **전세 안전도** — 주택도시보증공사 보증사고율 기반 안전등급

---

## 1. 구현 순서

```
1단계  DB 스키마 마이그레이션 (V4~V6)
2단계  데이터 수집 스크립트 (GTFS 파싱, 안전도 로딩)
3단계  백엔드 filter 로직 수정
4단계  AI 서버 다이얼로그 + 결과 포맷 수정
5단계  통합 테스트
```

---

## 2. DB 스키마 (1단계)

### 추가 테이블 3개

#### V4 — region_transit

```sql
CREATE TABLE region_transit (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_name   VARCHAR(20)    NOT NULL UNIQUE COMMENT '서울 구 이름 (ex: 관악구)',
    subway_count  INT            NOT NULL DEFAULT 0 COMMENT '구 내 지하철역 수',
    transit_score DECIMAL(5, 2)  NOT NULL DEFAULT 0 COMMENT '접근성 점수 0-100 (역 수 정규화)',
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### V5 — region_commute

```sql
CREATE TABLE region_commute (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_name     VARCHAR(20)   NOT NULL COMMENT '서울 구 이름',
    destination_key VARCHAR(30)   NOT NULL COMMENT 'gangnam | yeouido | gwanghwamun | hongdae | jamsil',
    avg_minutes     INT           NOT NULL COMMENT '대중교통 평균 통근 시간(분)',
    UNIQUE KEY uq_region_dest (region_name, destination_key)
);
```

#### V6 — region_jeonse_safety

```sql
CREATE TABLE region_jeonse_safety (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_name   VARCHAR(20)    NOT NULL UNIQUE COMMENT '서울 구 이름',
    accident_rate DECIMAL(6, 4)  NOT NULL COMMENT '전세사고율 (0.0000~1.0000)',
    safety_grade  CHAR(1)        NOT NULL COMMENT 'A(낮음) / B(보통) / C(높음)',
    reference_date DATE          NOT NULL COMMENT '기준 연월'
);
```

---

## 3. 데이터 수집 스크립트 (2단계)

위치: `scripts/` (프로젝트 루트)

### 3.1 GTFS 파싱 → region_transit + region_commute

**입력**: 국가교통DB에서 다운받은 서울 GTFS 파일 묶음
- `stops.txt` — 정류장/역 위치 (위경도)
- `stop_times.txt` — 구간별 소요 시간
- `trips.txt`, `routes.txt` — 노선 정보

**출력**:
- `region_transit`: 구별 지하철역 수 → 접근성 점수 (0-100 정규화)
- `region_commute`: 구 대표좌표 → 5개 목적지 최단 경로 통근 시간

**목적지 5개 (destination_key)**:

| key | 표시 라벨 | 기준 역 |
|---|---|---|
| `gangnam` | 강남/서초 | 강남역 (2호선) |
| `yeouido` | 여의도 | 여의도역 (5·9호선) |
| `gwanghwamun` | 광화문/종로 | 광화문역 (5호선) |
| `hongdae` | 홍대/마포 | 홍대입구역 (2·공항철도) |
| `jamsil` | 강동/잠실 | 잠실역 (2·8호선) |

**스크립트**: `scripts/parse_gtfs.py`

```
python scripts/parse_gtfs.py \
  --gtfs-dir data/gtfs/seoul \
  --db-url mysql+pymysql://homefit:homefit@localhost:3307/homefit
```

### 3.2 전세 안전도 → region_jeonse_safety

**입력**: 주택도시보증공사 보증사고율 데이터 (CSV)
- 공공데이터포털(data.go.kr) 또는 R-ONE에서 다운로드
- 구별 전세반환보증 사고 건수 / 총 보증 건수

**안전등급 기준**:

| 등급 | 사고율 |
|---|---|
| A | 0.5% 미만 |
| B | 0.5% 이상 ~ 2% 미만 |
| C | 2% 이상 |

**스크립트**: `scripts/load_safety.py`

```
python scripts/load_safety.py \
  --csv data/jeonse_safety.csv \
  --db-url mysql+pymysql://homefit:homefit@localhost:3307/homefit
```

---

## 4. 백엔드 filter 로직 수정 (3단계)

### API 변경: POST /internal/filter

**Request 추가 필드**:

```json
{
  "conditions": {
    "budget_max": 200000000,
    "deal_type": "jeonse",
    "commute_destination": "gangnam"
  }
}
```

**Response 추가 필드**:

```json
{
  "regions": ["영등포구", "관악구", "동작구"],
  "region_details": [
    { "name": "영등포구", "commute_minutes": 28, "safety_grade": "A" },
    { "name": "관악구",   "commute_minutes": 35, "safety_grade": "A" },
    { "name": "동작구",   "commute_minutes": 42, "safety_grade": "B" }
  ]
}
```

`region_details`는 `commute_destination` 없을 때도 반환 (commute_minutes 제외, safety_grade만).

### 랭킹 로직

```
목적지 있을 때:
  가격 필터 → 복합점수(가격 50% + 통근시간 30% + 지하철접근성 20%) 정렬 → 상위 5개

목적지 없을 때:
  가격 필터 → 복합점수(가격 70% + 지하철접근성 30%) 정렬 → 상위 5개
```

---

## 5. AI 서버 수정 (4단계)

### 5.1 다이얼로그 변경

```
step 0: ask_budget
step 1: ask_deal_type
step 2: (monthly_rent만) ask_monthly_rent
step 3: ask_commute      ← 추가
step RESULT
```

### 5.2 conditions 스키마 추가

```python
# app/schemas.py
commute_destination: str | None = None
# 허용값: gangnam | yeouido | gwanghwamun | hongdae | jamsil | None
```

### 5.3 칩 추가

```python
# app/services/chip_catalog.py
COMMUTE_CHIPS = [
  ChipDefinition(chip_id="commute_gangnam",     label="강남/서초",  raw=Conditions(commute_destination="gangnam")),
  ChipDefinition(chip_id="commute_yeouido",     label="여의도",     raw=Conditions(commute_destination="yeouido")),
  ChipDefinition(chip_id="commute_gwanghwamun", label="광화문/종로", raw=Conditions(commute_destination="gwanghwamun")),
  ChipDefinition(chip_id="commute_hongdae",     label="홍대/마포",  raw=Conditions(commute_destination="hongdae")),
  ChipDefinition(chip_id="commute_jamsil",      label="강동/잠실",  raw=Conditions(commute_destination="jamsil")),
  ChipDefinition(chip_id="commute_skip",        label="건너뛰기",   raw=Conditions()),  # destination 없이 진행
]
```

### 5.4 결과 메시지 예시

목적지 있을 때:
```
강남역 기준 전세 2억 예산에 맞는 서울 지역은
영등포구(28분·안전A)·관악구(35분·안전A)·동작구(42분·안전B)입니다.
```

목적지 없을 때:
```
전세 2억 예산에 맞는 서울 지역은
마포구(안전A)·은평구(안전B)·서대문구(안전A)입니다.
```

---

## 6. 진행 체크리스트

### 1단계 — DB 스키마
- [ ] V4__add_region_transit.sql
- [ ] V5__add_region_commute.sql
- [ ] V6__add_region_jeonse_safety.sql

### 2단계 — 데이터 수집
- [ ] GTFS 파일 확보 (국가교통DB)
- [ ] scripts/parse_gtfs.py 작성
- [ ] scripts/load_safety.py 작성
- [ ] 전세 안전도 CSV 확보
- [ ] DB 데이터 로딩 확인

### 3단계 — 백엔드
- [ ] FilterConditions에 commute_destination 추가
- [ ] FilterResponse에 region_details 추가
- [ ] region_commute JOIN 쿼리
- [ ] 복합 점수 랭킹 로직
- [ ] 전세 선택 시 safety_grade JOIN

### 4단계 — AI 서버
- [ ] schemas.py: commute_destination 추가
- [ ] chip_catalog.py: COMMUTE_CHIPS 추가
- [ ] dialog_policy.py: ASK_COMMUTE 단계 추가
- [ ] message_builder.py: ask_commute() 추가
- [ ] chat_service.py: step 3 분기 추가
- [ ] result_formatter.py: commute_minutes + safety_grade 포맷
- [ ] MockBackendClient: region_details 반환 업데이트
- [ ] 테스트 업데이트

### 5단계 — 통합 테스트
- [ ] make ai-check (pytest)
- [ ] make up → 실제 흐름 확인
- [ ] commute 있는 케이스 / 없는 케이스 모두 확인

---

## 7. 미결 사항

- [ ] GTFS 최단경로 알고리즘: Dijkstra 직접 구현 vs 외부 라이브러리 (NetworkX 등)
- [ ] 전세 안전도 원본 데이터 URL/형식 확인 필요
- [ ] `region_details` 포함 시 API 문서(API.md) 업데이트 필요
- [ ] 백엔드 `/internal/filter` 변경은 백엔드 팀과 협의 필요
