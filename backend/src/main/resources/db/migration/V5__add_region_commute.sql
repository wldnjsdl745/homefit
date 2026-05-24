CREATE TABLE IF NOT EXISTS region_commute (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sigungu VARCHAR(20) NOT NULL,
    destination_key VARCHAR(30) NOT NULL,
    avg_minutes INT NOT NULL,

    CONSTRAINT pk_region_commute PRIMARY KEY (id),
    CONSTRAINT uq_region_commute_sigungu_destination UNIQUE (sigungu, destination_key)
);
