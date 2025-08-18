import logging
from flask import Flask
import os

def create_app():
    """
    Factory function to create and configure the Flask application.
    Sets up configuration, logging, and registers blueprints.
    """
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # Load configuration from config.py.
    app.config.from_pyfile('config.py', silent=True)

    # Override config with environment variables if they exist.
    app.config["WHATAPP_ACCESS_TOKEN"] = os.environ.get("WHATAPP_ACCESS_TOKEN", app.config.get("WHATAPP_ACCESS_TOKEN"))
    app.config["VERIFY_TOKEN"] = os.environ.get("VERIFY_TOKEN", app.config.get("VERIFY_TOKEN"))
    app.config["PHONE_NUMBER_ID"] = os.environ.get("PHONE_NUMBER_ID", app.config.get("PHONE_NUMBER_ID"))
    app.config["RECIPIENT_WAID"] = os.environ.get("RECIPIENT_WAID", app.config.get("RECIPIENT_WAID"))
    app.config["VERSION"] = os.environ.get("VERSION", app.config.get("VERSION"))
    app.config["APP_ID"] = os.environ.get("APP_ID", app.config.get("APP_ID"))
    app.config["APP_SECRET"] = os.environ.get("APP_SECRET", app.config.get("APP_SECRET"))
    app.config["WEBHOOK_URL"] = os.environ.get("WEBHOOK_URL", app.config.get("WEBHOOK_URL"))
    
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.urandom(24)

    # --- MODIFICATION START ---
    # Configure logging to output to the console (stdout/stderr)
    # Removing 'filename' and 'filemode' directs logs to the console by default.
    logging.basicConfig(
        level=logging.INFO, # Set minimum logging level to INFO
        format="%(asctime)s - %(levelname)s - %(message)s" # Log format
        # filename and filemode are removed to log to console
    )
    # --- MODIFICATION END ---

    # Import and register blueprints
    from .views import webhook_blueprint, portal_blueprint
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(portal_blueprint)

    return app
