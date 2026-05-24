"""MOLIT 아파트 매매 실거래가 CSV → housing_transactions DB 로딩 스크립트.

사용법:
  pip install pymysql pandas
  python scripts/load_sale_transactions.py --csv "아파트(매매)_실거래가_20260524170217.csv"

CSV 형식 (국토부 실거래가 공개시스템 기준):
  - 앞 15줄: 메타데이터 (헤더 전 공지/검색조건)
  - 16번째 줄: 컬럼명
  - 컬럼: NO, 시군구, 번지, 본번, 부번, 단지명, 전용면적(㎡),
          계약년월, 계약일, 거래금액(만원), 동, 층, 매수자, 매도자,
          건축년도, 도로명, 해제사유발생일, 거래유형, 중개사소재지, 등기일자
  - 시군구 예시: "서울특별시 성북구 정릉동"
  - 계약년월 예시: "202605"  계약일: "22"
  - 거래금액: "60,000" (만원 단위, 쉼표 포함)
"""

import argparse
import re
import sys
from datetime import date

import pandas as pd
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "homefit",
    "password": "homefit",
    "database": "homefit",
    "charset": "utf8mb4",
}

METADATA_ROWS = 15  # 실제 컬럼 헤더 앞 메타데이터 줄 수


def parse_amount(val) -> int | None:
    if pd.isna(val) or str(val).strip() in ("-", ""):
        return None
    try:
        return int(re.sub(r"[,\s]", "", str(val)))
    except ValueError:
        return None


def parse_int(val) -> int | None:
    if pd.isna(val) or str(val).strip() in ("-", ""):
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def parse_float(val) -> float | None:
    if pd.isna(val) or str(val).strip() in ("-", ""):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return None


def split_address(addr: str) -> tuple[str, str]:
    """'서울특별시 성북구 정릉동' → ('성북구', '정릉동')"""
    parts = str(addr).strip().split()
    # parts[0]=시도, parts[1]=시군구, parts[2:]=동
    sigungu = parts[1] if len(parts) > 1 else ""
    dong = parts[2] if len(parts) > 2 else ""
    return sigungu, dong


def load_csv(csv_path: str, db_config: dict, batch_size: int = 1000) -> None:
    print(f"[load] reading {csv_path}")
    df = pd.read_csv(
        csv_path,
        encoding="cp949",
        skiprows=METADATA_ROWS,
        dtype=str,
        low_memory=False,
    )
    df.columns = df.columns.str.strip()
    print(f"[load] rows={len(df)}, cols={list(df.columns)}")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    # regions 캐시: (sigungu, dong) → region_id
    cursor.execute("SELECT id, sigungu, legal_dong_name FROM regions WHERE sido='서울특별시'")
    region_cache: dict[tuple, int] = {}
    sigungu_cache: dict[str, int] = {}  # sigungu만으로 fallback
    for rid, sigungu, dong in cursor.fetchall():
        region_cache[(sigungu.strip(), dong.strip())] = rid
        if sigungu.strip() not in sigungu_cache:
            sigungu_cache[sigungu.strip()] = rid

    inserted = skipped = 0
    batch: list[tuple] = []

    for _, row in df.iterrows():
        sigungu, dong = split_address(row.get("시군구", ""))
        if not sigungu:
            skipped += 1
            continue

        amount_manwon = parse_amount(row.get("거래금액(만원)"))
        if amount_manwon is None:
            skipped += 1
            continue

        region_id = region_cache.get((sigungu, dong)) or sigungu_cache.get(sigungu)
        if region_id is None:
            skipped += 1
            continue

        # 계약년월: "202605" → year=2026, month=05
        yyyymm = str(row.get("계약년월", "")).strip()
        try:
            year = int(yyyymm[:4])
            month = int(yyyymm[4:6])
            day = min(parse_int(row.get("계약일")) or 1, 28)
            contract_date = date(year, month, day)
        except (ValueError, TypeError):
            skipped += 1
            continue

        batch.append((
            region_id,
            "sale",
            None,          # deposit_amount (매매는 null)
            amount_manwon, # sale_price_amount
            None,          # monthly_rent
            contract_date,
            parse_float(row.get("전용면적(㎡)")),
            parse_int(row.get("층")),
            str(row.get("단지명", "")).strip() or None,
            parse_int(row.get("건축년도")),
            str(row.get("본번", "")).strip() or None,
            str(row.get("부번", "")).strip() or None,
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
          (region_id, deal_type, deposit_amount, sale_price_amount, monthly_rent,
           contract_date, rental_area, floor_no, building_name, built_year,
           main_bun, sub_bun)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
