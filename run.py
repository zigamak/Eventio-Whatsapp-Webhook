# run.py
import logging
from flask import Flask
from dotenv import load_dotenv
from config import DEBUG, SECRET_KEY
from views import bp

# Load environment variables from .env file
load_dotenv()

# Configure logging to display INFO level messages and above
logging.basicConfig(level=logging.INFO)

def create_app():
    """
    Creates and configures the Flask application.
    This function acts as a factory, which is a good practice for larger apps.
    """
    app = Flask(__name__)

    # Load configuration from a separate config.py file
    app.config['DEBUG'] = DEBUG
    app.config['SECRET_KEY'] = SECRET_KEY

    # Register the main blueprint for the application's routes
    app.register_blueprint(bp)

    return app

# The Flask application instance is created here.
# Gunicorn will look for a callable object named 'app' to run the application.
app = create_app()

# This block is added back for development purposes.
# It allows you to run the file directly without Gunicorn, which is handy
# for local testing and debugging. In a production environment, this block
# will be ignored by Gunicorn.
if __name__ == "__main__":
    logging.info("Flask app started in development mode")
    app.run(host="0.0.0.0", port=8000, debug=True)
