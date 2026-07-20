import os
import re
import csv
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# ─── All phone numbers provided ───────────────────────────────
RAW_NUMBERS = """
8033313027
8037136953
8037227117
8137311160
8120917799
8037724035
8120820865
8178686453
8064845654
8060202056
8033552880
8118194942
8183420743
8036963560
9050764004
8029486123
9030314592
8032675513
8094003730
8138491839
8033184345
8023033488
8023452944
8023439350
8023211420
8060520028
9162732543
8036089305
8132889768
8033025273
9060511508
8054779514
8033173611
8052001978
8023117747
8038732486
8036880278
0812 5588827
"""

# ─── Extract last 8 digits, skip non-numeric entries ──────────
def last8(raw):
    digits = re.sub(r'\D', '', raw)
    return digits[-8:] if len(digits) >= 8 else None

suffixes = sorted(set(
    s for s in (last8(n) for n in RAW_NUMBERS.strip().splitlines() if n.strip())
    if s is not None
))
print(f"Unique last-8-digit suffixes: {len(suffixes)}")

# ─── Build SQL (all entries, no date filter) ──────────────────
suffix_conditions = " OR ".join(f"wa_id LIKE '%{s}'" for s in suffixes)

query = f"""
    SELECT
        id,
        wa_id,
        name,
        type,
        body,
        timestamp,
        DATE(timestamp) AS message_date,
        direction,
        status,
        read
    FROM public.package_with_sense_messages
    WHERE ({suffix_conditions})
      AND timestamp >= '2025-06-08'
    ORDER BY
        wa_id ASC,
        timestamp ASC;
"""

# ─── Connect & fetch ──────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )

def ordinal(n):
    suffix = {1:"st",2:"nd",3:"rd"}.get(n % 10 if not 11 <= n % 100 <= 13 else 0, "th")
    return f"{n}{suffix}"

def format_ts(ts):
    if ts is None: return ""
    if isinstance(ts, str):
        try: ts = datetime.fromisoformat(ts)
        except: return ts
    if isinstance(ts, datetime):
        return f"{ordinal(ts.day)} {ts.strftime('%B, %Y')} {ts.strftime('%I:%M %p').lstrip('0')}"
    from datetime import date
    if isinstance(ts, date):
        return f"{ordinal(ts.day)} {ts.strftime('%B, %Y')}"
    return str(ts)

try:
    conn = get_connection()
    print("✅ Connected to database.")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    conn.close()
    print(f"✅ Fetched {len(rows)} rows.")
except Exception as e:
    print(f"❌ Error: {e}")
    rows = []

# ─── Export CSV ───────────────────────────────────────────────
if rows:
    filename = f"messages_pws_all.csv"
    fieldnames = ["wa_id","name","message_date","type","body","direction","status","read"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            r = dict(row)
            r["message_date"] = format_ts(r.get("message_date"))
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"✅ Saved to {filename}")
else:
    print("No rows found.")