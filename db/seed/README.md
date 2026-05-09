# DB 시드 데이터

DB 압축 파일은 `db/seed/` 디렉터리 내부에 넣어야 한다.

권장 경로는 아래와 같다.

```txt
db/seed/seed-data.sql.gz
```

압축하지 않은 SQL 파일을 사용할 수도 있다.

- `db/seed/seed-data.sql.gz` 권장
- `db/seed/seed-data.sql`

덤프 파일에는 `regions`와 `housing_transactions` 테이블의 데이터가 포함되어야 한다.

Docker MySQL 볼륨이 비어 있는 상태에서 `docker compose up frontend ai-server`를 실행하면, backend가 먼저 실행되어 Flyway가 스키마를 생성한 뒤 이 시드 파일을 한 번만 import한다.

이미 Docker DB에 `housing_transactions` 데이터가 있으면 import는 자동으로 건너뛴다.

## 시드 파일 생성 방법

로컬 MySQL에서 데이터만 덤프한다.

```sh
mysqldump --no-create-info --complete-insert --single-transaction \
  -u root -p homefit regions housing_transactions > seed-data.sql
```

Docker 자동 import용 압축 파일을 만든다.

```sh
make docker-db-pack
```

위 명령을 실행하면 `db/seed/seed-data.sql.gz` 파일이 생성된다.

이 압축 파일은 Git에 올리지 않고, 필요한 사람에게 별도로 전달한다.

## 전달받은 사람이 해야 할 일

전달받은 `seed-data.sql.gz` 파일을 아래 위치에 둔다.

```txt
db/seed/seed-data.sql.gz
```

그 다음 서비스를 실행한다.

```sh
docker compose up frontend ai-server
```
