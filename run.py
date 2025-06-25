import logging
from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started")
    # Run the Flask development server
    # In a production environment, use a WSGI server like Gunicorn or uWSGI
    app.run(host="0.0.0.0", port=8000, debug=True) # debug=True for development to auto-reload