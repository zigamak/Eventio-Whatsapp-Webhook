import logging
import os
from flask import Flask
from dotenv import load_dotenv

# Import your blueprint from the views module
from views import bp

# Load environment variables from the .env file
load_dotenv()

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def create_app():
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__)
    
    # Get configuration values from environment variables
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # Ensure SECRET_KEY is set
    if not app.config['SECRET_KEY'] or app.config['SECRET_KEY'] == 'your-secret-key-here':
        logging.warning("SECRET_KEY environment variable is not set. Using default (not recommended for production).")

    # Register the blueprint
    app.register_blueprint(bp)
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    # Get host and port from environment variables, with defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 8000))
    
    logging.info(f"Starting Flask app on {host}:{port}")
    
    # Run the application
    app.run(host=host, port=port)