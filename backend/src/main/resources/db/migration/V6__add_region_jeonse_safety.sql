-- 구별 전세 안전도 (주택도시보증공사 보증사고율 기반)
-- safety_grade: A(사고율 0.5% 미만) / B(0.5%~2%) / C(2% 이상)
CREATE TABLE region_jeonse_safety (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    sigungu        VARCHAR(50)   NOT NULL UNIQUE COMMENT '서울 구 이름 (regions.sigungu 참조)',
    accident_rate  DECIMAL(6, 4) NOT NULL COMMENT '전세사고율 (0.0000 ~ 1.0000)',
    safety_grade   CHAR(1)       NOT NULL COMMENT 'A / B / C',
    reference_date DATE          NOT NULL COMMENT '기준 연월 (해당 월 1일)',
    CONSTRAINT chk_region_jeonse_safety_grade
        CHECK (safety_grade IN ('A', 'B', 'C'))
);

CREATE INDEX idx_region_jeonse_safety_sigungu ON region_jeonse_safety (sigungu);
