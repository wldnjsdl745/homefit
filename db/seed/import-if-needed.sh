#!/bin/sh
set -eu

DB_HOST="${MYSQL_HOST:-db}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_NAME="${MYSQL_DATABASE:-homefit}"
DB_USER="${MYSQL_USER:-homefit}"
DB_PASSWORD="${MYSQL_PASSWORD:-homefit}"
SEED_DIR="${SEED_DIR:-/seed}"
SEED_FILE="${SEED_FILE:-}"
FORCE_SEED_IMPORT="${FORCE_SEED_IMPORT:-false}"
MAX_ATTEMPTS="${SEED_WAIT_ATTEMPTS:-60}"

force_import=false
case "$FORCE_SEED_IMPORT" in
  1|true|TRUE|yes|YES)
    force_import=true
    ;;
esac

mysql_cmd() {
  mysql \
    -h"$DB_HOST" \
    -P"$DB_PORT" \
    -u"$DB_USER" \
    -p"$DB_PASSWORD" \
    "$DB_NAME" \
    "$@"
}

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  if mysql_cmd -Nse "select 1;" >/dev/null 2>/dev/null; then
    break
  fi

  echo "Waiting for database connection... ($attempt/$MAX_ATTEMPTS)"
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$attempt" -gt "$MAX_ATTEMPTS" ]; then
  echo "Database was not ready."
  exit 1
fi

table_exists="$(mysql_cmd -Nse "select count(*) from information_schema.tables where table_schema = database() and table_name = 'housing_transactions';")"
if [ "$table_exists" -gt 0 ]; then
  transaction_count="$(mysql_cmd -Nse "select count(*) from housing_transactions;")"
else
  transaction_count=0
fi

if [ "$transaction_count" -gt 0 ] && [ "$force_import" != "true" ]; then
  echo "Seed import skipped. housing_transactions already has $transaction_count rows."
  exit 0
fi

if [ "$transaction_count" -gt 0 ]; then
  echo "Force seed import enabled. Existing seed tables will be truncated before import."
fi

if [ -n "$SEED_FILE" ]; then
  seed_path="$SEED_FILE"
elif [ -f "$SEED_DIR/seed-data.sql.gz" ]; then
  seed_path="$SEED_DIR/seed-data.sql.gz"
elif [ -f "$SEED_DIR/seed-data.sql" ]; then
  seed_path="$SEED_DIR/seed-data.sql"
else
  echo "Seed data not found."
  echo "Place seed-data.sql.gz or seed-data.sql in db/seed, then run docker compose up again."
  exit 1
fi

if [ "$table_exists" -gt 0 ] && [ "$force_import" = "true" ]; then
  echo "Preparing empty seed tables before import..."
  mysql_cmd -e "set foreign_key_checks=0; truncate table housing_transactions; truncate table regions; set foreign_key_checks=1;"
fi

echo "Importing seed data from $seed_path..."
case "$seed_path" in
  *.gz)
    gzip -dc "$seed_path" | mysql_cmd
    ;;
  *)
    mysql_cmd < "$seed_path"
    ;;
esac

mysql_cmd -e "select count(*) as regions from regions; select count(*) as housing_transactions from housing_transactions;"
echo "Seed import completed."
