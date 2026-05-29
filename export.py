import os
import csv
from datetime import date, timedelta
from dotenv import load_dotenv

import psycopg2
from psycopg2.extras import RealDictCursor

# ─────────────────────────────────────────────────────────────
# Load Environment Variables
# ─────────────────────────────────────────────────────────────

load_dotenv()

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

# ─────────────────────────────────────────────────────────────
# Database Connection
# ─────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )

# ─────────────────────────────────────────────────────────────
# Query 1 — Messages that FAILED
# ─────────────────────────────────────────────────────────────

QUERY_FAILED = f"""
    SELECT
        id,
        wa_id,
        name,
        type,
        body,
        timestamp,
        direction,
        status,
        error_details,
        template_name,
        event_id
    FROM public.eventio_messages
    WHERE status = 'failed'
      AND timestamp >= '{YESTERDAY}'::timestamp
      AND timestamp < ('{TODAY}'::timestamp + INTERVAL '1 day')
    ORDER BY timestamp ASC;
"""

# ─────────────────────────────────────────────────────────────
# Query 2 — All messages for wa_ids that have duplicate entries
# (same number used more than once — same or different names)
# ─────────────────────────────────────────────────────────────

QUERY_DUPLICATES = f"""
    SELECT
        m.id,
        m.wa_id,
        m.name,
        m.type,
        m.body,
        m.timestamp,
        m.direction,
        m.status,
        m.error_details,
        m.template_name,
        m.event_id,
        dup.total_entries,
        dup.distinct_names,
        dup.all_names
    FROM public.eventio_messages m
    INNER JOIN (
        SELECT
            wa_id,
            COUNT(*)                                        AS total_entries,
            COUNT(DISTINCT name)                            AS distinct_names,
            STRING_AGG(DISTINCT name, ' / ' ORDER BY name) AS all_names
        FROM public.eventio_messages
        GROUP BY wa_id
        HAVING COUNT(*) > 1
    ) dup ON m.wa_id = dup.wa_id
    WHERE m.timestamp >= '{YESTERDAY}'::timestamp
      AND m.timestamp < ('{TODAY}'::timestamp + INTERVAL '1 day')
    ORDER BY m.wa_id, m.timestamp ASC;
"""

# ─────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────

def export_csv(rows, filepath):
    if not rows:
        print(f"  No rows — skipping {filepath}")
        return

    fieldnames = rows[0].keys()
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    print(f"  Exported {len(rows)} rows → {filepath}")

# ─────────────────────────────────────────────────────────────
# Main Function
# ─────────────────────────────────────────────────────────────

def main():
    try:
        conn = get_connection()
        print("Connected to database.")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # --- Failed messages ---
            print("\n[1/2] Fetching failed messages...")
            try:
                cur.execute(QUERY_FAILED)
                failed_rows = cur.fetchall()
            except Exception as e:
                print(f"  Query failed: {e}")
                failed_rows = []

            # --- Duplicate wa_id messages ---
            print("[2/2] Fetching duplicate wa_id messages...")
            try:
                cur.execute(QUERY_DUPLICATES)
                duplicate_rows = cur.fetchall()
            except Exception as e:
                print(f"  Query failed: {e}")
                duplicate_rows = []

    finally:
        conn.close()

    # --- Export ---
    print("\nExporting CSVs...")
    export_csv(failed_rows,    f"failed_messages_{YESTERDAY}_to_{TODAY}.csv")
    export_csv(duplicate_rows, f"duplicate_wa_id_messages_{YESTERDAY}_to_{TODAY}.csv")

    print("\nDone.")

# ─────────────────────────────────────────────────────────────
# Run Script
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()