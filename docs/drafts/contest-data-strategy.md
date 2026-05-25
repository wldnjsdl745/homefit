# Homefit 공모전 데이터 활용 전략

작성일: 2026-05-25

## 1. 목표

Homefit의 공모전 제출 방향은 "AI 기반 주거 맞춤 추천 서비스 개발"로 잡는다.

핵심 차별점:

- 실거래가만 보지 않고 주변 인프라와 동네 연령층을 함께 반영한다.
- 추천 단위를 `구`가 아니라 `아파트 단지`로 낮춘다.
- 사용자의 자연어 선호를 AI가 구조화하고, Backend가 데이터 기반 점수를 계산한다.
- 추천 결과에 "왜 이 아파트인지"를 설명한다.

## 2. 가점 대응

| 가점 항목 | 대응 전략 |
|---|---|
| 데이터융합 5점 | 국토부 실거래가 + 공동주택 단지정보 + 학교 + 병원/약국 + 유흥시설 + 체육시설 + 연령층/교통 데이터를 단지 단위로 결합 |
| 가명정보결합 5점 | 직접 개인정보를 쓰지 않고 행정동/격자 단위 집계 인구, 교통 O/D, 보증사고율 같은 비식별/집계 데이터를 사용. 가능하면 안심구역 또는 제공기관 집계 데이터로 확장 |
| 안심구역 5점 | 한국교통연구원 모바일 경로형 데이터, 교통카드 이용내역 등 민감도가 있는 데이터는 신청/안심구역 이용 가능성을 별도 제안 |
| AI활용 10점 | Qwen/GPT로 자연어 조건 추출, LightGBM/랭킹 모델 또는 점수 기반 AI 분석으로 추천 점수 산출/튜닝 |

## 3. 사용할 데이터

### 3.1 필수 데이터

| 데이터 | 출처 | 사용 목적 | 적재 테이블 |
|---|---|---|---|
| 아파트 매매 실거래가 자료 | 공공데이터포털/국토교통부 | 예산 필터, 최근 거래가, 가격 안정성 | `apartment_transactions` |
| 아파트 전월세 실거래가 자료 | 공공데이터포털/국토교통부 | 전세/월세 추천 확장 | `apartment_transactions` |
| 공동주택 단지 목록/기본정보 | 국토교통부 K-APT API | 단지 master, 세대수, 주소, 관리/설비 정보 | `apartment_complexes` |
| 전국초중등학교위치표준데이터 | 공공데이터포털 | 학교 접근성, 초등학교 거리 | `nearby_facilities` |
| 지방행정인허가데이터 | LOCALDATA | 유흥주점, 단란주점, 체육시설, 노래연습장 등 | `nearby_facilities` |
| 병의원/약국 현황 | 건강보험심사평가원/공공데이터포털 | 의료 접근성 | `nearby_facilities` |
| 주민등록 연령별 인구 | KOSIS/SGIS/서울 열린데이터광장 | 동네 연령층 매칭 | `neighborhood_demographics` |

### 3.2 확장 데이터

| 데이터 | 출처 | 사용 목적 |
|---|---|---|
| GTFS/역 위치 | 국가교통DB, 공공데이터포털 | 역세권/대중교통 접근성 |
| 교통카드 통계/O-D | STCIS, 국가교통 데이터 오픈마켓 | 실제 통행 시간/혼잡/생활권 |
| View-T 통행지표 | View-T | 행정구역/링크 단위 이동성 지표 |
| 전세반환보증 현황/보증사고율 | 주택도시보증공사, R-ONE | 전세 안전도 |
| KB부동산 지표 | KB부동산 데이터 | 지역 가격 흐름 보강 |
| R-ONE 부동산통계 | 한국부동산원 | 가격동향/거래현황 보강 |
| ECOS 금리/물가 | 한국은행 | 시장 환경 설명 feature |

## 4. 데이터 파이프라인

```text
외부 포털/API/다운로드
  -> CSV/API 원본 저장
  -> scripts/load_recommendation_data.py
  -> apartment_complexes / apartment_transactions / nearby_facilities / neighborhood_demographics
  -> complex_feature_scores 사전 계산
  -> Backend filter/ranking
  -> AI Server 설명 생성
  -> Frontend 추천 카드 렌더
```

## 5. 현재 추가된 DB 구조

새 migration:

- `V10__add_apartment_recommendation_data.sql`

추가 테이블:

- `data_sources`
- `apartment_complexes`
- `apartment_transactions`
- `nearby_facilities`
- `neighborhood_demographics`
- `complex_feature_scores`

## 6. 적재 명령 예시

공동주택 단지 정보:

```sh
python scripts/load_recommendation_data.py complexes \
  --csv data/raw/kapt_complexes.csv \
  --source-key molit_kapt_basic
```

학교:

```sh
python scripts/load_recommendation_data.py facilities \
  --type school \
  --source-key school_location \
  --csv data/raw/schools.csv
```

유흥시설:

```sh
python scripts/load_recommendation_data.py facilities \
  --type nightlife \
  --source-key localdata_license \
  --csv data/raw/localdata_nightlife.csv
```

체육시설:

```sh
python scripts/load_recommendation_data.py facilities \
  --type gym \
  --source-key localdata_license \
  --csv data/raw/localdata_gym.csv
```

병원/약국:

```sh
python scripts/load_recommendation_data.py facilities \
  --type hospital \
  --source-key hira_hospital \
  --csv data/raw/hospitals.csv

python scripts/load_recommendation_data.py facilities \
  --type pharmacy \
  --source-key hira_pharmacy \
  --csv data/raw/pharmacies.csv
```

연령층:

```sh
python scripts/load_recommendation_data.py demographics \
  --source-key kosis_population \
  --csv data/raw/population_by_age.csv
```

단지별 feature 재계산:

```sh
python scripts/load_recommendation_data.py features
```

## 7. 추천 점수 초안

Hard filter:

- 거래 유형
- 예산 상한
- 면적대
- 최근 거래 존재
- 서비스 지역

Soft score:

```text
final_score =
  0.30 * price_score
+ 0.20 * commute_score
+ 0.15 * school_score
+ 0.10 * medical_score
+ 0.10 * lifestyle_score
+ 0.10 * quiet_score
+ 0.05 * demographic_score
```

사용자 선호에 따라 가중치는 동적으로 조정한다.

예:

- "아이 학교가 중요해요" -> `school_score` 가중치 상승
- "유흥시설 없는 조용한 곳" -> `quiet_score` 가중치 상승
- "병원 가까운 곳" -> `medical_score` 가중치 상승
- "젊은 사람이 많은 동네" -> `demographic_score`에서 youth ratio 강조

## 8. AI 활용 설계

학습/분석 도구 후보:

- Qwen 또는 GPT: 사용자 자연어에서 주거 조건 추출
- BERT/Sentence-BERT: 사용자 선호 문장과 단지 설명/후기/지역 설명 embedding 매칭
- LightGBM/XGBoost: 실제 클릭/저장/선택 로그가 쌓이면 랭킹 모델 학습
- KMeans/HDBSCAN: 단지 feature 기반 동네 유형 군집화
- SHAP: 추천 점수 설명 가능성 확보

현재 코드와 가장 자연스러운 1차 AI 활용:

1. Qwen/GPT로 `budget_max`, `deal_type`, `workplace`, `avoid_nightlife`, `school_importance`, `medical_importance`, `preferred_age_group` 추출
2. Backend가 데이터 기반 score 계산
3. AI 서버가 score reason을 한국어 설명으로 정리

## 9. 바로 해야 할 작업

1. 실제 seed SQL이 비어 있으므로 `db/seed/seed-data.sql.gz`에 유효한 dump를 다시 넣는다.
2. 국토부 실거래가 CSV/API 원본을 `data/raw/`에 모은다.
3. K-APT 단지 목록/기본정보를 받아 `apartment_complexes`에 적재한다.
4. 학교/유흥/체육/병원/약국 데이터를 `nearby_facilities`에 넣는다.
5. KOSIS/SGIS 연령층 데이터를 `neighborhood_demographics`에 넣는다.
6. `features` 명령으로 `complex_feature_scores`를 만든다.
7. Backend의 현재 `apartments` 응답에 `complex_feature_scores` 기반 주변 인프라 점수와 설명 근거를 연결한다.
