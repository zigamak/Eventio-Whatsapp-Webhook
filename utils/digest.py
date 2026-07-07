"""
digest.py — Daily AI-ranked digest of inbound eventio_messages.

Pulls the last 24h of inbound messages for Eventio, asks Gemini to classify
each as inquiry / urgent / general and score it for reply-priority, then
emails a scannable summary (top messages in full, the rest as snippets).

A Postgres claim table (digest_log) guards against duplicate sends if the
in-process scheduler (see run.py) ends up running in more than one worker.
"""

import html
import json
import logging
import re
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import formataddr

import google.generativeai as genai

import config
from utils.db_manager import db_manager

logger = logging.getLogger(__name__)

EVENTIO_TABLE = "public.eventio_messages"
GEMINI_MODEL = "gemini-1.5-flash"
TRIAGE_BATCH_SIZE = 20      # messages per coarse triage call
REFINE_CANDIDATE_CAP = 20   # max messages that get the deeper second-pass review
CONTEXT_MESSAGE_LIMIT = 10  # conversation history depth fed to the refine sub-agent

CATEGORY_LABELS = {
    "inquiry": "📩 Inquiry",
    "urgent": "🚨 Urgent",
    "general": "General",
}


def fetch_recent_messages(hours=24):
    """Inbound eventio_messages from the last `hours` hours."""
    return db_manager.get_recent_inbound_messages(EVENTIO_TABLE, hours=hours)


def _parse_gemini_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _get_model():
    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


def _generate_json(model, prompt):
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
    except TypeError:
        # Older SDK versions may not support response_mime_type
        response = model.generate_content(prompt)
    return _parse_gemini_json(response.text)


def _build_triage_prompt(batch):
    lines = []
    for i, msg in enumerate(batch):
        body = (msg.get("body") or "").replace("\n", " ").strip()
        lines.append(f'{i}. From "{msg.get("name") or "Unknown"}": "{body}"')

    return (
        "You are the triage sub-agent for the WhatsApp inbox of Eventio, an "
        "events business. Most inbound messages are social pleasantries from "
        "past guests (thank-you notes, blessings, greetings) — low priority. "
        "Occasionally a message is a genuine business inquiry (asking about "
        "booking, pricing, availability, or details of Eventio's event "
        "services) or an urgent/dissatisfied message needing a fast reply — "
        "high priority.\n\n"
        "Classify EVERY numbered message below and return a JSON array only "
        "(no prose, no markdown fences), one object per message, each with "
        "exactly these fields:\n"
        '  "index": the message number (integer)\n'
        '  "category": one of "inquiry", "urgent", "general"\n'
        '  "score": integer 1-10 reply-priority (10 = reply immediately)\n'
        '  "reason": a short (<15 word) justification\n\n'
        "Messages:\n" + "\n".join(lines)
    )


def _triage_batch(model, batch):
    """Sub-agent 1: fast, coarse classification of a batch of messages."""
    try:
        verdicts = _generate_json(model, _build_triage_prompt(batch))
    except Exception as e:
        logger.error(f"Triage batch failed, defaulting batch to 'general': {e}")
        verdicts = []

    verdicts_by_index = {int(v["index"]): v for v in verdicts if "index" in v}
    results = []
    for i, msg in enumerate(batch):
        v = verdicts_by_index.get(i, {})
        results.append({
            "message_id": msg["id"],
            "wa_id": msg["wa_id"],
            "category": v.get("category", "general"),
            "score": v.get("score", 5),
            "reason": v.get("reason", ""),
        })
    return results


def _build_refine_prompt(msg, context_rows):
    context_lines = []
    for row in reversed(context_rows):  # chronological order for readability
        who = "Guest" if row["direction"] == "inbound" else "Eventio"
        context_lines.append(f"{who}: {(row.get('body') or '').strip()}")

    return (
        "You are the priority-review sub-agent for Eventio's WhatsApp inbox. "
        "A triage pass already flagged the message below as a likely inquiry "
        "or urgent item. Using the recent conversation history for context, "
        "give a sharper assessment.\n\n"
        "Recent conversation with this contact (oldest first):\n"
        + "\n".join(context_lines)
        + "\n\nMost recent inbound message to assess: "
        f'"{(msg.get("body") or "").strip()}"\n\n'
        "Return a single JSON object only (no prose, no markdown fences) with:\n"
        '  "category": one of "inquiry", "urgent", "general"\n'
        '  "score": integer 1-10 reply-priority (10 = reply immediately)\n'
        '  "reason": a concise (<20 word) summary of what they need/want, '
        "useful for someone deciding whether to reply right now"
    )


def _refine_candidate(model, msg):
    """Sub-agent 2: deeper review (with conversation context) for messages the triage pass flagged as important."""
    fallback = {
        "message_id": msg["id"],
        "wa_id": msg["wa_id"],
        "category": msg["category"],
        "score": msg["score"],
        "reason": msg["reason"],
    }
    try:
        context_rows = db_manager.get_conversation_context(
            EVENTIO_TABLE, msg["wa_id"], limit=CONTEXT_MESSAGE_LIMIT
        )
        verdict = _generate_json(model, _build_refine_prompt(msg, context_rows))
        if isinstance(verdict, list):
            verdict = verdict[0]
        return {
            "message_id": msg["id"],
            "wa_id": msg["wa_id"],
            "category": verdict.get("category", msg["category"]),
            "score": verdict.get("score", msg["score"]),
            "reason": verdict.get("reason", msg["reason"]),
        }
    except Exception as e:
        logger.error(f"Refine pass failed for message {msg['id']}, keeping triage result: {e}")
        return fallback


def rank_messages_with_gemini(messages):
    """
    Orchestrator: runs a cheap triage sub-agent over all messages in batches
    (persisting results after every batch so a crash mid-run loses no work
    and reruns skip already-ranked messages), then spends a deeper,
    context-aware refine sub-agent pass only on the messages triage flagged
    as inquiry/urgent — the ones actually worth extra attention.

    Returns `messages` combined with category/score/reason, sorted by score
    desc then recency.
    """
    if not messages:
        return []

    message_ids = [m["id"] for m in messages]
    existing = db_manager.get_existing_rankings(message_ids)

    to_triage = [m for m in messages if m["id"] not in existing]
    if to_triage:
        model = _get_model()
        for start in range(0, len(to_triage), TRIAGE_BATCH_SIZE):
            batch = to_triage[start:start + TRIAGE_BATCH_SIZE]
            batch_results = _triage_batch(model, batch)
            db_manager.upsert_rankings(batch_results)  # persisted immediately, batch by batch
            for r in batch_results:
                existing[r["message_id"]] = r

    combined = [{**msg, **existing[msg["id"]]} for msg in messages]

    candidates = [m for m in combined if m["category"] in ("inquiry", "urgent")]
    candidates.sort(key=lambda m: m["score"], reverse=True)
    candidates = candidates[:REFINE_CANDIDATE_CAP]

    if candidates:
        model = _get_model()
        refined_by_id = {}
        for msg in candidates:
            refined = _refine_candidate(model, msg)
            refined_by_id[refined["message_id"]] = refined
        db_manager.upsert_rankings(list(refined_by_id.values()))  # persisted immediately
        for m in combined:
            if m["id"] in refined_by_id:
                m.update(refined_by_id[m["id"]])

    combined.sort(key=lambda m: (m["score"], m["timestamp"]), reverse=True)
    return combined


BRAND_PURPLE = "#46276a"
BRAND_PURPLE_LIGHT = "#faf8fc"
BRAND_PURPLE_MUTED = "#6b5a7a"
LOGO_URL = "https://eventio.africa/wp-content/uploads/2025/02/eventio-logo-1-scaled.png"


def _format_readable_date(dt):
    day = dt.day
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix} {dt.strftime('%B')}, {dt.year}"


def _contact_line(m):
    name = html.escape(m.get("name") or "Unknown")
    wa_id = html.escape(str(m.get("wa_id") or "—"))
    return f"<b>{name}</b> <span style='color:{BRAND_PURPLE_MUTED};'>&middot; 📞 {wa_id}</span>"


def _email_shell(title, subtitle, body_html):
    return f"""
<div style="background:#f4f1f7;padding:24px 12px;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e5e0ec;">
    <div style="background:{BRAND_PURPLE};padding:28px 24px;text-align:center;">
      <img src="{LOGO_URL}" alt="Eventio" style="height:40px;margin-bottom:14px;" />
      <h1 style="color:#ffffff;margin:0;font-size:20px;font-family:Arial,Helvetica,sans-serif;">{html.escape(title)}</h1>
      <p style="color:#e0d6ec;margin:6px 0 0;font-size:13px;">{html.escape(subtitle)}</p>
    </div>
    <div style="padding:24px;color:#2c1a40;">
      {body_html}
    </div>
    <div style="padding:16px 24px;background:{BRAND_PURPLE_LIGHT};text-align:center;font-size:12px;color:{BRAND_PURPLE_MUTED};">
      Automated daily digest &middot; public.eventio_messages
    </div>
  </div>
</div>
"""


def render_digest_email(ranked, hours=24):
    """
    Returns (subject, html_body) for the digest. Groups every message by
    category (no fixed top-N cutoff) — Urgent and Inquiry get full detail
    since those are what someone needs to act on, General is shown as a
    compact list so the noise (thank-yous/greetings) is still visible but
    doesn't crowd out what matters. Every entry shows both the contact's
    name and phone number (wa_id).
    """
    today_dt = datetime.now(timezone.utc)
    today_readable = _format_readable_date(today_dt)
    subject = f"Eventio WhatsApp Messages — Last 24 Hours ({today_readable})"
    title = "Eventio WhatsApp Messages"
    subtitle = f"{today_readable} — the most pressing messages, ranked"

    if not ranked:
        body = f"<p>No inbound messages on eventio_messages in the last {hours} hours.</p>"
        return subject, _email_shell(title, subtitle, body)

    buckets = {"urgent": [], "inquiry": [], "general": []}
    for m in ranked:
        buckets.setdefault(m["category"], buckets["general"]).append(m)

    parts = []

    for category in ("urgent", "inquiry"):
        msgs = buckets[category]
        if not msgs:
            continue
        label = CATEGORY_LABELS.get(category, category)
        parts.append(
            f"<h2 style='color:{BRAND_PURPLE};border-bottom:2px solid {BRAND_PURPLE};"
            f"padding-bottom:6px;font-size:16px;margin:24px 0 12px;'>{label} ({len(msgs)})</h2>"
        )
        for m in msgs:
            parts.append(
                f"<div style='margin-bottom:14px;padding:14px;border-left:4px solid {BRAND_PURPLE};"
                f"background:{BRAND_PURPLE_LIGHT};border-radius:4px;'>"
                f"<div style='margin-bottom:4px;'>{_contact_line(m)}"
                f" <span style='color:{BRAND_PURPLE_MUTED};font-size:12px;'>&middot; score {m['score']}/10</span></div>"
                f"<div style='font-size:12px;font-style:italic;color:{BRAND_PURPLE};margin-bottom:8px;'>{html.escape(m.get('reason', ''))}</div>"
                f"<div style='font-size:14px;color:#333;'>{html.escape(m.get('body') or '')}</div>"
                "</div>"
            )

    general = buckets["general"]
    if general:
        parts.append(
            f"<h3 style='color:{BRAND_PURPLE};border-bottom:1px solid #e5e0ec;"
            f"padding-bottom:6px;font-size:14px;margin:24px 0 12px;'>{CATEGORY_LABELS['general']} ({len(general)})</h3>"
        )
        parts.append("<ul style='padding-left:18px;margin:0;'>")
        for m in general:
            snippet = html.escape((m.get("body") or "")[:120])
            parts.append(f"<li style='margin-bottom:8px;font-size:13px;'>{_contact_line(m)} — {snippet}</li>")
        parts.append("</ul>")

    return subject, _email_shell(title, subtitle, "\n".join(parts))


def send_digest_email(subject, html_body):
    if not (config.SMTP_HOST and config.SMTP_USERNAME and config.SMTP_PASSWORD and config.DIGEST_RECIPIENT_EMAIL):
        raise RuntimeError("SMTP/digest recipient env vars are not fully configured")

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = formataddr((config.EMAIL_FROM_NAME, config.EMAIL_FROM))
    msg["To"] = config.DIGEST_RECIPIENT_EMAIL

    port = int(config.SMTP_PORT)
    if config.SMTP_SECURE.lower() == "ssl" or port == 465:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, port)
    else:
        server = smtplib.SMTP(config.SMTP_HOST, port)
        server.starttls()

    with server:
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        server.sendmail(config.EMAIL_FROM, [config.DIGEST_RECIPIENT_EMAIL], msg.as_string())


def run_daily_digest(hours=24, force=False):
    """
    Orchestrates the full job: claim lock -> fetch -> rank -> render -> send.
    Returns a summary dict; never raises (errors are logged and returned).
    """
    today = datetime.now(timezone.utc).date()
    summary = {"date": str(today), "sent": False, "message_count": 0, "error": None}

    claimed = False
    try:
        if not force:
            if not db_manager.claim_digest_run(today):
                summary["error"] = "Digest already sent today (claim lock held by another run)"
                logger.info(summary["error"])
                return summary
            claimed = True

        messages = fetch_recent_messages(hours=hours)
        summary["message_count"] = len(messages)

        ranked = rank_messages_with_gemini(messages)
        subject, html_body = render_digest_email(ranked, hours=hours)
        send_digest_email(subject, html_body)

        summary["sent"] = True
        summary["categories"] = {
            cat: sum(1 for m in ranked if m["category"] == cat)
            for cat in ("inquiry", "urgent", "general")
        }
        logger.info(f"✅ Daily digest sent: {summary}")
    except Exception as e:
        summary["error"] = str(e)
        logger.error(f"❌ Daily digest failed: {e}")
        if claimed:
            # Don't let a failed attempt permanently block retries for today.
            db_manager.release_digest_claim(today)

    return summary
