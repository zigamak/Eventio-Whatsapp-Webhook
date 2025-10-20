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
        self.conn = None
        self.cursor = None
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.connect()
        self.create_tables_if_not_exists()

    def connect(self):
        """Establish a connection to the database with retry logic."""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                if self.conn:
                    self.close()
                
                self.conn = psycopg2.connect(self.connection_string)
                self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                logger.info(f"Successfully connected to database: {self.connection_string.split('dbname=')[1].split(' ')[0]}")
                return
                
            except psycopg2.Error as e:
                retry_count += 1
                logger.error(f"Failed to connect to database (attempt {retry_count}/{self.max_retries}): {e}")
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to database after {self.max_retries} attempts")
                    raise

    def _ensure_connection(self):
        """Ensure the database connection is active."""
        try:
            if not self.conn or self.conn.closed:
                logger.info("Connection is closed, reconnecting...")
                self.connect()
            else:
                # Test the connection
                self.cursor.execute("SELECT 1")
                self.conn.commit()
        except psycopg2.Error:
            logger.info("Connection test failed, reconnecting...")
            self.connect()

    def close(self):
        """Close the database connection and cursor."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.conn:
                self.conn.close()
                self.conn = None
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def execute_query(self, query, params=None, fetch=False):
        """
        Execute a SQL query with optional parameters and retry logic.
        
        Args:
            query (str): SQL query to execute.
            params (tuple): Parameters for the query (optional).
            fetch (bool): Whether to fetch results (default: False).
        
        Returns:
            list or None: List of results if fetch=True, None otherwise.
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self._ensure_connection()
                
                # Log the query (be careful with sensitive data)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Executing query: {query[:100]}..." if len(query) > 100 else query)
                
                self.cursor.execute(query, params)
                self.conn.commit()
                
                if fetch:
                    results = self.cursor.fetchall()
                    logger.debug(f"Query executed successfully, fetched {len(results)} rows")
                    return results
                else:
                    logger.debug("Query executed successfully")
                    return None
                    
            except psycopg2.Error as e:
                retry_count += 1
                error_msg = f"Database error (attempt {retry_count}/{self.max_retries}): {e}"
                logger.error(error_msg)
                
                if retry_count < self.max_retries:
                    # Check if it's a connection issue that we can retry
                    if any(err_code in str(e) for err_code in ['connection', 'server closed', 'terminated']):
                        logger.info("Connection error detected, retrying...")
                        time.sleep(self.retry_delay)
                        try:
                            self.conn.rollback()
                        except:
                            pass
                        self.connect()
                    else:
                        # Non-retryable error, don't retry
                        logger.error(f"Non-retryable error: {e}")
                        try:
                            self.conn.rollback()
                        except:
                            pass
                        raise
                else:
                    logger.error(f"Failed to execute query after {self.max_retries} attempts")
                    try:
                        self.conn.rollback()
                    except:
                        pass
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                try:
                    if self.conn:
                        self.conn.rollback()
                except:
                    pass
                raise

    def test_connection(self):
        """Test the database connection."""
        try:
            self._ensure_connection()
            self.cursor.execute("SELECT version()")
            version = self.cursor.fetchone()
            # RealDictCursor returns a dictionary, not a tuple
            version_str = version['version'] if version else 'Unknown'
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
                        image_id VARCHAR(255)
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
                        image_id VARCHAR(255)
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
                        image_id VARCHAR(255)
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
            (id, wa_id, name, type, body, timestamp, direction, status, read, image_url, image_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            message_data.get('image_id')
        )
        self.execute_query(query, params)
        logger.info(f"✅ Message saved to {table_name}: {message_data['id']}")

    def update_message_status(self, table_name, message_id, status, read):
        """
        Update message status directly in the specified table.
        
        Args:
            table_name (str): Full table name including schema
            message_id (str): Message ID to update
            status (str): New status
            read (bool): Read status
        """
        query = f"""
            UPDATE {table_name}
            SET status = %s, read = %s
            WHERE id = %s
        """
        params = (status, read, message_id)
        self.execute_query(query, params)
        logger.info(f"✅ Updated message status in {table_name}: {message_id} -> {status}")

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
    else:
        logger.error("❌ Database manager initialization failed - connection test failed")
        
except Exception as e:
    logger.error(f"❌ Failed to initialize database manager: {e}")
    raise