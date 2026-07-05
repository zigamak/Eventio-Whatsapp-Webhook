import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )

QUERY = """
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      table_name ILIKE '%conversation%'
      OR table_name ILIKE '%message%'
      OR table_name ILIKE '%chat%'
      OR table_name ILIKE '%whatsapp%'
      OR table_name ILIKE '%wa%'
  )
ORDER BY table_name, ordinal_position;
"""

def main():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(QUERY)
        rows = cur.fetchall()

    conn.close()

    current_table = None

    for table, column, data_type, nullable in rows:
        if table != current_table:
            current_table = table
            print(f"\n{'='*60}")
            print(f"TABLE: {table}")
            print(f"{'='*60}")

        print(f"{column:<30} {data_type:<25} Nullable: {nullable}")

if __name__ == "__main__":
    main()