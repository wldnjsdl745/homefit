-- 구 → 주요 목적지 대중교통 통근 시간 (GTFS 최단경로 사전 계산)
-- destination_key: gangnam | yeouido | gwanghwamun | hongdae | jamsil
CREATE TABLE region_commute (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    sigungu         VARCHAR(50)  NOT NULL COMMENT '서울 구 이름 (regions.sigungu 참조)',
    destination_key VARCHAR(30)  NOT NULL COMMENT '목적지 키',
    avg_minutes     INT          NOT NULL COMMENT '대중교통 평균 통근 시간(분)',
    CONSTRAINT uq_region_commute_sigungu_dest UNIQUE (sigungu, destination_key),
    CONSTRAINT chk_region_commute_dest
        CHECK (destination_key IN ('gangnam', 'yeouido', 'gwanghwamun', 'hongdae', 'jamsil'))
);

CREATE INDEX idx_region_commute_sigungu ON region_commute (sigungu);
CREATE INDEX idx_region_commute_dest    ON region_commute (destination_key);
