import logging
import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from the .env file FIRST before any other imports
load_dotenv()

# Import your blueprint from the views module
from views import bp

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def validate_env():
    """Log all critical env vars at startup so misconfigurations are immediately visible."""
    vars_to_check = [
        "SECRET_KEY",
        "VERIFY_TOKEN",
        "EVENTIO_ACCESS_TOKEN",
        "ACCOUNT1_PHONE_ID_EVENTIO",
        "PACKAGE_ACCESS_TOKEN",
        "ACCOUNT1_PHONE_ID_PACKAGE",
        "ACCOUNT2_ACCESS_TOKEN",
        "ACCOUNT2_PHONE_ID",
        "GEMINI_API_KEY",
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]
    logging.info("=" * 60)
    logging.info("STARTUP ENV VAR CHECK")
    logging.info("=" * 60)
    all_ok = True
    for var in vars_to_check:
        val = os.getenv(var)
        if val:
            # Show first 6 chars only for secrets
            preview = val[:6] + "..." if len(val) > 6 else val
            logging.info(f"  ✅ {var} = {preview}")
        else:
            logging.error(f"  ❌ {var} is NOT SET")
            all_ok = False
    logging.info("=" * 60)
    if all_ok:
        logging.info("✅ All env vars present")
    else:
        logging.error("❌ Some env vars are missing — check above")
    logging.info("=" * 60)


def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)

    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    if not app.config['SECRET_KEY']:
        logging.error("SECRET_KEY environment variable is not set. This is a security risk.")

    app.register_blueprint(bp)

    return app


# Validate env vars before anything else runs
validate_env()

# Create the application instance
app = create_app()

if __name__ == "__main__":
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 8000))

    logging.info(f"Starting Flask app on {host}:{port}")
    app.run(host=host, port=port)