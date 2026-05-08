import os
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'neondb'),
        user=os.getenv('DB_USER', 'neondb_owner'),
        password=os.getenv('DB_PASSWORD', 'npg_SIgb5lKTF3Dz'),
        sslmode=os.getenv('DB_SSLMODE', 'require'),
    )

def main():
    logger.info("Connecting to database …")
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM public.ignitiohub_messages
                ORDER BY timestamp DESC
                LIMIT 10;
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning("No rows found in ignitiohub_messages.")
        return

    logger.info(f"Last {len(rows)} messages (newest first):\n")
    for i, row in enumerate(rows, 1):
        print(f"--- Message {i} ---")
        for key, value in row.items():
            print(f"  {key}: {value}")
        print()

if __name__ == "__main__":
    main()