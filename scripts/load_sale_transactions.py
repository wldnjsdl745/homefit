"""MOLIT 매매 실거래가 CSV → housing_transactions DB 로딩 스크립트.

사용법:
  pip install pymysql pandas
  python scripts/load_sale_transactions.py --csv data/sale_seoul_2024.csv

MOLIT 다운로드 방법:
  1. https://rtdown.molit.go.kr 접속
  2. 거래유형: 아파트 매매 (또는 연립/다세대 매매)
  3. 지역: 서울특별시 (전체 구 선택)
  4. 기간: 최근 1~2년
  5. CSV 다운로드

CSV 컬럼 (MOLIT 표준):
  시군구, 법정동, 지번, 아파트, 건축년도, 층, 전용면적, 계약년도, 계약월, 계약일, 거래금액(만원), ...
"""

import argparse
import re
import sys
from datetime import date

import pandas as pd
import pymysql

# ── DB 연결 기본값 ───────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "homefit",
    "password": "homefit",
    "database": "homefit",
    "charset": "utf8mb4",
}

# ── MOLIT CSV 컬럼 → DB 컬럼 매핑 ───────────────────────────
# 국토부 실거래가 CSV는 버전마다 헤더가 조금씩 다름.
# 아래는 가장 일반적인 컬럼명 기준.
COL_MAP = {
    "sigungu":      ["시군구", "시군구명"],
    "dong":         ["법정동", "동"],
    "building":     ["아파트", "건물명", "단지명"],
    "built_year":   ["건축년도", "건축년"],
    "floor":        ["층"],
    "area":         ["전용면적", "전용 면적"],
    "year":         ["계약년도", "년"],
    "month":        ["계약월", "월"],
    "day":          ["계약일", "일"],
    "amount":       ["거래금액", "거래금액(만원)"],
    "jibun_main":   ["본번", "지번"],
    "jibun_sub":    ["부번"],
}


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_amount(val) -> int | None:
    if pd.isna(val):
        return None
    cleaned = re.sub(r"[,\s]", "", str(val))
    try:
        return int(cleaned)
    except ValueError:
        return None


def load_csv(csv_path: str, db_config: dict, batch_size: int = 1000) -> None:
    print(f"[load] reading {csv_path}")
    df = pd.read_csv(csv_path, encoding="cp949", dtype=str, low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"[load] rows={len(df)}, cols={list(df.columns)}")

    # 컬럼 매핑
    cols = {k: find_col(df, v) for k, v in COL_MAP.items()}
    missing = [k for k, v in cols.items() if v is None and k in ("sigungu", "amount", "year", "month")]
    if missing:
        print(f"[error] 필수 컬럼 없음: {missing}")
        print(f"  실제 컬럼: {list(df.columns)}")
        sys.exit(1)

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    # regions 캐시 (sigungu + dong → region_id)
    cursor.execute("SELECT id, sigungu, legal_dong_name FROM regions WHERE sido='서울특별시'")
    region_cache: dict[tuple, int] = {}
    for rid, sigungu, dong in cursor.fetchall():
        region_cache[(sigungu.strip(), dong.strip())] = rid

    inserted = skipped = 0
    batch: list[tuple] = []

    for _, row in df.iterrows():
        sigungu = str(row[cols["sigungu"]]).strip() if cols["sigungu"] else ""
        dong = str(row[cols["dong"]]).strip() if cols["dong"] else ""
        amount_manwon = parse_amount(row[cols["amount"]])
        if amount_manwon is None:
            skipped += 1
            continue

        # sigungu에 서울특별시 포함된 경우 파싱
        if "서울특별시" in sigungu:
            parts = sigungu.replace("서울특별시", "").strip().split()
            sigungu = parts[0] if parts else sigungu

        region_id = region_cache.get((sigungu, dong))
        if region_id is None:
            # dong 없이 sigungu만으로 fallback (첫 번째 매칭)
            region_id = next((v for (s, d), v in region_cache.items() if s == sigungu), None)
        if region_id is None:
            skipped += 1
            continue

        year = str(row[cols["year"]]).strip() if cols["year"] else "2024"
        month = str(row[cols["month"]]).strip().zfill(2) if cols["month"] else "01"
        day = str(row[cols["day"]]).strip().zfill(2) if cols["day"] else "01"
        try:
            contract_date = date(int(year), int(month), min(int(day), 28))
        except (ValueError, TypeError):
            contract_date = date(int(year) if year.isdigit() else 2024, 1, 1)

        area = None
        if cols["area"] and not pd.isna(row[cols["area"]]):
            try:
                area = float(str(row[cols["area"]]).replace(",", ""))
            except ValueError:
                pass

        floor_no = None
        if cols["floor"] and not pd.isna(row[cols["floor"]]):
            try:
                floor_no = int(str(row[cols["floor"]]).strip())
            except ValueError:
                pass

        built_year = None
        if cols["built_year"] and not pd.isna(row[cols["built_year"]]):
            try:
                built_year = int(str(row[cols["built_year"]]).strip())
            except ValueError:
                pass

        building = str(row[cols["building"]]).strip() if cols["building"] and not pd.isna(row[cols["building"]]) else None

        batch.append((
            region_id,
            "sale",
            amount_manwon,  # deposit_amount (만원 단위 — BE filter에서 변환)
            None,           # monthly_rent
            contract_date,
            area,
            floor_no,
            building,
            built_year,
        ))

        if len(batch) >= batch_size:
            _insert_batch(cursor, batch)
            conn.commit()
            inserted += len(batch)
            print(f"  inserted {inserted} rows...")
            batch = []

    if batch:
        _insert_batch(cursor, batch)
        conn.commit()
        inserted += len(batch)

    cursor.close()
    conn.close()
    print(f"[done] inserted={inserted}, skipped={skipped}")


def _insert_batch(cursor, batch: list[tuple]) -> None:
    cursor.executemany(
        """
        INSERT INTO housing_transactions
          (region_id, deal_type, deposit_amount, monthly_rent,
           contract_date, rental_area, floor_no, building_name, built_year)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        batch,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOLIT 매매 CSV → DB 로딩")
    parser.add_argument("--csv", required=True, help="MOLIT 다운로드 CSV 파일 경로")
    parser.add_argument("--host", default=DB_CONFIG["host"])
    parser.add_argument("--port", type=int, default=DB_CONFIG["port"])
    parser.add_argument("--user", default=DB_CONFIG["user"])
    parser.add_argument("--password", default=DB_CONFIG["password"])
    parser.add_argument("--database", default=DB_CONFIG["database"])
    args = parser.parse_args()

    cfg = {**DB_CONFIG, "host": args.host, "port": args.port,
           "user": args.user, "password": args.password, "database": args.database}
    load_csv(args.csv, cfg)
