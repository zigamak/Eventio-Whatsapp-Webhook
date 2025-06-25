# APP/config.py
# This file contains configuration variables for your Flask application.
# IMPORTANT: For production, use environment variables instead of hardcoding sensitive data.

# WhatsApp Business API Configuration
WHATAPP_ACCESS_TOKEN = "EAAateL6gXUMBO2WjUHFt3LSI812aQ69vX5MwzdtAnrb3NBB04VIQ6JtHqO6VrOUNmdUxsODf3kzt2ZBOZBNBtUZAHRA2fWhMAr8MOrcUFe8Y5VNLZAUYx0be4uwPRQgZBCz8xSoIrfwM57k7rj1DPoe1qDukEXJqE2zuGaHyjSHDY3CZAlGZA9Six4nehOaG12u4AZDZD" # Replace with your WhatsApp Business API access token
VERIFY_TOKEN = "123456"         # Replace with your chosen webhook verify token
PHONE_NUMBER_ID = "608867502309431"   # Replace with your WhatsApp Business Account phone number ID
RECIPIENT_WAID = "2348055614455"  # Replace with a default recipient WA ID for testing (optional)
VERSION = "v19.0"                           # WhatsApp API version (e.g., v19.0)

# Facebook App Details (Optional, primarily for webhook setup)
APP_ID = "YOUR_FACEBOOK_APP_ID"             # Replace with your Facebook App ID
APP_SECRET = "YOUR_FACEBOOK_APP_SECRET"     # Replace with your Facebook App Secret
WEBHOOK_URL = "YOUR_WEBHOOK_URL"            # Replace with your public webhook URL (e.g., ngrok URL)

# Flask Application Settings
DEBUG = True # Set to False in production
SECRET_KEY = "supersecretkey" # Replace with a strong, randomly generated key in production