import os
import csv
import logging
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
    )

# ── Target wa_id list ─────────────────────────────────────────────────────────

RAW_IDS = [
    "8055614455", "2348023349149", "2348033224896", "8069182932",
    "8058008469", "8034330353", "809427637", "8036015537",
    "8102212910", "8033338004", "8023080412", "8055740094",
    "8103794369", "8067405013", "8028899019", "8138590077",
    "8032030977", "8053439111", "8105671052", "8081801950",
    "8023096720", "8023210867", "8033259896", "7057141698",
    "2348033099383", "8025017744", "8023349149", "8033430808",
    "8034294960", "9095966116", "8037115736", "8056029065",
    "8035074787", "8022234419", "9117777778", "8137541811",
    "8023128492", "8033065978", "8023080248", "2347034456697",
    "8186780635", "9099156072", "8033076880", "8053815099",
    "8036767678", "8023159077", "8061103506", "8085893830",
    "8056434758", "8034302842", "8032002025", "8036187424",
    "8094000063", "7051399366", "8033075160", "7067341334",
    "8037024916", "7025026000", "8032252298", "8082305428",
    "8061127708", "8023061600", "iobakin71@gmail.com", "7039833358",
    "8036799510", "8132770575", "8035621942", "8023135000",
    "9060004565", "8023015334", "8033116373", "8023151405",
    "8023037251", "7038435946", "8139269177", "8128259498",
    "8062073783", "8023015406", "8037226788", "8034023791",
    "8188557338", "8080358916", "8094556175", "8131333442",
    "9115927038", "8038220248", "8093340011", "7083897480",
    "9099670421", "8035354000", "8083100520", "8038852446",
    "8086239485", "9096851318", "8062136090", "8023251185",
    "8033745448", "8062076127", "8033279495", "7034863734",
    "8032555246", "8033338370", "8025616767", "8032148860",
    "8132363986", "8175102620", "8035859585", "8166350570",
    "8093646473", "8033598153", "8055025834", "8023037318",
    "8023168955", "8027782711", "8127843938", "8034762000",
    "7034532485", "8087595910", "7039278266", "8034063604",
    "8054245204", "9014506823", "8036547901", "8033425882",
    "7088881020", "8034105875", "8052305661", "8068335464",
    "8023125437", "8039127186", "8033804152", "8055069331",
    "7030128958", "8030481331", "8150421256", "8023537740",
    "8186227855", "8132479961", "7081376902", "8033314242",
    "8053262568", "8023014931", "8023311605", "9133884803",
    "8035192117", "8062961968", "8033320255", "8099450095",
    "9016030374", "2348023813905", "8079715690", "8033260246",
    "8064525791", "9167941965", "8035356060", "8023290706",
    "8023294508", "8023017303", "8052044739", "8023256365",
    "8023415001", "8023314205", "8059622051", "8067782718",
    "8033287790", "8064323506", "810025819", "8070890553",
    "8036719456", "9029999196", "2347015212937", "2347013133522",
    "8025370775", "8163423097", "8034274516", "8033064453",
    "8033208183", "8033203047", "8033371555", "8067477933",
    "7082130678", "8033552912", "8166853765", "8078506094",
    "7033243137", "8101058691", "8033082382", "8023234055",
    "9167589756", "2348038220600", "8052466700",
]

# Deduplicate while preserving order
seen = set()
RAW_IDS = [x for x in RAW_IDS if not (x in seen or seen.add(x))]


def build_id_variants(raw_ids):
    variants = set()
    for rid in raw_ids:
        rid = rid.strip()
        variants.add(rid)
        if rid.startswith("234") and len(rid) > 3:
            local = rid[3:]
            variants.add(local)
            variants.add("0" + local)
        if rid.startswith("234"):
            variants.add("+" + rid)
        if len(rid) == 10 and rid[0] in ("7", "8", "9"):
            variants.add("234" + rid)
            variants.add("+234" + rid)
        if len(rid) == 11 and rid.startswith("0"):
            variants.add("234" + rid[1:])
            variants.add("+234" + rid[1:])
    return list(variants)


ALL_VARIANTS = build_id_variants(RAW_IDS)

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
    WHERE wa_id = ANY(%s)
    ORDER BY wa_id ASC, timestamp ASC;
"""

# ── Export ────────────────────────────────────────────────────────────────────

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

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info(
        f"Connecting to database — fetching ALL messages "
        f"for {len(RAW_IDS)} target contacts ({len(ALL_VARIANTS)} wa_id variants) …"
    )

    try:
        conn = get_connection()
    except Exception as e:
        logger.error(f"❌ Could not connect to database: {e}")
        raise

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(QUERY, (ALL_VARIANTS,))
            rows = cur.fetchall()
    finally:
        conn.close()

    matched_ids = set(row['wa_id'] for row in rows)
    logger.info(f"Fetched {len(rows)} message(s) across {len(matched_ids)} unique wa_id(s)")

    if matched_ids:
        logger.info(f"Matched wa_ids: {sorted(matched_ids)}")

    unmatched = [rid for rid in RAW_IDS if not any(
        rid in v or v in rid for v in matched_ids
    )]
    if unmatched:
        logger.warning(f"⚠️  No messages found for {len(unmatched)} requested ID(s): {unmatched}")

    if not rows:
        logger.warning("No messages found at all. Exiting.")
        return

    export_csv(rows, "eventio_messages_filtered.csv")
    logger.info("Done.")


if __name__ == "__main__":
    main()