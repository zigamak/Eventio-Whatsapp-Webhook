import os

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "EAAateL6gXUMBO2WjUHFt3LSI812aQ69vX5MwzdtAnrb3NBB04VIQ6JtHqO6VrOUNmdUxsODf3kzt2ZBOZBNBtUZAHRA2fWhMAr8MOrcUFe8Y5VNLZAUYx0be4uwPRQgZBCz8xSoIrfwM57k7rj1DPoe1qDukEXJqE2zuGaHyjSHDY3CZAlGZA9Six4nehOaG12u4AZDZD")  # Replace with your actual token
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "123456")  # Ensure this matches the token set in Meta's dashboard
EVENTIO_PHONE_ID = os.getenv("EVENTIO_PHONE_ID", "608867502309431")  # Eventio phone number ID
PACKAGE_WITH_SENSE_PHONE_ID = os.getenv("PACKAGE_WITH_SENSE_PHONE_ID", "630482473482641")  # Package with Sense phone number ID
RECIPIENT_WAID = os.getenv("RECIPIENT_WAID", "2348055614455")
VERSION = "v19.0"

# Facebook App Details
APP_ID = os.getenv("APP_ID", "YOUR_FACEBOOK_APP_ID")
APP_SECRET = os.getenv("APP_SECRET", "YOUR_FACEBOOK_APP_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://great-enjoyed-piglet.ngrok-free.app/webhook")  # Your ngrok webhook URL

# Flask Application Settings
DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "$%#^37286")