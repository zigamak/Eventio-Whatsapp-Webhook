import os
from dotenv import load_dotenv

load_dotenv()

# Shared webhook configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://eventio-whatsapp-webhook-kroi.onrender.com")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "123456")
VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")  # WhatsApp API version

# Account 1 configuration (Eventio and Package with Sense)
ACCOUNT1_ACCESS_TOKEN = os.getenv("ACCOUNT1_ACCESS_TOKEN")
ACCOUNT1_PHONE_ID_EVENTIO = os.getenv("ACCOUNT1_PHONE_ID_EVENTIO")
ACCOUNT1_PHONE_ID_PACKAGE = os.getenv("ACCOUNT1_PHONE_ID_PACKAGE")

# Account 2 configuration (Ignitio Hub)
ACCOUNT2_ACCESS_TOKEN = os.getenv("ACCOUNT2_ACCESS_TOKEN")
ACCOUNT2_PHONE_ID = os.getenv("ACCOUNT2_PHONE_ID")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "ep-quiet-mud-ad433srr-pooler.c-2.us-east-1.aws.neon.tech")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "neondb")
DB_USER = os.getenv("DB_USER", "neondb_owner")
DB_PASSWORD = os.getenv("DB_PASSWORD", "npg_SIgb5lKTF3Dz")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
DB_CHANNEL_BINDING = os.getenv("DB_CHANNEL_BINDING", "require")
