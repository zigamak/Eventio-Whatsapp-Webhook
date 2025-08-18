# run.py
import logging
from flask import Flask
from dotenv import load_dotenv
from config import DEBUG, SECRET_KEY
from views import bp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config['DEBUG'] = DEBUG
    app.config['SECRET_KEY'] = SECRET_KEY

    # Register blueprints
    app.register_blueprint(bp)

    return app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started")
    app.run(host="0.0.0.0", port=8000, debug=True)