import psycopg2
import logging
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def test_database_connection():
    try:
        # Attempt to connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=DB_SSLMODE
        )
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result[0] == 1:
            logging.info("Database connection successful: SELECT 1 returned %s", result)
        else:
            logging.error("Database connection test failed: unexpected result %s", result)
            return False

        # Check if package_with_sense_messages table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'package_with_sense_messages'
            );
        """)
        table_exists = cursor.fetchone()[0]
        if table_exists:
            logging.info("Table package_with_sense_messages exists")
            # Check for sample data
            cursor.execute("SELECT COUNT(*) FROM package_with_sense_messages WHERE wa_id = %s", ('2348055614455',))
            message_count = cursor.fetchone()[0]
            logging.info("Found %s messages for wa_id 2348055614455", message_count)
        else:
            logging.warning("Table package_with_sense_messages does not exist")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logging.error("Database connection test failed: %s - %s", e.pgcode, e.pgerror)
        return False
    except Exception as e:
        logging.error("Database connection test failed: %s", str(e))
        return False

if __name__ == "__main__":
    logging.info("Testing database connection...")
    if test_database_connection():
        logging.info("Database connection test passed")
    else:
        logging.error("Database connection test failed")