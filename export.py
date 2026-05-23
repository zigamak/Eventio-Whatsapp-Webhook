import os
import csv
import logging
from dotenv import load_dotenv

import psycopg2
from psycopg2.extras import RealDictCursor

# ─────────────────────────────────────────────────────────────
# Load Environment Variables
# ─────────────────────────────────────────────────────────────

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

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
# SQL Query
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
        CASE
            WHEN direction = 'inbound'  THEN 'Inbound'
            WHEN direction = 'outbound' THEN 'Outbound'
            ELSE 'Unknown'
        END AS direction_label,
        status,
        read,
        image_url,
        image_id
    FROM public.eventio_messages
    WHERE timestamp >= '2026-05-21'
    ORDER BY timestamp ASC;
"""

# ─────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────

def export_csv(rows, filepath):
    if not rows:
        logger.warning("No rows found to export.")
        return

    fieldnames = rows[0].keys()

    with open(filepath, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    logger.info(f"✅ CSV exported successfully → {filepath}")

# ─────────────────────────────────────────────────────────────
# Main Function
# ─────────────────────────────────────────────────────────────

def main():
    logger.info("Connecting to database...")

    try:
        conn = get_connection()
        logger.info("✅ Database connection successful")

    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            logger.info("Fetching eventio messages from 20th May 2026 onwards...")

            cur.execute(QUERY)
            rows = cur.fetchall()

            logger.info(f"✅ Retrieved {len(rows)} message(s)")

    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        return

    finally:
        conn.close()
        logger.info("Database connection closed.")

    if not rows:
        logger.warning("No messages found from 20th May 2026 onwards.")
        return

    filename = "eventio_messages_from_2026-05-21.csv"

    export_csv(rows, filename)

    logger.info("🎉 Done.")

# ─────────────────────────────────────────────────────────────
# Run Script
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()