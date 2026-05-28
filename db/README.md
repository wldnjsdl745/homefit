# DB 시드 데이터

DB 사용 전략은 환경에 따라 나뉜다.

```text
개발: Docker MySQL
운영/배포: Amazon RDS MySQL
```

Docker MySQL은 개발 중 빠른 실행과 테스트를 위한 DB다.

RDS MySQL은 실제 배포에서 Backend가 연결하는 운영 DB다.

DB 압축 파일은 `db/seed/` 디렉터리 내부에 넣어야 한다.

권장 경로는 아래와 같다.

```txt
db/seed/seed-data.sql.gz
```

압축하지 않은 SQL 파일을 사용할 수도 있다.

- `db/seed/seed-data.sql.gz` 권장
- `db/seed/seed-data.sql`

덤프 파일에는 Backend가 사용하는 테이블 구조와 초기 데이터가 함께 포함되어야 한다.

아파트 단지 추천 기능까지 사용하려면 아래 테이블 데이터도 포함하는 것이 좋다.

- `apartment_complexes`
- `apartment_transactions`
- `nearby_facilities`
- `neighborhood_demographics`
- `complex_feature_scores`

Docker MySQL 볼륨이 비어 있는 상태에서 `docker compose up frontend ai-server`를 실행하면 `db-seed`가 이 시드 파일을 한 번만 import한다.

이미 Docker DB에 `housing_transactions` 데이터가 있으면 import는 자동으로 건너뛴다.

## 시드 파일 생성 방법

로컬 MySQL에서 스키마와 데이터를 함께 덤프한다.

```sh
mysqldump --single-transaction --routines --triggers \
  -u root -p homefit > seed-data.sql
```

Docker 자동 import용 압축 파일을 만든다.

```sh
make docker-db-pack
```

위 명령을 실행하면 `db/seed/seed-data.sql.gz` 파일이 생성된다.

이 압축 파일은 Git에 올리지 않고, 필요한 사람에게 별도로 전달한다.

## RDS에 dump 데이터 import

RDS로 dump 데이터를 넣을 때는 RDS 접속 정보를 make 변수로 넘긴다.

```sh
make rds-import-seed \
  RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com \
  RDS_USER=homefit \
  RDS_PASSWORD=your_rds_password \
  RDS_DATABASE=homefit
```

RDS 데이터가 들어갔는지 확인한다.

```sh
make rds-count \
  RDS_HOST=your-rds-endpoint.ap-northeast-2.rds.amazonaws.com \
  RDS_USER=homefit \
  RDS_PASSWORD=your_rds_password \
  RDS_DATABASE=homefit
```

## 공모전/추천 데이터 적재

공공데이터포털, 국토교통부 데이터 통합채널, LOCALDATA, KOSIS/SGIS 등에서 내려받은 CSV는 아래 스크립트로 적재한다.

```sh
python scripts/load_recommendation_data.py complexes --csv data/raw/kapt_complexes.csv
python scripts/load_recommendation_data.py facilities --type school --csv data/raw/schools.csv --source-key school_location
python scripts/load_recommendation_data.py facilities --type nightlife --csv data/raw/localdata_nightlife.csv --source-key localdata_license
python scripts/load_recommendation_data.py demographics --csv data/raw/population_by_age.csv --source-key kosis_population
python scripts/load_recommendation_data.py features
```

주의:

- Backend는 DB schema 변경 작업을 실행하지 않는다.
- RDS import 전에는 dump SQL에 필요한 테이블 구조가 포함되어 있는지 확인한다.
- seed SQL에 `truncate` 또는 `delete`가 포함되어 있으면 기존 RDS 데이터가 삭제될 수 있다.
- 운영 데이터가 쌓인 뒤에는 import 전에 백업을 확인한다.
- `LOCALDATA` 일부 CSV의 `좌표정보(x/y)`는 WGS84 위경도가 아니라 TM 좌표일 수 있다. 현재 스크립트는 WGS84 위도/경도 컬럼만 거리 계산에 사용한다.
- API 키나 자료신청이 필요한 데이터는 포털에서 먼저 내려받은 뒤 `data/raw/`에 둔다.
- 단지별 추천에는 `apartment_complexes.lat/lng`와 `nearby_facilities.lat/lng`가 있어야 한다.

## 로컬 MySQL 기준으로 Docker DB 새로고침

로컬 MySQL의 최신 `regions`, `housing_transactions` 데이터를 Docker MySQL DB에 다시 반영하려면 아래 명령을 실행한다.

```sh
make docker-db-refresh-from-local
```

이 명령은 아래 작업을 순서대로 수행한다.

1. 로컬 MySQL의 `homefit` DB 전체 구조와 데이터를 `seed-data.sql`로 덤프한다.
2. `seed-data.sql`을 `db/seed/seed-data.sql.gz`로 압축한다.
3. Docker MySQL의 `regions`, `housing_transactions` 테이블을 비운 뒤 새 seed 데이터를 import한다.

즉, 이 명령은 Docker DB의 기존 `regions`, `housing_transactions` 데이터를 덮어쓴다. `docker compose down -v`를 실행하지 않으므로 `frontend_node_modules` 같은 다른 Docker volume은 삭제하지 않는다.

기본 로컬 MySQL 접속값은 아래와 같다.

| 변수 | 기본값 |
|---|---|
| `LOCAL_MYSQL_HOST` | `127.0.0.1` |
| `LOCAL_MYSQL_PORT` | `3306` |
| `LOCAL_MYSQL_USER` | `root` |
| `LOCAL_MYSQL_DATABASE` | `homefit` |

로컬 MySQL 접속값이 다르면 make 변수로 덮어쓴다.

```sh
make docker-db-refresh-from-local LOCAL_MYSQL_USER=root LOCAL_MYSQL_DATABASE=homefit
```

명령 실행 중 로컬 MySQL 비밀번호 입력을 요청받으면 로컬 MySQL 계정 비밀번호를 입력한다.

## 전달받은 사람이 해야 할 일

전달받은 `seed-data.sql.gz` 파일을 아래 위치에 둔다.

```txt
db/seed/seed-data.sql.gz
```

그 다음 서비스를 실행한다.

```sh
docker compose up frontend ai-server
```
