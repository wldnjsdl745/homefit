-- 서울 25개 구 → 5개 주요 목적지 대중교통 평균 통근 시간 (분)
-- 기준: 구 내 주요 지점 → 목적지 역까지 대중교통 최단 경로 평균
-- gangnam=강남역, yeouido=여의도역, gwanghwamun=광화문역, hongdae=홍대입구역, jamsil=잠실역
INSERT INTO region_commute (sigungu, destination_key, avg_minutes) VALUES
  -- 강남구
  ('강남구', 'gangnam',     8), ('강남구', 'yeouido',    30), ('강남구', 'gwanghwamun', 32), ('강남구', 'hongdae',    38), ('강남구', 'jamsil',    20),
  -- 서초구
  ('서초구', 'gangnam',    12), ('서초구', 'yeouido',    25), ('서초구', 'gwanghwamun', 35), ('서초구', 'hongdae',    40), ('서초구', 'jamsil',    28),
  -- 송파구
  ('송파구', 'gangnam',    20), ('송파구', 'yeouido',    35), ('송파구', 'gwanghwamun', 40), ('송파구', 'hongdae',    45), ('송파구', 'jamsil',     8),
  -- 강동구
  ('강동구', 'gangnam',    28), ('강동구', 'yeouido',    42), ('강동구', 'gwanghwamun', 45), ('강동구', 'hongdae',    50), ('강동구', 'jamsil',    15),
  -- 광진구
  ('광진구', 'gangnam',    25), ('광진구', 'yeouido',    32), ('광진구', 'gwanghwamun', 28), ('광진구', 'hongdae',    33), ('광진구', 'jamsil',    18),
  -- 성동구
  ('성동구', 'gangnam',    22), ('성동구', 'yeouido',    28), ('성동구', 'gwanghwamun', 22), ('성동구', 'hongdae',    30), ('성동구', 'jamsil',    25),
  -- 용산구
  ('용산구', 'gangnam',    18), ('용산구', 'yeouido',    15), ('용산구', 'gwanghwamun', 20), ('용산구', 'hongdae',    22), ('용산구', 'jamsil',    35),
  -- 동작구
  ('동작구', 'gangnam',    18), ('동작구', 'yeouido',    18), ('동작구', 'gwanghwamun', 32), ('동작구', 'hongdae',    28), ('동작구', 'jamsil',    32),
  -- 관악구
  ('관악구', 'gangnam',    22), ('관악구', 'yeouido',    25), ('관악구', 'gwanghwamun', 35), ('관악구', 'hongdae',    32), ('관악구', 'jamsil',    38),
  -- 영등포구
  ('영등포구', 'gangnam',  28), ('영등포구', 'yeouido',   7), ('영등포구', 'gwanghwamun', 25), ('영등포구', 'hongdae',  18), ('영등포구', 'jamsil',  40),
  -- 양천구
  ('양천구', 'gangnam',    38), ('양천구', 'yeouido',    25), ('양천구', 'gwanghwamun', 35), ('양천구', 'hongdae',    30), ('양천구', 'jamsil',    47),
  -- 강서구
  ('강서구', 'gangnam',    43), ('강서구', 'yeouido',    20), ('강서구', 'gwanghwamun', 38), ('강서구', 'hongdae',    22), ('강서구', 'jamsil',    52),
  -- 구로구
  ('구로구', 'gangnam',    32), ('구로구', 'yeouido',    20), ('구로구', 'gwanghwamun', 30), ('구로구', 'hongdae',    28), ('구로구', 'jamsil',    43),
  -- 금천구
  ('금천구', 'gangnam',    33), ('금천구', 'yeouido',    28), ('금천구', 'gwanghwamun', 35), ('금천구', 'hongdae',    33), ('금천구', 'jamsil',    47),
  -- 마포구
  ('마포구', 'gangnam',    33), ('마포구', 'yeouido',    12), ('마포구', 'gwanghwamun', 18), ('마포구', 'hongdae',     8), ('마포구', 'jamsil',    42),
  -- 서대문구
  ('서대문구', 'gangnam',  38), ('서대문구', 'yeouido',  22), ('서대문구', 'gwanghwamun', 20), ('서대문구', 'hongdae',  15), ('서대문구', 'jamsil',  48),
  -- 은평구
  ('은평구', 'gangnam',    52), ('은평구', 'yeouido',    35), ('은평구', 'gwanghwamun', 28), ('은평구', 'hongdae',    18), ('은평구', 'jamsil',    55),
  -- 종로구
  ('종로구', 'gangnam',    30), ('종로구', 'yeouido',    25), ('종로구', 'gwanghwamun',  7), ('종로구', 'hongdae',    22), ('종로구', 'jamsil',    35),
  -- 중구
  ('중구', 'gangnam',      28), ('중구', 'yeouido',      20), ('중구', 'gwanghwamun',   10), ('중구', 'hongdae',      25), ('중구', 'jamsil',      33),
  -- 성북구
  ('성북구', 'gangnam',    47), ('성북구', 'yeouido',    43), ('성북구', 'gwanghwamun', 35), ('성북구', 'hongdae',    37), ('성북구', 'jamsil',    38),
  -- 강북구
  ('강북구', 'gangnam',    53), ('강북구', 'yeouido',    47), ('강북구', 'gwanghwamun', 38), ('강북구', 'hongdae',    40), ('강북구', 'jamsil',    43),
  -- 도봉구
  ('도봉구', 'gangnam',    57), ('도봉구', 'yeouido',    52), ('도봉구', 'gwanghwamun', 45), ('도봉구', 'hongdae',    47), ('도봉구', 'jamsil',    47),
  -- 노원구
  ('노원구', 'gangnam',    52), ('노원구', 'yeouido',    48), ('노원구', 'gwanghwamun', 42), ('노원구', 'hongdae',    43), ('노원구', 'jamsil',    40),
  -- 중랑구
  ('중랑구', 'gangnam',    42), ('중랑구', 'yeouido',    40), ('중랑구', 'gwanghwamun', 35), ('중랑구', 'hongdae',    40), ('중랑구', 'jamsil',    28),
  -- 동대문구
  ('동대문구', 'gangnam',  35), ('동대문구', 'yeouido',  33), ('동대문구', 'gwanghwamun', 20), ('동대문구', 'hongdae',  28), ('동대문구', 'jamsil',  28);
