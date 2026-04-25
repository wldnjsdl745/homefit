CREATE TABLE regions (
                         id BIGINT NOT NULL AUTO_INCREMENT,
                         sido VARCHAR(50) NOT NULL,
                         sigungu_code VARCHAR(10) NOT NULL,
                         sigungu VARCHAR(50) NOT NULL,
                         legal_dong_code VARCHAR(10) NOT NULL,
                         legal_dong_name VARCHAR(50) NOT NULL,
                         created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                         updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

                         CONSTRAINT pk_regions PRIMARY KEY (id),
                         CONSTRAINT uq_regions_sido_sigungu_dong UNIQUE (sido, sigungu_code, legal_dong_code)
);

CREATE TABLE housing_transactions (
                                      id BIGINT NOT NULL AUTO_INCREMENT,
                                      region_id BIGINT NOT NULL,

                                      receipt_year SMALLINT NULL,
                                      deal_type VARCHAR(30) NOT NULL,

                                      deposit_amount BIGINT NULL,
                                      monthly_rent INT NULL,

                                      contract_date DATE NOT NULL,
                                      rental_area DECIMAL(10, 2) NULL,

                                      jibun_type_code VARCHAR(10) NULL,
                                      jibun_type VARCHAR(20) NULL,
                                      main_bun VARCHAR(10) NULL,
                                      sub_bun VARCHAR(10) NULL,
                                      floor_no INT NULL,

                                      building_name VARCHAR(255) NULL,
                                      built_year SMALLINT NULL,
                                      building_usage VARCHAR(50) NULL,

                                      contract_period VARCHAR(50) NULL,
                                      contract_type VARCHAR(50) NULL,
                                      renewal_claim_used VARCHAR(50) NULL,

                                      previous_deposit_amount BIGINT NULL,
                                      previous_monthly_rent INT NULL,

                                      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                                      CONSTRAINT pk_housing_transactions PRIMARY KEY (id),
                                      CONSTRAINT fk_housing_transactions_region
                                          FOREIGN KEY (region_id)
                                              REFERENCES regions (id),

                                      CONSTRAINT chk_housing_transactions_deal_type
                                          CHECK (deal_type IN ('jeonse', 'monthly_rent'))
);

CREATE INDEX idx_housing_transactions_region_id
    ON housing_transactions (region_id);

CREATE INDEX idx_housing_transactions_deal_type
    ON housing_transactions (deal_type);

CREATE INDEX idx_housing_transactions_contract_date
    ON housing_transactions (contract_date);

CREATE INDEX idx_housing_transactions_deal_type_deposit_amount
    ON housing_transactions (deal_type, deposit_amount);

CREATE INDEX idx_housing_transactions_region_id_deal_type
    ON housing_transactions (region_id, deal_type);

CREATE INDEX idx_housing_transactions_region_deal_date
    ON housing_transactions (region_id, deal_type, contract_date);

CREATE TABLE chat_messages (
                               id CHAR(36) NOT NULL,
                               session_id CHAR(36) NOT NULL,
                               raw JSON NOT NULL,
                               conditions JSON NOT NULL,
                               created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                               CONSTRAINT pk_chat_messages PRIMARY KEY (id)
);

CREATE INDEX idx_chat_messages_session_id
    ON chat_messages (session_id);

CREATE INDEX idx_chat_messages_session_id_created_at
    ON chat_messages (session_id, created_at);

CREATE INDEX idx_chat_messages_created_at
    ON chat_messages (created_at);