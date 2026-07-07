import os
from dotenv import load_dotenv

load_dotenv()

# Shared webhook configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://eventio-whatsapp-webhook-kroi.onrender.com")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "123456")
VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")  # WhatsApp API version

# Eventio configuration
EVENTIO_ACCESS_TOKEN = os.getenv("EVENTIO_ACCESS_TOKEN")
ACCOUNT1_PHONE_ID_EVENTIO = os.getenv("ACCOUNT1_PHONE_ID_EVENTIO")

# Package with Sense configuration
PACKAGE_ACCESS_TOKEN = os.getenv("PACKAGE_ACCESS_TOKEN")
ACCOUNT1_PHONE_ID_PACKAGE = os.getenv("ACCOUNT1_PHONE_ID_PACKAGE")

# MWsmile configuration (shares PACKAGE_ACCESS_TOKEN)
ACCOUNT1_PHONE_ID_MWSMILE = os.getenv("ACCOUNT1_PHONE_ID_MWSMILE")

# Ignitio Hub configuration
ACCOUNT2_ACCESS_TOKEN = os.getenv("ACCOUNT2_ACCESS_TOKEN")
ACCOUNT2_PHONE_ID = os.getenv("ACCOUNT2_PHONE_ID")

# Gemini AI configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "neondb")
DB_USER = os.getenv("DB_USER", "neondb_owner")
DB_PASSWORD = os.getenv("DB_PASSWORD", "npg_SIgb5lKTF3Dz")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
DB_CHANNEL_BINDING = os.getenv("DB_CHANNEL_BINDING", "require")

# Daily inbox digest configuration
DIGEST_RECIPIENT_EMAIL = os.getenv("DIGEST_RECIPIENT_EMAIL")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SECURE = os.getenv("SMTP_SECURE", "tls")  # "ssl" (implicit TLS, e.g. port 465) or "tls" (STARTTLS, e.g. port 587)
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Eventio")
DIGEST_HOUR_UTC = os.getenv("DIGEST_HOUR_UTC", "6")
DIGEST_SECRET = os.getenv("DIGEST_SECRET")