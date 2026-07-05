import os
import csv
import re
from datetime import date
from dotenv import load_dotenv

import psycopg2
from psycopg2.extras import RealDictCursor

# ─────────────────────────────────────────────────────────────
# Load Environment Variables
# ─────────────────────────────────────────────────────────────

load_dotenv()

START_DATE = "2026-06-01"
END_DATE = date.today().isoformat()

# ─────────────────────────────────────────────────────────────
# Phone number list
# Matching is done using the LAST 10 DIGITS
# ─────────────────────────────────────────────────────────────

RAW_NUMBERS = """
"""

# Normalize phone numbers and keep the last 10 digits
PHONE_SUFFIXES = sorted({
    re.sub(r"\D", "", number.strip())[-10:]
    for number in RAW_NUMBERS.splitlines()
    if number.strip() and number.strip().lower() != "phone"
})

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
# Query
# Messages for supplied phone numbers
# From June 1, 2026 until today
# ─────────────────────────────────────────────────────────────

QUERY = """
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
WHERE
    RIGHT(wa_id, 10) = ANY(%s)
    AND timestamp::date BETWEEN %s AND %s
ORDER BY wa_id, timestamp ASC;
"""

# ─────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────

def export_csv(rows, filepath):
    if not rows:
        print(f"No rows found. Skipping {filepath}")
        return

    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows to {filepath}")

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print(f"Loaded {len(PHONE_SUFFIXES)} unique phone numbers.")
    print(f"Date Range: {START_DATE} → {END_DATE}")

    try:
        conn = get_connection()
        print("Connected to database.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("Fetching messages...")
            cur.execute(
                QUERY,
                (
                    PHONE_SUFFIXES,
                    START_DATE,
                    END_DATE,
                ),
            )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Query failed: {e}")
        rows = []
    finally:
        conn.close()

    export_csv(rows, "messages_june_1_2026_to_today.csv")
    print("Done.")

# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()