# Eventio WhatsApp Webhook

A Flask application that receives and sends WhatsApp messages for three businesses via the Meta Business API, persisting all messages to PostgreSQL (Neon).

## Running the app

```bash
python run.py
# or in production
gunicorn run:app
```

Default port: `8000`. Override with `FLASK_PORT` env var.

## Project structure

```
run.py                      # Entry point — creates Flask app, registers blueprint, validates env
config.py                   # Loads all env vars from .env
views.py                    # All Flask routes (webhook + portal + chat API)
utils/
  db_manager.py             # DatabaseManager class + global db_manager singleton
  whatsapp_utils.py         # WhatsApp API helpers, PHONE_ID_TO_TABLE map, message processing
  ai_responder.py           # Gemini AI auto-reply (currently disabled — returns None)
decorators/
  security.py               # Webhook HMAC signature validation (currently disabled for dev)
__init__.py                 # Legacy factory create_app() — superseded by run.py
```

## Three phone IDs → three DB tables

The core routing concept: every phone ID maps to a dedicated table.

| Config var | Table |
|---|---|
| `ACCOUNT1_PHONE_ID_EVENTIO` | `public.eventio_messages` |
| `ACCOUNT1_PHONE_ID_PACKAGE` | `public.package_with_sense_messages` |
| `ACCOUNT2_PHONE_ID` | `public.ignitiohub_messages` |

Mapping lives in `utils/whatsapp_utils.py:PHONE_ID_TO_TABLE`. Each phone ID also has its own access token in `PHONE_ID_TO_TOKEN`.

## Database schema (all three tables identical)

```sql
id            VARCHAR(255) PRIMARY KEY   -- WhatsApp message ID
wa_id         VARCHAR(255)               -- sender/recipient WhatsApp number
name          VARCHAR(255)               -- contact display name
type          VARCHAR(50)                -- 'text' | 'image' | 'template'
body          TEXT                       -- message text or image caption
timestamp     TIMESTAMPTZ
direction     VARCHAR(50)                -- 'inbound' | 'outbound'
status        VARCHAR(50)                -- 'delivered' | 'sent' | 'read' | 'failed'
read          BOOLEAN
image_url     TEXT                       -- local /static/uploads/... path
image_id      VARCHAR(255)               -- WhatsApp media ID
error_details TEXT                       -- populated on Meta delivery failure
```

Tables are auto-created on startup by `DatabaseManager.create_tables_if_not_exists()`. The `error_details` column is added via migration if missing (`migrate_add_error_details()`).

## API routes

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/webhook` | Meta webhook (verification + inbound messages/statuses) |
| GET | `/` | Package with Sense portal (`index.html`) |
| GET | `/eventio` | Eventio portal (`eventio.html`) |
| GET | `/ignitiohub` | Ignitio Hub portal (`ignitiohub.html`) |
| GET | `/messages/<phone_id>` | Raw message list for a phone ID |
| GET | `/api/chats?phone_id=` | Chats grouped by wa_id with unread counts |
| GET | `/api/chats/<wa_id>?phone_id=` | All messages for one conversation |
| POST | `/api/mark-read` | Mark inbound messages as read |
| POST | `/api/respond` | Send outbound text reply and save to DB |
| POST | `/api/send-image` | Upload image, send via API, save to DB |
| POST | `/api/log-outbound` | Log outbound message sent by Apps Script/PHP |
| GET | `/get_image/<image_id>/<phone_id>` | Download image from WhatsApp media API |
| POST | `/send_message` | Generic send (text or image) |

## Required environment variables

```
# Flask
SECRET_KEY
FLASK_DEBUG          # optional, default False
FLASK_PORT           # optional, default 8000

# Webhook
VERIFY_TOKEN

# Eventio (Meta Business Account 1a)
EVENTIO_ACCESS_TOKEN
ACCOUNT1_PHONE_ID_EVENTIO

# Package with Sense (Meta Business Account 1b)
PACKAGE_ACCESS_TOKEN
ACCOUNT1_PHONE_ID_PACKAGE

# Ignitio Hub (Meta Business Account 2)
ACCOUNT2_ACCESS_TOKEN
ACCOUNT2_PHONE_ID

# AI (currently disabled)
GEMINI_API_KEY

# PostgreSQL / Neon
DB_HOST
DB_PORT              # default 5432
DB_NAME              # default neondb
DB_USER
DB_PASSWORD
DB_SSLMODE           # default require
DB_CHANNEL_BINDING   # default require
```

## Key design notes

- `db_manager` is a **module-level singleton** instantiated when `utils/db_manager.py` is imported. Connection failures at import time raise immediately and crash startup.
- `DatabaseManager.execute_query()` retries up to 3 times; reconnects automatically on connection drops.
- Inbound text messages trigger an AI auto-reply via `get_ai_response()`. Currently the responder is a stub that returns `None` — no replies are sent. To re-enable, restore the Gemini implementation in `utils/ai_responder.py` and set `GEMINI_API_KEY`.
- Webhook HMAC signature validation is **disabled** in `decorators/security.py`. Re-enable before production by uncommenting the original `validate_signature` logic and setting `APP_SECRET`.
- Images received inbound are downloaded and stored at `static/uploads/`. Outbound images sent via `/api/send-image` are also stored there before being sent.
- `ON CONFLICT (id) DO NOTHING` on inserts prevents duplicate messages from replayed webhooks.

## Dependencies

```
flask
python-dotenv
requests
psycopg2-binary
gunicorn
google-generativeai>=0.5.0   # only needed if AI responder is re-enabled
openai                        # unused in current code
aiohttp                       # unused in current code
```
