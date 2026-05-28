-- 구별 지하철 접근성 지표 (GTFS 파싱 결과)
-- sigungu 는 regions.sigungu 와 동일한 값 (ex: '관악구')
CREATE TABLE region_transit (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    sigungu       VARCHAR(50)   NOT NULL UNIQUE COMMENT '서울 구 이름 (regions.sigungu 참조)',
    subway_count  INT           NOT NULL DEFAULT 0 COMMENT '구 내 지하철역 수',
    transit_score DECIMAL(5, 2) NOT NULL DEFAULT 0.00 COMMENT '접근성 점수 0-100 (subway_count 정규화)',
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_region_transit_sigungu ON region_transit (sigungu);
