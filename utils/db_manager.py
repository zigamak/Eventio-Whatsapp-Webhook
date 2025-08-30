import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string

    @contextmanager
    def get_connection(self):
        """Get a database connection and ensure it's closed after use."""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query, params=None, fetch=False):
        """Execute a query and optionally fetch results."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                if fetch:
                    return cur.fetchall()
                return None

db_manager = DatabaseManager('postgresql://neondb_owner:npg_SIgb5lKTF3Dz@ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')