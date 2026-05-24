CREATE TABLE IF NOT EXISTS region_jeonse_safety (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sigungu VARCHAR(20) NOT NULL,
    accident_rate DECIMAL(6, 4) NOT NULL,
    safety_grade CHAR(1) NOT NULL,
    reference_date DATE NOT NULL,

    CONSTRAINT pk_region_jeonse_safety PRIMARY KEY (id),
    CONSTRAINT uq_region_jeonse_safety_sigungu UNIQUE (sigungu)
);
