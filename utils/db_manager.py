import psycopg2
import logging
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """A class to manage PostgreSQL database connections and queries."""
    
    def __init__(self, host, port, dbname, user, password, sslmode='require', channel_binding='require'):
        """
        Initialize the DatabaseManager with connection parameters.
        
        Args:
            host (str): Database host.
            port (str): Database port.
            dbname (str): Database name.
            user (str): Database user.
            password (str): Database password.
            sslmode (str): SSL mode (default: 'require').
            channel_binding (str): Channel binding mode (default: 'require').
        """
        self.connection_string = (
            f"host={host} port={port} dbname={dbname} user={user} password={password} "
            f"sslmode={sslmode} channel_binding={channel_binding}"
        )
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        # Verify connectivity once at startup, then let the connection close so
        # Neon can scale its compute to zero while the app is idle.
        self.create_tables_if_not_exists()

    def _new_connection(self):
        """
        Open a fresh short-lived connection with retry logic and return it.

        Connections are intentionally NOT kept open between queries: holding a
        persistent connection keeps Neon's compute awake 24/7. Opening per query
        lets the compute scale to zero during idle periods (the app's normal
        state between bursts of WhatsApp traffic).
        """
        retry_count = 0
        while True:
            try:
                return psycopg2.connect(self.connection_string)
            except psycopg2.Error as e:
                retry_count += 1
                logger.error(f"Failed to connect to database (attempt {retry_count}/{self.max_retries}): {e}")
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to database after {self.max_retries} attempts")
                    raise

    def close(self):
        """No-op kept for backwards compatibility.

        Connections are now short-lived and closed after each query, so there
        is no persistent connection to tear down.
        """
        return

    def execute_query(self, query, params=None, fetch=False):
        """
        Execute a SQL query with optional parameters and retry logic.

        A fresh connection is opened for this call and closed before returning,
        so no connection is held open between queries. This is inherently
        thread-safe (no shared connection/cursor across gunicorn workers).

        Args:
            query (str): SQL query to execute.
            params (tuple): Parameters for the query (optional).
            fetch (bool): Whether to fetch results (default: False).

        Returns:
            list or None: List of results if fetch=True, None otherwise.
        """
        retry_count = 0
        while retry_count < self.max_retries:
            conn = None
            try:
                conn = self._new_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Log the query (be careful with sensitive data)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Executing query: {query[:100]}..." if len(query) > 100 else query)

                cursor.execute(query, params)
                conn.commit()

                if fetch:
                    results = cursor.fetchall()
                    logger.debug(f"Query executed successfully, fetched {len(results)} rows")
                    return results
                else:
                    logger.debug("Query executed successfully")
                    return None

            except psycopg2.Error as e:
                retry_count += 1
                logger.error(f"Database error (attempt {retry_count}/{self.max_retries}): {e}")

                if retry_count < self.max_retries:
                    # Retry only transient connection issues; fail fast otherwise.
                    if any(err_code in str(e) for err_code in ['connection', 'server closed', 'terminated']):
                        logger.info("Connection error detected, retrying...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Non-retryable error: {e}")
                        raise
                else:
                    logger.error(f"Failed to execute query after {self.max_retries} attempts")
                    raise

            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                raise

            finally:
                if conn is not None:
                    conn.close()

    def test_connection(self):
        """Test the database connection with a short-lived connection."""
        try:
            result = self.execute_query("SELECT version()", fetch=True)
            version_str = result[0]['version'] if result else 'Unknown'
            logger.info(f"Database connection test successful. Version: {version_str}")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_table_info(self, table_name, schema='public'):
        """Get information about a table's columns."""
        try:
            query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """
            return self.execute_query(query, (schema, table_name), fetch=True)
        except Exception as e:
            logger.error(f"Error getting table info for {schema}.{table_name}: {e}")
            return []

    def table_exists(self, table_name, schema='public'):
        """Check if a table exists in the specified schema."""
        try:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
            """
            result = self.execute_query(query, (schema, table_name), fetch=True)
            return result[0]['exists']
        except Exception as e:
            logger.error(f"Error checking if table {schema}.{table_name} exists: {e}")
            return False

    def create_tables_if_not_exists(self, schema='public'):
        """Create required tables if they do not exist in the specified schema."""
        tables = [
            {
                'name': 'eventio_messages',
                'schema': """
                    CREATE TABLE {schema}.{name} (
                        id VARCHAR(255) PRIMARY KEY,
                        wa_id VARCHAR(255),
                        name VARCHAR(255),
                        type VARCHAR(50),
                        body TEXT,
                        timestamp TIMESTAMPTZ,
                        direction VARCHAR(50),
                        status VARCHAR(50),
                        read BOOLEAN,
                        image_url TEXT,
                        image_id VARCHAR(255),
                        error_details TEXT,
                        event_id INTEGER,
                        template_name VARCHAR(255)
                    )
                """
            },
            {
                'name': 'package_with_sense_messages',
                'schema': """
                    CREATE TABLE {schema}.{name} (
                        id VARCHAR(255) PRIMARY KEY,
                        wa_id VARCHAR(255),
                        name VARCHAR(255),
                        type VARCHAR(50),
                        body TEXT,
                        timestamp TIMESTAMPTZ,
                        direction VARCHAR(50),
                        status VARCHAR(50),
                        read BOOLEAN,
                        image_url TEXT,
                        image_id VARCHAR(255),
                        error_details TEXT,
                        event_id INTEGER,
                        template_name VARCHAR(255)
                    )
                """
            },
            {
                'name': 'mwsmile_messages',
                'schema': """
                    CREATE TABLE {schema}.{name} (
                        id VARCHAR(255) PRIMARY KEY,
                        wa_id VARCHAR(255),
                        name VARCHAR(255),
                        type VARCHAR(50),
                        body TEXT,
                        timestamp TIMESTAMPTZ,
                        direction VARCHAR(50),
                        status VARCHAR(50),
                        read BOOLEAN,
                        image_url TEXT,
                        image_id VARCHAR(255),
                        error_details TEXT,
                        event_id INTEGER,
                        template_name VARCHAR(255)
                    )
                """
            },
            {
                'name': 'ignitiohub_messages',
                'schema': """
                    CREATE TABLE {schema}.{name} (
                        id VARCHAR(255) PRIMARY KEY,
                        wa_id VARCHAR(255),
                        name VARCHAR(255),
                        type VARCHAR(50),
                        body TEXT,
                        timestamp TIMESTAMPTZ,
                        direction VARCHAR(50),
                        status VARCHAR(50),
                        read BOOLEAN,
                        image_url TEXT,
                        image_id VARCHAR(255),
                        error_details TEXT,
                        event_id INTEGER,
                        template_name VARCHAR(255)
                    )
                """
            }
        ]

        for table in tables:
            table_name = table['name']
            if not self.table_exists(table_name, schema):
                try:
                    query = table['schema'].format(schema=schema, name=table_name)
                    self.execute_query(query)
                    logger.info(f"Created table {schema}.{table_name}")
                except psycopg2.Error as e:
                    logger.error(f"Failed to create table {schema}.{table_name}: {e}")
                    if 'permission denied for schema' in str(e).lower():
                        logger.error(
                            f"Permission denied for schema {schema}. "
                            "Try granting CREATE privileges with: "
                            f"GRANT CREATE ON SCHEMA {schema} TO {self.connection_string.split('user=')[1].split(' ')[0]};"
                        )
                    raise
            else:
                logger.info(f"Table {schema}.{table_name} already exists")

    def insert_message(self, table_name, message_data):
        """
        Insert a message directly into the specified table.

        Args:
            table_name (str): Full table name including schema (e.g., 'public.eventio_messages')
            message_data (dict): Message data with all required fields
        """
        query = f"""
            INSERT INTO {table_name}
            (id, wa_id, name, type, body, timestamp, direction, status, read,
             image_url, image_id, error_details, event_id, template_name, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (id) DO NOTHING
        """
        params = (
            message_data['id'],
            message_data['wa_id'],
            message_data['name'],
            message_data['type'],
            message_data['body'],
            message_data['timestamp'],
            message_data['direction'],
            message_data['status'],
            message_data['read'],
            message_data.get('image_url'),
            message_data.get('image_id'),
            message_data.get('error_details'),
            message_data.get('event_id'),       # None for inbound/unknown
            message_data.get('template_name'),  # None unless set by PHP
        )
        self.execute_query(query, params)
        logger.info(f"✅ Message saved to {table_name}: {message_data['id']}")

    def update_message_status(self, table_name, message_id, status, read, error_details=None):
        """
        Update message status directly in the specified table.

        Args:
            table_name (str): Full table name including schema
            message_id (str): Message ID to update
            status (str): New status
            read (bool): Read status
            error_details (str): Optional Meta error details when status is 'failed'
        """
        query = f"""
            UPDATE {table_name}
            SET status = %s, read = %s, error_details = %s, updated_at = NOW()
            WHERE id = %s
        """
        params = (status, read, error_details, message_id)
        self.execute_query(query, params)
        logger.info(f"✅ Updated message status in {table_name}: {message_id} -> {status}")

    def migrate_add_error_details(self, schema='public'):
        """
        Add error_details column to existing tables if it does not already exist.
        Called automatically on startup so existing deployments are migrated safely.
        """
        tables = ['eventio_messages', 'package_with_sense_messages', 'mwsmile_messages', 'ignitiohub_messages']
        for table in tables:
            try:
                query = f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS error_details TEXT"
                self.execute_query(query)
                logger.info(f"✅ Migration OK — {schema}.{table}.error_details")
            except Exception as e:
                logger.error(f"❌ Migration failed for {schema}.{table}: {e}")

    def migrate_add_event_columns(self, schema='public'):
        """
        Add event_id and template_name columns to existing tables if missing.
        Called automatically on startup — safe to run repeatedly (IF NOT EXISTS).
        """
        tables = ['eventio_messages', 'package_with_sense_messages', 'mwsmile_messages', 'ignitiohub_messages']
        for table in tables:
            try:
                self.execute_query(
                    f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS event_id INTEGER"
                )
                self.execute_query(
                    f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS template_name VARCHAR(255)"
                )
                # Index so per-event queries stay fast even as rows grow
                self.execute_query(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_event_id ON {schema}.{table}(event_id)"
                )
                logger.info(f"✅ Migration OK — {schema}.{table}: event_id, template_name, index")
            except Exception as e:
                logger.error(f"❌ Migration failed for {schema}.{table}: {e}")

    def get_recent_inbound_messages(self, table_name, hours=24):
        """
        Fetch inbound messages from the last `hours` for the given table.

        Args:
            table_name (str): Full table name including schema (e.g., 'public.eventio_messages')
            hours (int): How many hours back to look (default: 24)
        """
        query = f"""
            SELECT id, wa_id, name, body, timestamp
            FROM {table_name}
            WHERE direction = 'inbound' AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
        """
        return self.execute_query(query, (hours,), fetch=True)

    def create_digest_log_table_if_not_exists(self, schema='public'):
        """Create the digest_log claim table used to prevent duplicate daily-digest sends."""
        if not self.table_exists('digest_log', schema):
            self.execute_query(f"""
                CREATE TABLE {schema}.digest_log (
                    run_date DATE PRIMARY KEY,
                    sent_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            logger.info(f"Created table {schema}.digest_log")

    def claim_digest_run(self, run_date, schema='public'):
        """
        Attempt to claim today's digest run. Returns True if this call won the
        claim (i.e. no other process/worker has sent today's digest yet), False
        otherwise. Prevents duplicate sends if multiple gunicorn workers each
        run their own in-process scheduler.
        """
        self.create_digest_log_table_if_not_exists(schema)
        result = self.execute_query(
            f"INSERT INTO {schema}.digest_log (run_date) VALUES (%s) ON CONFLICT DO NOTHING RETURNING run_date",
            (run_date,),
            fetch=True
        )
        return bool(result)

    def release_digest_claim(self, run_date, schema='public'):
        """
        Undo a claim_digest_run() claim after a failed send, so the job can
        be retried the same day instead of being permanently blocked by its
        own failed attempt.
        """
        self.execute_query(f"DELETE FROM {schema}.digest_log WHERE run_date = %s", (run_date,))

    def get_conversation_context(self, table_name, wa_id, limit=10):
        """Recent messages (both directions) for one contact, most recent first."""
        query = f"""
            SELECT direction, body, timestamp
            FROM {table_name}
            WHERE wa_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return self.execute_query(query, (wa_id, limit), fetch=True)

    def create_message_rankings_table_if_not_exists(self, schema='public'):
        """
        Create the message_rankings table if missing. Stores the AI's
        category/score/reason per message, keyed by message_id, so ranking
        work survives a crash/restart mid-batch and reruns can skip messages
        already ranked instead of re-calling the AI for them.
        """
        if not self.table_exists('message_rankings', schema):
            self.execute_query(f"""
                CREATE TABLE {schema}.message_rankings (
                    message_id VARCHAR(255) PRIMARY KEY,
                    wa_id VARCHAR(255),
                    category VARCHAR(50),
                    score INTEGER,
                    reason TEXT,
                    ranked_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            logger.info(f"Created table {schema}.message_rankings")

    def get_existing_rankings(self, message_ids, schema='public'):
        """Returns {message_id: {category, score, reason}} for any ids already ranked."""
        if not message_ids:
            return {}
        self.create_message_rankings_table_if_not_exists(schema)
        query = f"""
            SELECT message_id, category, score, reason
            FROM {schema}.message_rankings
            WHERE message_id = ANY(%s)
        """
        rows = self.execute_query(query, (list(message_ids),), fetch=True)
        return {
            row['message_id']: {
                'category': row['category'],
                'score': row['score'],
                'reason': row['reason'],
            }
            for row in rows
        }

    def upsert_rankings(self, rankings, schema='public'):
        """
        Batch-upsert AI rankings. `rankings` is a list of dicts with keys
        message_id, wa_id, category, score, reason. Persisted immediately
        after each ranked batch so partial progress is never lost.
        """
        if not rankings:
            return
        self.create_message_rankings_table_if_not_exists(schema)
        values_sql = ", ".join(["(%s, %s, %s, %s, %s, NOW())"] * len(rankings))
        params = []
        for r in rankings:
            params.extend([r['message_id'], r['wa_id'], r['category'], r['score'], r['reason']])

        query = f"""
            INSERT INTO {schema}.message_rankings (message_id, wa_id, category, score, reason, ranked_at)
            VALUES {values_sql}
            ON CONFLICT (message_id) DO UPDATE SET
                wa_id = EXCLUDED.wa_id,
                category = EXCLUDED.category,
                score = EXCLUDED.score,
                reason = EXCLUDED.reason,
                ranked_at = NOW()
        """
        self.execute_query(query, tuple(params))

    def migrate_message_rankings_table(self, schema='public'):
        """
        Ensure public.message_rankings exists with all expected columns,
        adding any that are missing (IF NOT EXISTS). Mirrors the other
        migrate_add_* methods so the digest job's storage self-heals on
        startup the same way the message tables do.
        """
        try:
            self.create_message_rankings_table_if_not_exists(schema)
            for column, ddl in [
                ('wa_id', 'VARCHAR(255)'),
                ('category', 'VARCHAR(50)'),
                ('score', 'INTEGER'),
                ('reason', 'TEXT'),
                ('ranked_at', 'TIMESTAMPTZ DEFAULT NOW()'),
            ]:
                self.execute_query(
                    f"ALTER TABLE {schema}.message_rankings ADD COLUMN IF NOT EXISTS {column} {ddl}"
                )
            logger.info(f"✅ Migration OK — {schema}.message_rankings columns")
        except Exception as e:
            logger.error(f"❌ Migration failed for {schema}.message_rankings: {e}")

    def migrate_add_updated_at(self, schema='public'):
        """
        Add updated_at column to existing tables if missing, backfilled from
        timestamp for existing rows. update_message_status() bumps this on
        every status change (sent -> delivered -> read), so pollers can pick
        up status-only changes on already-synced rows by watching updated_at
        instead of timestamp (which never changes after the row is created).
        Called automatically on startup - safe to run repeatedly (IF NOT EXISTS).
        """
        tables = ['eventio_messages', 'package_with_sense_messages', 'mwsmile_messages', 'ignitiohub_messages']
        for table in tables:
            try:
                self.execute_query(
                    f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"
                )
                self.execute_query(
                    f"UPDATE {schema}.{table} SET updated_at = timestamp WHERE updated_at IS NULL"
                )
                self.execute_query(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_updated_at ON {schema}.{table}(updated_at)"
                )
                logger.info(f"✅ Migration OK — {schema}.{table}.updated_at")
            except Exception as e:
                logger.error(f"❌ Migration failed for {schema}.{table}: {e}")

    def __del__(self):
        """Destructor to ensure database connection is closed."""
        try:
            self.close()
        except:
            pass

# Initialize DatabaseManager instance for neondb
try:
    db_manager = DatabaseManager(
        host=os.getenv('DB_HOST', 'ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'neondb'),
        user=os.getenv('DB_USER', 'neondb_owner'),
        password=os.getenv('DB_PASSWORD', 'npg_SIgb5lKTF3Dz'),
        sslmode=os.getenv('DB_SSLMODE', 'require'),
        channel_binding=os.getenv('DB_CHANNEL_BINDING', 'require')
    )
    
    # Test the connection on startup
    if db_manager.test_connection():
        logger.info("✅ Database manager initialized successfully")
        # Migrate existing tables to add missing columns
        db_manager.migrate_add_error_details()
        db_manager.migrate_add_event_columns()
        db_manager.migrate_add_updated_at()
        db_manager.migrate_message_rankings_table()
    else:
        logger.error("❌ Database manager initialization failed - connection test failed")
        
except Exception as e:
    logger.error(f"❌ Failed to initialize database manager: {e}")
    raise