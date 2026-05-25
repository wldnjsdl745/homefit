CREATE TABLE data_sources (
    id             BIGINT NOT NULL AUTO_INCREMENT,
    source_key     VARCHAR(80) NOT NULL,
    provider       VARCHAR(100) NOT NULL,
    name           VARCHAR(200) NOT NULL,
    url            VARCHAR(500) NOT NULL,
    category       VARCHAR(50) NOT NULL,
    requires_key   BOOLEAN NOT NULL DEFAULT TRUE,
    update_cycle   VARCHAR(50) NULL,
    note           VARCHAR(500) NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_data_sources PRIMARY KEY (id),
    CONSTRAINT uq_data_sources_source_key UNIQUE (source_key)
);

CREATE TABLE apartment_complexes (
    id               BIGINT NOT NULL AUTO_INCREMENT,
    source_key       VARCHAR(80) NOT NULL,
    external_id      VARCHAR(120) NOT NULL,
    name             VARCHAR(255) NOT NULL,
    sido             VARCHAR(50) NOT NULL,
    sigungu          VARCHAR(50) NOT NULL,
    legal_dong_name  VARCHAR(50) NULL,
    road_address     VARCHAR(500) NULL,
    lot_address      VARCHAR(500) NULL,
    lat              DECIMAL(10, 7) NULL,
    lng              DECIMAL(10, 7) NULL,
    household_count  INT NULL,
    built_year       SMALLINT NULL,
    parking_count    INT NULL,
    heating_type     VARCHAR(80) NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_apartment_complexes PRIMARY KEY (id),
    CONSTRAINT uq_apartment_complexes_source_external UNIQUE (source_key, external_id)
);

CREATE INDEX idx_apartment_complexes_region
    ON apartment_complexes (sido, sigungu, legal_dong_name);

CREATE INDEX idx_apartment_complexes_location
    ON apartment_complexes (lat, lng);

CREATE TABLE apartment_transactions (
    id                  BIGINT NOT NULL AUTO_INCREMENT,
    complex_id          BIGINT NULL,
    source_key          VARCHAR(80) NOT NULL,
    deal_type           VARCHAR(30) NOT NULL,
    contract_date       DATE NOT NULL,
    area_m2             DECIMAL(10, 2) NULL,
    floor_no            INT NULL,
    sale_price_amount   BIGINT NULL,
    deposit_amount      BIGINT NULL,
    monthly_rent        INT NULL,
    raw_complex_name    VARCHAR(255) NULL,
    raw_address         VARCHAR(500) NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_apartment_transactions PRIMARY KEY (id),
    CONSTRAINT fk_apartment_transactions_complex
        FOREIGN KEY (complex_id)
            REFERENCES apartment_complexes (id),
    CONSTRAINT chk_apartment_transactions_deal_type
        CHECK (deal_type IN ('jeonse', 'monthly_rent', 'sale'))
);

CREATE INDEX idx_apartment_transactions_complex_date
    ON apartment_transactions (complex_id, contract_date);

CREATE INDEX idx_apartment_transactions_deal_price
    ON apartment_transactions (deal_type, sale_price_amount, deposit_amount, monthly_rent);

CREATE TABLE nearby_facilities (
    id             BIGINT NOT NULL AUTO_INCREMENT,
    source_key     VARCHAR(80) NOT NULL,
    facility_type  VARCHAR(40) NOT NULL,
    subtype        VARCHAR(120) NULL,
    name           VARCHAR(255) NOT NULL,
    sido           VARCHAR(50) NULL,
    sigungu        VARCHAR(50) NULL,
    legal_dong_name VARCHAR(50) NULL,
    road_address   VARCHAR(500) NULL,
    lot_address    VARCHAR(500) NULL,
    lat            DECIMAL(10, 7) NULL,
    lng            DECIMAL(10, 7) NULL,
    status         VARCHAR(80) NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_nearby_facilities PRIMARY KEY (id),
    CONSTRAINT chk_nearby_facilities_type
        CHECK (facility_type IN ('school', 'hospital', 'pharmacy', 'gym', 'nightlife', 'transit', 'commercial', 'other'))
);

CREATE INDEX idx_nearby_facilities_type_region
    ON nearby_facilities (facility_type, sido, sigungu);

CREATE INDEX idx_nearby_facilities_location
    ON nearby_facilities (lat, lng);

CREATE TABLE neighborhood_demographics (
    id                 BIGINT NOT NULL AUTO_INCREMENT,
    source_key         VARCHAR(80) NOT NULL,
    sido               VARCHAR(50) NOT NULL,
    sigungu            VARCHAR(50) NOT NULL,
    admin_dong_name    VARCHAR(80) NULL,
    legal_dong_name    VARCHAR(80) NULL,
    reference_month    CHAR(6) NOT NULL,
    population_total   INT NULL,
    child_ratio        DECIMAL(6, 4) NULL,
    youth_ratio        DECIMAL(6, 4) NULL,
    senior_ratio       DECIMAL(6, 4) NULL,
    household_count    INT NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_neighborhood_demographics PRIMARY KEY (id),
    CONSTRAINT uq_neighborhood_demographics_scope UNIQUE (
        source_key, sido, sigungu, admin_dong_name, legal_dong_name, reference_month
    )
);

CREATE INDEX idx_neighborhood_demographics_region
    ON neighborhood_demographics (sido, sigungu, legal_dong_name, admin_dong_name);

CREATE TABLE complex_feature_scores (
    complex_id              BIGINT NOT NULL,
    school_count_500m       INT NOT NULL DEFAULT 0,
    elementary_distance_m   INT NULL,
    hospital_count_1000m    INT NOT NULL DEFAULT 0,
    pharmacy_count_1000m    INT NOT NULL DEFAULT 0,
    gym_count_1000m         INT NOT NULL DEFAULT 0,
    nightlife_count_500m    INT NOT NULL DEFAULT 0,
    transit_count_1000m     INT NOT NULL DEFAULT 0,
    child_ratio             DECIMAL(6, 4) NULL,
    youth_ratio             DECIMAL(6, 4) NULL,
    senior_ratio            DECIMAL(6, 4) NULL,
    school_score            DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    medical_score           DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    lifestyle_score         DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    quiet_score             DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    demographic_score       DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_complex_feature_scores PRIMARY KEY (complex_id),
    CONSTRAINT fk_complex_feature_scores_complex
        FOREIGN KEY (complex_id)
            REFERENCES apartment_complexes (id)
);

INSERT INTO data_sources (source_key, provider, name, url, category, requires_key, update_cycle, note) VALUES
  ('molit_kapt_list', '국토교통부', '공동주택 단지 목록제공 서비스', 'https://www.data.go.kr/data/15057332/openapi.do', 'apartment', TRUE, '실시간', 'K-APT 단지 목록 master 후보'),
  ('molit_kapt_basic', '국토교통부', '공동주택 기본 정보제공 서비스', 'https://www.data.go.kr/data/15058453/openapi.do', 'apartment', TRUE, '실시간', '단지 세대수, 관리방식, 설비, 주변시설 정보'),
  ('molit_apt_trade', '국토교통부', '아파트 매매 실거래가 자료', 'https://www.data.go.kr/data/15126469/openapi.do', 'transaction', TRUE, '실시간', '법정동 코드와 계약년월 기준 매매 실거래'),
  ('school_location', '한국지방교육행정연구재단', '전국초중등학교위치표준데이터', 'https://www.data.go.kr/data/15021148/standard.do', 'facility', TRUE, '반기', '초중고 위치 데이터'),
  ('hira_hospital', '건강보험심사평가원', '전국 병의원 현황', 'https://www.data.go.kr/data/15051059/fileData.do', 'facility', TRUE, '월간/분기', '병원, 의원, 치과, 한의원 등 의료 접근성 후보'),
  ('hira_pharmacy', '건강보험심사평가원', '전국 약국 현황', 'https://www.data.go.kr/data/15051059/fileData.do', 'facility', TRUE, '월간/분기', '약국 접근성 후보'),
  ('localdata_license', '행정안전부', '지방행정인허가데이터개방', 'https://www.localdata.go.kr/', 'facility', TRUE, '수시', '유흥주점, 단란주점, 체육시설, 노래연습장 등'),
  ('kosis_population', '통계청', 'KOSIS 주민등록인구현황', 'https://kosis.kr', 'demographic', TRUE, '월간', '행정동/연령대별 인구 비율 산출 후보'),
  ('sgis_population', '통계청', 'SGIS 통계지리정보서비스', 'https://sgis.kostat.go.kr/', 'demographic', TRUE, '연간/신청', '소지역/격자 단위 인구 및 공간통계 후보'),
  ('transport_openmarket', '국가교통 데이터 오픈마켓', '국가교통 데이터 오픈마켓', 'https://bigdata-transportation.kr/', 'transport', TRUE, '데이터별 상이', '유동인구, 통행, 대중교통 데이터 후보'),
  ('viewt_ktdb', '한국교통연구원', 'View-T 통행지표 데이터', 'https://viewt.ktdb.go.kr/', 'transport', TRUE, '데이터별 상이', '행정구역/링크 단위 통행지표 후보'),
  ('stcis', '한국교통안전공단', '교통카드 빅데이터 통합정보시스템', 'https://stcis.go.kr/', 'transport', TRUE, '데이터별 상이', '대중교통 이용량, 통행시간, OD 지표 후보');
