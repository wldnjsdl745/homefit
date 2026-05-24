# Homefit Backend

Homefit 백엔드 서버입니다.

AI 서버가 호출하는 내부 API를 제공하고, 사용자 조건 저장과 지역 추천용 거래 데이터 필터링을 담당합니다.

## Tech Stack

- **Java**: 21
- **Spring Boot**: 3.5.14
- **Build Tool**: Gradle
- **Database**: MySQL
- **Migration**: Flyway
- **Container**: Docker

## Dependencies

- **Spring Web**: RESTful API 구현
- **Spring Data JPA**: ORM 기반 데이터 접근
- **Spring Security**: 인증/인가 및 보안 설정
- **Spring Validation**: 요청 데이터 검증
- **Spring Boot Actuator**: 헬스체크 및 애플리케이션 상태 확인
- **Flyway**: DB 마이그레이션 버전 관리
- **MySQL Driver**: MySQL DB 연결
- **Lombok**: 반복 코드 간소화

## Test Dependencies

- **Spring Boot Test**: Spring Boot 통합 테스트
- **Spring Security Test**: Security 설정 테스트
- **H2 Database**: 테스트용 인메모리 DB
- **JUnit Platform Launcher**: JUnit 테스트 실행

## 역할

Backend는 Frontend가 직접 호출하지 않습니다.

요청 흐름은 아래와 같습니다.

```text
Frontend -> AI Server -> Backend -> MySQL
```

Backend의 주요 책임:

- 세션별 사용자 입력과 누적 조건 저장
- 거래 조건 검증
- MySQL 거래 데이터 조회
- 조건에 맞는 지역 목록 반환
- DB schema migration 실행

## 주요 API

### `POST /internal/upsert-conditions`

세션을 생성하거나 기존 세션의 조건을 업데이트합니다.

역할:

- `session_id`가 없으면 새 세션 생성
- `chat_messages`에 이번 턴의 `raw`와 누적 `conditions` 저장
- 저장된 최종 `session_id`, `conditions` 반환

### `POST /internal/filter`

누적 조건을 기준으로 추천 지역을 조회합니다.

역할:

- `deal_type`, `budget_max` 검증
- 원 단위 입력값을 만원 단위로 변환
- `housing_transactions`, `regions` 조회
- 상위 지역명 목록 반환

### `GET /healthz`

애플리케이션 생존 확인용 헬스체크 API입니다.

## Database

주요 테이블:

- `regions`: 지역 기준 정보
- `housing_transactions`: 주거 거래 데이터
- `chat_messages`: 사용자 입력과 누적 조건 저장

마이그레이션 파일 위치:

```text
src/main/resources/db/migration
```

현재 migration:

- `V1__init.sql`
- `V2__increase_chat_message_created_at_precision.sql`
- `V3__add_sale_transactions.sql`
- `V4__add_region_transit.sql`
- `V5__add_region_commute.sql`
- `V6__add_region_jeonse_safety.sql`
- `V7__seed_region_transit.sql`
- `V8__seed_region_commute.sql`
- `V9__seed_region_jeonse_safety.sql`

## Environment Variables

| 변수 | 설명 | 기본값 |
|---|---|---|
| `SPRING_DATASOURCE_URL` | MySQL JDBC URL | 개발 Docker Compose에서는 `jdbc:mysql://db:3306/homefit?...`, 운영에서는 RDS endpoint |
| `SPRING_DATASOURCE_USERNAME` | DB 사용자명 | 개발 기본값 `homefit` |
| `SPRING_DATASOURCE_PASSWORD` | DB 비밀번호 | 개발 기본값 `homefit` |
| `SPRING_FLYWAY_BASELINE_VERSION` | 기존 V3 스키마 자동 채택 시 baseline으로 간주할 migration version | `3` |

개발 Docker Compose에서는 기본적으로 아래 DB를 사용합니다.

```text
jdbc:mysql://db:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8&allowPublicKeyRetrieval=true&useSSL=false
```

운영 EC2에서는 RDS endpoint를 사용합니다.

```text
jdbc:mysql://your-rds-endpoint.ap-northeast-2.rds.amazonaws.com:3306/homefit?serverTimezone=Asia/Seoul&characterEncoding=UTF-8
```

RDS에 이미 `regions`, `housing_transactions`, `chat_messages` 테이블과 `housing_transactions.sale_price_amount` 컬럼이 있고 Flyway 이력이 없다면, Backend는 현재 스키마를 자동으로 `V3` baseline으로 등록합니다.
이후 `V4`부터의 migration만 실행합니다.

## Local Run

백엔드만 로컬에서 실행하려면 MySQL이 먼저 실행되어 있어야 합니다.

```sh
./gradlew bootRun
```

프로젝트 루트에서 Docker Compose로 실행할 수도 있습니다.

```sh
docker compose up backend
```

AI 서버와 함께 전체 흐름을 실행하려면 프로젝트 루트에서 실행합니다.

```sh
docker compose up frontend ai-server
```

## Test

```sh
./gradlew test
```

## Docker

Docker는 개발 환경에서 사용합니다.

운영 EC2에서는 Docker 없이 Spring Boot jar를 systemd service로 실행합니다.

백엔드 Dockerfile은 Java 21 기반 이미지로 빌드합니다.

- Build stage: `eclipse-temurin:21-jdk-alpine`
- Runtime stage: `eclipse-temurin:21-jre-alpine`

컨테이너는 8080 포트를 사용합니다.

```text
EXPOSE 8080
```

## Production Run

운영 EC2에서는 Backend를 systemd service로 실행하고 RDS MySQL에 연결합니다.

권장 JVM 메모리 제한:

```text
JAVA_TOOL_OPTIONS=-Xms128m -Xmx384m -XX:MaxMetaspaceSize=128m
```

예시 파일:

```text
deploy/systemd/backend.service.example
```

## Security

현재 보안 설정은 MVP 내부 API 구조를 기준으로 합니다.

허용 경로:

- `/internal/**`
- `/healthz`
- `/actuator/health`

그 외 요청은 인증이 필요합니다.

운영 배포에서는 Backend를 외부에 직접 노출하지 않고, AI Server와 같은 내부 네트워크에서만 접근하도록 제한해야 합니다.
