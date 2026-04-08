import os
import csv
import json
import logging
from datetime import date
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'neondb'),
        user=os.getenv('DB_USER', 'neondb_owner'),
        password=os.getenv('DB_PASSWORD', 'npg_SIgb5lKTF3Dz'),
        sslmode=os.getenv('DB_SSLMODE', 'require'),
        # channel_binding is NOT supported by Neon's pooler — omit it here
    )

# ── Date range ────────────────────────────────────────────────────────────────

START_DATE = date(2026, 3, 1)
END_DATE   = date(2026, 3, 1)

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
        read,
        image_url,
        image_id
    FROM public.eventio_messages
    WHERE timestamp::date BETWEEN %s AND %s
    ORDER BY timestamp ASC;
"""

# ── Export helpers ────────────────────────────────────────────────────────────

def export_csv(rows, filepath):
    if not rows:
        logger.warning("No rows to export — CSV will not be created.")
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    logger.info(f"✅ CSV exported → {filepath}  ({len(rows)} rows)")


def export_json(rows, filepath):
    if not rows:
        logger.warning("No rows to export — JSON will not be created.")
        return
    data = []
    for row in rows:
        d = dict(row)
        if hasattr(d.get('timestamp'), 'isoformat'):
            d['timestamp'] = d['timestamp'].isoformat()
        data.append(d)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ JSON exported → {filepath}  ({len(rows)} rows)")


def export_conversations_txt(rows, filepath):
    """
    Groups messages by wa_id and writes a human-readable conversation
    transcript, showing the date alongside each message timestamp.
    """
    if not rows:
        logger.warning("No rows to export — TXT will not be created.")
        return

    conversations: dict[str, list] = {}
    for row in rows:
        key = row['wa_id'] or 'unknown'
        conversations.setdefault(key, []).append(dict(row))

    date_range_str = (
        f"{START_DATE.strftime('%d %B %Y')} – {END_DATE.strftime('%d %B %Y')}"
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"Eventio Messages — {date_range_str}\n")
        f.write("=" * 60 + "\n\n")

        for wa_id, messages in conversations.items():
            contact_name = messages[0].get('name') or wa_id
            f.write(f"Conversation with: {contact_name}  ({wa_id})\n")
            f.write("-" * 60 + "\n")

            for msg in messages:
                ts = msg['timestamp']
                ts_str = ts.strftime('%d %b %H:%M:%S') if hasattr(ts, 'strftime') else str(ts)
                direction = (msg.get('direction') or '').upper()
                body = msg.get('body') or ''
                msg_type = msg.get('type', 'text')

                if msg_type == 'image':
                    body = f"[IMAGE] {msg.get('image_url') or msg.get('image_id') or ''}"

                arrow = '→' if direction == 'OUTBOUND' else '←'
                f.write(f"  [{ts_str}] {arrow} {body}\n")

            f.write("\n")

    logger.info(f"✅ Conversation transcript exported → {filepath}  ({len(conversations)} conversations)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info(
        f"Connecting to database and fetching eventio_messages "
        f"from {START_DATE} to {END_DATE} …"
    )

    try:
        conn = get_connection()
    except Exception as e:
        logger.error(f"❌ Could not connect to database: {e}")
        raise

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(QUERY, (START_DATE, END_DATE))
            rows = cur.fetchall()
    finally:
        conn.close()

    logger.info(f"Fetched {len(rows)} message(s) between {START_DATE} and {END_DATE}")

    if not rows:
        logger.warning(f"No messages found between {START_DATE} and {END_DATE}. Exiting.")
        return

    # Output filenames reflect the full range
    range_str = f"{START_DATE.strftime('%Y-%m-%d')}_to_{END_DATE.strftime('%Y-%m-%d')}"
    csv_path  = f"eventio_messages_{range_str}.csv"
    json_path = f"eventio_messages_{range_str}.json"
    txt_path  = f"eventio_conversations_{range_str}.txt"

    export_csv(rows, csv_path)
    export_json(rows, json_path)
    export_conversations_txt(rows, txt_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()