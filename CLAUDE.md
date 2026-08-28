# Eventio WhatsApp Webhook

A Flask application that receives and sends WhatsApp messages for four businesses via the Meta Business API, persisting all messages to PostgreSQL (Neon). It also exposes per-event message APIs, a CSV export page, and an AI-ranked inbox digest (manual-run only — see below).

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
views.py                    # All Flask routes (webhook + portals + chat/event/export/digest APIs)
run_digest.py               # CLI to run the digest on demand (python run_digest.py [--force] [--hours N])
export.py, export_pws.py    # Standalone CSV export scripts
query.py, diagnose.py       # Ad-hoc DB query / connectivity helpers
utils/
  db_manager.py             # DatabaseManager class + global db_manager singleton
  whatsapp_utils.py         # WhatsApp API helpers, PHONE_ID_TO_TABLE map, message processing
  digest.py                 # AI-ranked inbox digest (Gemini triage + refine, SMTP email)
  ai_responder.py           # Gemini AI auto-reply (currently disabled — returns None)
decorators/
  security.py               # Webhook HMAC signature validation (currently disabled for dev)
templates/                  # index (PwS), eventio, mwsmile, ignitiohub, export + shared whatsapp.css/js
__init__.py                 # Legacy factory create_app() — superseded by run.py
```

## Four phone IDs → four DB tables

The core routing concept: every phone ID maps to a dedicated table.

| Config var | Table |
|---|---|
| `ACCOUNT1_PHONE_ID_EVENTIO` | `public.eventio_messages` |
| `ACCOUNT1_PHONE_ID_PACKAGE` | `public.package_with_sense_messages` |
| `ACCOUNT1_PHONE_ID_MWSMILE` | `public.mwsmile_messages` |
| `ACCOUNT2_PHONE_ID` | `public.ignitiohub_messages` |

Mapping lives in `utils/whatsapp_utils.py:PHONE_ID_TO_TABLE`. Each phone ID also has its own access token in `PHONE_ID_TO_TOKEN` (MW Smile shares `PACKAGE_ACCESS_TOKEN`). Unknown phone IDs fall back to `public.eventio_messages`.

## Database schema (all four message tables identical)

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
event_id      INTEGER                    -- links a message to an event (indexed)
template_name VARCHAR(255)               -- template used for outbound template sends
updated_at    TIMESTAMPTZ
```

Supporting tables: `digest_log` (once-a-day claim lock for the digest) and `message_rankings` (cached AI category/score per message).

Tables are auto-created on startup by `DatabaseManager.create_tables_if_not_exists()`. Migrations run automatically and are idempotent: `migrate_add_error_details()`, `migrate_add_event_columns()`, `migrate_add_updated_at()`, `migrate_message_rankings_table()`.

## API routes

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/webhook` | Meta webhook (verification + inbound messages/statuses) |
| GET | `/` | Package with Sense portal (`index.html`) |
| GET | `/eventio` | Eventio portal (`eventio.html`) |
| GET | `/mwsmile` | MW Smile portal (`mwsmile.html`) |
| GET | `/ignitiohub` | Ignitio Hub portal (`ignitiohub.html`) |
| GET | `/export` | CSV export page (pick business, direction, date range) |
| GET | `/messages/<phone_id>` | Raw message list for a phone ID |
| GET | `/api/chats?phone_id=` | Chats grouped by wa_id with unread counts |
| GET | `/api/chats/<wa_id>?phone_id=` | All messages for one conversation |
| GET | `/api/messages` | Message polling feed (used by `cron/whatsapp_message_sync.php`) |
| POST | `/api/mark-read` | Mark inbound messages as read |
| POST | `/api/respond` | Send outbound text reply and save to DB |
| POST | `/api/send-image` | Upload image, send via API, save to DB |
| POST | `/api/log-outbound` | Log outbound message sent by Apps Script/PHP |
| GET | `/api/events/<event_id>/messages` | Messages for one event |
| GET | `/api/events/<event_id>/conversations` | Conversations grouped by guest for an event |
| GET | `/api/events/<event_id>/conversations/<wa_id>` | Full thread for one guest in an event |
| GET | `/api/events/<event_id>/stats` | Message/delivery stats for an event |
| POST | `/api/events/<event_id>/link-inbound` | Attach inbound messages to an event |
| POST | `/api/digest/run-now` | Manually trigger the digest (requires `DIGEST_SECRET`) |
| GET | `/api/export` | CSV download of messages |
| GET | `/get_image/<image_id>/<phone_id>` | Download image from WhatsApp media API |
| POST | `/send_message` | Generic send (text or image) |

## Daily digest email — DISABLED by default

`utils/digest.py` builds an AI-ranked summary of the last 24h of **inbound Eventio messages**: Gemini triages each message (inquiry / urgent / general + priority score), the top candidates get a deeper second pass with conversation context, and the result is emailed over SMTP.

**The automatic daily email is off.** `run.py` starts the APScheduler job only when `DIGEST_ENABLED` is truthy (`1` / `true` / `yes` / `on`); otherwise it logs `Daily digest scheduler disabled` at startup and never sends. To turn the daily email back on, set `DIGEST_ENABLED=true` (and `DIGEST_HOUR_UTC`, default `6`).

Manual runs still work either way:

```bash
python run_digest.py               # skipped if already sent today
python run_digest.py --force       # bypass the once-a-day claim lock
python run_digest.py --hours 48    # look further back
```

or `POST /api/digest/run-now` with the `DIGEST_SECRET` (optional `force`).

## Required environment variables

```
# Flask
SECRET_KEY
FLASK_DEBUG          # optional, default False
FLASK_HOST           # optional, default 0.0.0.0
FLASK_PORT           # optional, default 8000

# Webhook
VERIFY_TOKEN

# Eventio (Meta Business Account 1a)
EVENTIO_ACCESS_TOKEN
ACCOUNT1_PHONE_ID_EVENTIO

# Package with Sense (Meta Business Account 1b)
PACKAGE_ACCESS_TOKEN
ACCOUNT1_PHONE_ID_PACKAGE

# MW Smile (shares PACKAGE_ACCESS_TOKEN)
ACCOUNT1_PHONE_ID_MWSMILE

# Ignitio Hub (Meta Business Account 2)
ACCOUNT2_ACCESS_TOKEN
ACCOUNT2_PHONE_ID

# AI (auto-reply disabled; still used by the digest)
GEMINI_API_KEY

# PostgreSQL / Neon
DB_HOST
DB_PORT              # default 5432
DB_NAME              # default neondb
DB_USER
DB_PASSWORD
DB_SSLMODE           # default require
DB_CHANNEL_BINDING   # default require

# Digest email (only needed if you run or re-enable the digest)
DIGEST_ENABLED       # default false — daily email off
DIGEST_HOUR_UTC      # default 6
DIGEST_RECIPIENT_EMAIL
DIGEST_SECRET        # guards POST /api/digest/run-now
SMTP_HOST
SMTP_PORT            # default 587
SMTP_USERNAME
SMTP_PASSWORD
SMTP_SECURE          # 'tls' (STARTTLS, 587) or 'ssl' (implicit, 465)
EMAIL_FROM           # default SMTP_USERNAME
EMAIL_FROM_NAME      # default 'Eventio'
```

## Key design notes

- `db_manager` is a **module-level singleton** instantiated when `utils/db_manager.py` is imported. Connection failures at import time raise immediately and crash startup.
- Connections are **short-lived**: `execute_query()` opens a fresh connection per call and closes it before returning, so the Neon compute can scale to zero while the app is idle. `close()` is a no-op kept for backwards compatibility. Connects with up to 3 retries.
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
APScheduler                   # digest scheduler (job registered only when DIGEST_ENABLED)
google-generativeai>=0.5.0    # used by the digest; also needed if the AI responder is re-enabled
openai                        # unused in current code
aiohttp                       # unused in current code
```
