"""공모전/공공데이터 기반 아파트 추천 데이터 적재 도구.

이 스크립트는 공공데이터포털, LOCALDATA, KOSIS/SGIS 등에서 내려받은 CSV를
Homefit 추천용 테이블에 적재한다. API 키가 필요한 데이터는 먼저 포털에서 CSV로
내려받은 뒤 이 스크립트에 넘긴다.

예시:
  python scripts/load_recommendation_data.py complexes --csv kapt_complexes.csv
  python scripts/load_recommendation_data.py facilities --type school --csv schools.csv
  python scripts/load_recommendation_data.py facilities --type nightlife --csv localdata_nightlife.csv
  python scripts/load_recommendation_data.py demographics --csv population.csv
  python scripts/load_recommendation_data.py features
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path
from typing import Iterable

import pymysql


DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "homefit",
    "password": "homefit",
    "database": "homefit",
    "charset": "utf8mb4",
    "autocommit": False,
}

FACILITY_TYPES = {
    "school",
    "hospital",
    "pharmacy",
    "gym",
    "nightlife",
    "transit",
    "commercial",
    "other",
}


def detect_encoding(path: Path) -> str:
    data = path.read_bytes()[:65536]
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "utf-8-sig"


def iter_csv(path: Path) -> Iterable[dict[str, str]]:
    encoding = detect_encoding(path)
    with path.open(newline="", encoding=encoding) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            yield {normalize_header(k): (v or "").strip() for k, v in row.items() if k is not None}


def normalize_header(value: str) -> str:
    return value.replace("\ufeff", "").strip()


def read_value(row: dict[str, str], *names: str, contains: tuple[str, ...] = ()) -> str | None:
    for name in names:
        if name in row and row[name] != "":
            return row[name]

    for key, value in row.items():
        if value == "":
            continue
        if any(fragment in key for fragment in contains):
            return value

    return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = re.sub(r"[,\s]", "", value)
    if text in ("", "-"):
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.replace(",", "").strip()
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_year(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19|20)\d{2}", value)
    return int(match.group(0)) if match else None


def parse_reference_month(value: str | None) -> str:
    if value is None:
        return "000000"
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 6:
        return digits[:6]
    if len(digits) == 4:
        return f"{digits}01"
    return "000000"


def split_region(address: str | None) -> tuple[str | None, str | None, str | None]:
    if not address:
        return None, None, None
    parts = address.split()
    if len(parts) < 2:
        return None, None, None
    sido = parts[0]
    sigungu = parts[1]
    dong = parts[2] if len(parts) > 2 and parts[2].endswith(("동", "가", "읍", "면", "리")) else None
    return sido, sigungu, dong


def parse_wgs84(row: dict[str, str]) -> tuple[float | None, float | None]:
    lat = parse_float(read_value(row, "위도", "lat", "latitude", "LAT", "Latitude"))
    lng = parse_float(read_value(row, "경도", "lng", "lon", "longitude", "LNG", "Longitude"))

    # LOCALDATA 일부 파일의 좌표정보(x/y)는 EPSG:5174 계열이다. 변환 없이 WGS84로 쓰지 않는다.
    if lat is not None and lng is not None and 32 <= lat <= 39 and 124 <= lng <= 132:
        return lat, lng
    return None, None


def external_id_for(row: dict[str, str], name: str, address: str | None) -> str:
    explicit = read_value(
        row,
        "kaptCode",
        "KAPT_CODE",
        "단지코드",
        "아파트코드",
        "관리번호",
        "학교ID",
        "상가업소번호",
        "번호",
        "id",
    )
    if explicit:
        return explicit[:120]
    base = f"{name}|{address or ''}"
    return re.sub(r"\s+", " ", base).strip()[:120]


def connect(args: argparse.Namespace):
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=False,
    )


def load_complexes(args: argparse.Namespace) -> None:
    rows = inserted = skipped = 0
    conn = connect(args)
    try:
        with conn.cursor() as cursor:
            for row in iter_csv(Path(args.csv)):
                rows += 1
                name = read_value(row, "단지명", "kaptName", "아파트명", "공동주택명", "name")
                road_address = read_value(row, "도로명주소", "소재지도로명주소", "road_address")
                lot_address = read_value(row, "법정동주소", "소재지지번주소", "지번주소", "lot_address")
                address = road_address or lot_address
                sido, sigungu, dong = (
                    read_value(row, "시도", "시도명"),
                    read_value(row, "시군구", "시군구명"),
                    read_value(row, "법정동", "법정동명"),
                )
                if not (sido and sigungu):
                    sido, sigungu, dong_from_address = split_region(address)
                    dong = dong or dong_from_address

                if not (name and sido and sigungu):
                    skipped += 1
                    continue

                lat, lng = parse_wgs84(row)
                external_id = external_id_for(row, name, address)
                cursor.execute(
                    """
                    INSERT INTO apartment_complexes (
                      source_key, external_id, name, sido, sigungu, legal_dong_name,
                      road_address, lot_address, lat, lng, household_count, built_year,
                      parking_count, heating_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      name=VALUES(name),
                      sido=VALUES(sido),
                      sigungu=VALUES(sigungu),
                      legal_dong_name=VALUES(legal_dong_name),
                      road_address=VALUES(road_address),
                      lot_address=VALUES(lot_address),
                      lat=VALUES(lat),
                      lng=VALUES(lng),
                      household_count=VALUES(household_count),
                      built_year=VALUES(built_year),
                      parking_count=VALUES(parking_count),
                      heating_type=VALUES(heating_type)
                    """,
                    (
                        args.source_key,
                        external_id,
                        name,
                        sido,
                        sigungu,
                        dong,
                        road_address,
                        lot_address,
                        lat,
                        lng,
                        parse_int(read_value(row, "세대수", "호수", "household_count")),
                        parse_year(read_value(row, "사용승인일", "준공일", "건축년도", "built_year")),
                        parse_int(read_value(row, "주차대수", "parking_count")),
                        read_value(row, "난방방식", "heating_type"),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[complexes] rows={rows}, upserted={inserted}, skipped={skipped}")


def load_facilities(args: argparse.Namespace) -> None:
    if args.type not in FACILITY_TYPES:
        raise SystemExit(f"--type must be one of {sorted(FACILITY_TYPES)}")

    rows = inserted = skipped = no_wgs84 = 0
    conn = connect(args)
    try:
        with conn.cursor() as cursor:
            for row in iter_csv(Path(args.csv)):
                rows += 1
                name = read_value(row, "학교명", "사업장명", "업소명", "시설명", "요양기관명", "상호명", "name")
                road_address = read_value(row, "소재지도로명주소", "도로명주소", "road_address")
                lot_address = read_value(row, "소재지지번주소", "지번주소", "주소", "lot_address")
                address = road_address or lot_address
                sido, sigungu, dong = (
                    read_value(row, "시도", "시도명"),
                    read_value(row, "시군구", "시군구명"),
                    read_value(row, "법정동", "법정동명"),
                )
                if not (sido and sigungu):
                    sido, sigungu, dong_from_address = split_region(address)
                    dong = dong or dong_from_address

                if not name:
                    skipped += 1
                    continue

                lat, lng = parse_wgs84(row)
                if lat is None or lng is None:
                    no_wgs84 += 1

                subtype = args.subtype or read_value(
                    row,
                    "학교급구분",
                    "업태구분명",
                    "상세영업상태명",
                    "종별코드명",
                    "분류",
                    "subtype",
                )
                status = read_value(row, "운영상태", "영업상태명", "상세영업상태명", "상태", "status")
                cursor.execute(
                    """
                    INSERT INTO nearby_facilities (
                      source_key, facility_type, subtype, name, sido, sigungu, legal_dong_name,
                      road_address, lot_address, lat, lng, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        args.source_key,
                        args.type,
                        subtype,
                        name,
                        sido,
                        sigungu,
                        dong,
                        road_address,
                        lot_address,
                        lat,
                        lng,
                        status,
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()

    print(
        f"[facilities:{args.type}] rows={rows}, inserted={inserted}, "
        f"skipped={skipped}, missing_wgs84={no_wgs84}"
    )
    if no_wgs84:
        print("[warn] WGS84 위경도가 없는 행은 거리 기반 feature 계산에서 제외됩니다.")


def load_demographics(args: argparse.Namespace) -> None:
    rows = inserted = skipped = 0
    conn = connect(args)
    try:
        with conn.cursor() as cursor:
            for row in iter_csv(Path(args.csv)):
                rows += 1
                sido = read_value(row, "시도", "시도명")
                sigungu = read_value(row, "시군구", "시군구명")
                admin_dong = read_value(row, "행정동", "행정동명", "읍면동", "읍면동명")
                legal_dong = read_value(row, "법정동", "법정동명")
                if not (sido and sigungu):
                    sido, sigungu, dong_from_address = split_region(read_value(row, "주소"))
                    admin_dong = admin_dong or dong_from_address

                total = parse_int(read_value(row, "총인구", "총인구수", "계", "population_total"))
                child = parse_int(read_value(row, "유소년인구", "0-14세", "0~14세", "child_count"))
                youth = parse_int(read_value(row, "청년인구", "20-39세", "20~39세", "youth_count"))
                senior = parse_int(read_value(row, "고령인구", "65세이상", "65세 이상", "senior_count"))

                child_ratio = parse_float(read_value(row, "child_ratio", "유소년비율"))
                youth_ratio = parse_float(read_value(row, "youth_ratio", "청년비율"))
                senior_ratio = parse_float(read_value(row, "senior_ratio", "고령인구비율"))
                if total and total > 0:
                    child_ratio = child_ratio if child_ratio is not None else (child or 0) / total
                    youth_ratio = youth_ratio if youth_ratio is not None else (youth or 0) / total
                    senior_ratio = senior_ratio if senior_ratio is not None else (senior or 0) / total

                if not (sido and sigungu and (admin_dong or legal_dong)):
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO neighborhood_demographics (
                      source_key, sido, sigungu, admin_dong_name, legal_dong_name,
                      reference_month, population_total, child_ratio, youth_ratio,
                      senior_ratio, household_count
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      population_total=VALUES(population_total),
                      child_ratio=VALUES(child_ratio),
                      youth_ratio=VALUES(youth_ratio),
                      senior_ratio=VALUES(senior_ratio),
                      household_count=VALUES(household_count)
                    """,
                    (
                        args.source_key,
                        sido,
                        sigungu,
                        admin_dong,
                        legal_dong,
                        parse_reference_month(read_value(row, "기준월", "기준년월", "reference_month")),
                        total,
                        child_ratio,
                        youth_ratio,
                        senior_ratio,
                        parse_int(read_value(row, "세대수", "household_count")),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[demographics] rows={rows}, upserted={inserted}, skipped={skipped}")


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def score_cap(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def compute_features(args: argparse.Namespace) -> None:
    conn = connect(args)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, sido, sigungu, legal_dong_name, lat, lng
                FROM apartment_complexes
                WHERE lat IS NOT NULL AND lng IS NOT NULL
                """
            )
            complexes = cursor.fetchall()

            cursor.execute(
                """
                SELECT facility_type, subtype, lat, lng
                FROM nearby_facilities
                WHERE lat IS NOT NULL AND lng IS NOT NULL
                """
            )
            facilities = cursor.fetchall()

            cursor.execute(
                """
                SELECT sido, sigungu, admin_dong_name, legal_dong_name, child_ratio, youth_ratio, senior_ratio
                FROM neighborhood_demographics
                ORDER BY reference_month DESC
                """
            )
            demographics_rows = cursor.fetchall()

            demographics = {}
            for row in demographics_rows:
                for dong_key in (row["legal_dong_name"], row["admin_dong_name"], None):
                    key = (row["sido"], row["sigungu"], dong_key)
                    demographics.setdefault(key, row)

            updated = 0
            for complex_row in complexes:
                lat = float(complex_row["lat"])
                lng = float(complex_row["lng"])
                counts = {
                    "school_500": 0,
                    "hospital_1000": 0,
                    "pharmacy_1000": 0,
                    "gym_1000": 0,
                    "nightlife_500": 0,
                    "transit_1000": 0,
                }
                elementary_distance = None

                for facility in facilities:
                    dist = haversine_m(lat, lng, float(facility["lat"]), float(facility["lng"]))
                    ftype = facility["facility_type"]
                    subtype = facility["subtype"] or ""

                    if ftype == "school" and dist <= 500:
                        counts["school_500"] += 1
                    if ftype == "school" and "초" in subtype:
                        elementary_distance = min(elementary_distance or dist, dist)
                    if ftype == "hospital" and dist <= 1000:
                        counts["hospital_1000"] += 1
                    if ftype == "pharmacy" and dist <= 1000:
                        counts["pharmacy_1000"] += 1
                    if ftype == "gym" and dist <= 1000:
                        counts["gym_1000"] += 1
                    if ftype == "nightlife" and dist <= 500:
                        counts["nightlife_500"] += 1
                    if ftype == "transit" and dist <= 1000:
                        counts["transit_1000"] += 1

                demo = (
                    demographics.get((complex_row["sido"], complex_row["sigungu"], complex_row["legal_dong_name"]))
                    or demographics.get((complex_row["sido"], complex_row["sigungu"], None))
                    or {}
                )
                child_ratio = demo.get("child_ratio")
                youth_ratio = demo.get("youth_ratio")
                senior_ratio = demo.get("senior_ratio")

                school_score = score_cap(
                    counts["school_500"] * 25
                    + (50 - min(elementary_distance or 1000, 1000) / 20)
                )
                medical_score = score_cap(counts["hospital_1000"] * 15 + counts["pharmacy_1000"] * 10)
                lifestyle_score = score_cap(counts["gym_1000"] * 20 + counts["transit_1000"] * 10)
                quiet_score = score_cap(100 - counts["nightlife_500"] * 15)
                demographic_score = score_cap((float(child_ratio or 0) + float(youth_ratio or 0)) * 100)

                cursor.execute(
                    """
                    INSERT INTO complex_feature_scores (
                      complex_id, school_count_500m, elementary_distance_m,
                      hospital_count_1000m, pharmacy_count_1000m, gym_count_1000m,
                      nightlife_count_500m, transit_count_1000m, child_ratio,
                      youth_ratio, senior_ratio, school_score, medical_score,
                      lifestyle_score, quiet_score, demographic_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      school_count_500m=VALUES(school_count_500m),
                      elementary_distance_m=VALUES(elementary_distance_m),
                      hospital_count_1000m=VALUES(hospital_count_1000m),
                      pharmacy_count_1000m=VALUES(pharmacy_count_1000m),
                      gym_count_1000m=VALUES(gym_count_1000m),
                      nightlife_count_500m=VALUES(nightlife_count_500m),
                      transit_count_1000m=VALUES(transit_count_1000m),
                      child_ratio=VALUES(child_ratio),
                      youth_ratio=VALUES(youth_ratio),
                      senior_ratio=VALUES(senior_ratio),
                      school_score=VALUES(school_score),
                      medical_score=VALUES(medical_score),
                      lifestyle_score=VALUES(lifestyle_score),
                      quiet_score=VALUES(quiet_score),
                      demographic_score=VALUES(demographic_score)
                    """,
                    (
                        complex_row["id"],
                        counts["school_500"],
                        int(elementary_distance) if elementary_distance is not None else None,
                        counts["hospital_1000"],
                        counts["pharmacy_1000"],
                        counts["gym_1000"],
                        counts["nightlife_500"],
                        counts["transit_1000"],
                        child_ratio,
                        youth_ratio,
                        senior_ratio,
                        school_score,
                        medical_score,
                        lifestyle_score,
                        quiet_score,
                        demographic_score,
                    ),
                )
                updated += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[features] updated_complexes={updated}")


def add_db_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=DB_CONFIG["host"])
    parser.add_argument("--port", type=int, default=DB_CONFIG["port"])
    parser.add_argument("--user", default=DB_CONFIG["user"])
    parser.add_argument("--password", default=DB_CONFIG["password"])
    parser.add_argument("--database", default=DB_CONFIG["database"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Homefit 추천 데이터 적재")
    subparsers = parser.add_subparsers(dest="command", required=True)

    complexes = subparsers.add_parser("complexes", help="공동주택 단지 master CSV 적재")
    add_db_args(complexes)
    complexes.add_argument("--csv", required=True)
    complexes.add_argument("--source-key", default="molit_kapt_basic")
    complexes.set_defaults(func=load_complexes)

    facilities = subparsers.add_parser("facilities", help="학교/병원/체육/유흥 등 시설 CSV 적재")
    add_db_args(facilities)
    facilities.add_argument("--csv", required=True)
    facilities.add_argument("--type", required=True, choices=sorted(FACILITY_TYPES))
    facilities.add_argument("--source-key", default="localdata_license")
    facilities.add_argument("--subtype")
    facilities.set_defaults(func=load_facilities)

    demographics = subparsers.add_parser("demographics", help="행정동/법정동 연령층 CSV 적재")
    add_db_args(demographics)
    demographics.add_argument("--csv", required=True)
    demographics.add_argument("--source-key", default="kosis_population")
    demographics.set_defaults(func=load_demographics)

    features = subparsers.add_parser("features", help="단지별 주변 feature score 재계산")
    add_db_args(features)
    features.set_defaults(func=compute_features)

    args = parser.parse_args()
    try:
        args.func(args)
    except pymysql.MySQLError as exc:
        print(f"[db-error] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
