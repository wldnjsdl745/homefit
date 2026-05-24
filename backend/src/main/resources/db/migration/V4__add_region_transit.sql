CREATE TABLE IF NOT EXISTS region_transit (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sigungu VARCHAR(20) NOT NULL,
    subway_count INT NOT NULL DEFAULT 0,
    transit_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_region_transit PRIMARY KEY (id),
    CONSTRAINT uq_region_transit_sigungu UNIQUE (sigungu)
);
