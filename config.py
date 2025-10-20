import os

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
EVENTIO_PHONE_ID = os.getenv("EVENTIO_PHONE_ID")
PACKAGE_WITH_SENSE_PHONE_ID = os.getenv("PACKAGE_WITH_SENSE_PHONE_ID")
IGNITIO_PHONE_ID = os.getenv("IGNITIO_PHONE_ID")
IGNITIO_TOKEN = os.getenv("IGNITIO_TOKEN")
RECIPIENT_WAID = os.getenv("RECIPIENT_WAID")
VERSION = os.getenv("VERSION", "v19.0")

# Facebook App Details
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Flask Application Settings
DEBUG = os.getenv("FLASK_DEBUG") == "True"