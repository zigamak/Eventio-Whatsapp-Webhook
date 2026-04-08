"""
ai_responder.py — Place this file inside your utils/ folder.

Install dependency: pip install google-generativeai
Add to your .env:   GEMINI_API_KEY=your_key_here
"""

import logging
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini once at import time
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ── Eventio Africa Pricing Table ──────────────────────────────────────────────
# Each service: (base_price, per_guest_price, min_guests_for_per_guest)
# per_guest kicks in from guest 1 unless min_guests_for_per_guest is set

PRICING = {
    "online_rsvp":              {"label": "Online RSVP",                        "base": 25000, "per_guest": 20,  "per_guest_after": 0},
    "guest_management":         {"label": "Event Guest Management",              "base": 25000, "per_guest": 25,  "per_guest_after": 0},
    "e_invites":                {"label": "E-Invites with QR Codes",            "base": 25000, "per_guest": 25,  "per_guest_after": 0},
    "checkin_team":             {"label": "Physical Check-In Team (per person)", "base": 50000, "per_guest": 0,   "per_guest_after": 0, "note": "₦50,000 per team member (min. 1)"},
    "table_arrangement":        {"label": "Table Arrangement & Floorplan",       "base": 20000, "per_guest": 5,   "per_guest_after": 100},
    "photo_wall":               {"label": "Photo Wall (Love Wall)",              "base": 50000, "per_guest": 25,  "per_guest_after": 0},
    "analytics":                {"label": "Event Analytics & Reports",           "base": 20000, "per_guest": 5,   "per_guest_after": 100},
    "live_streaming":           {"label": "Live Streaming Integration",          "base": 200000,"per_guest": 5,   "per_guest_after": 100},
    "badge_printing":           {"label": "Onsite Badge Printing",               "base": 0,     "per_guest": 400, "per_guest_after": 0},
    "wristbands":               {"label": "Wristbands",                          "base": 0,     "per_guest": 100, "per_guest_after": 0},
    "surveys":                  {"label": "Event Surveys & Feedback Forms",      "base": 25000, "per_guest": 25,  "per_guest_after": 0},
    "event_website":            {"label": "Event Website",                       "base": 100000,"per_guest": 25,  "per_guest_after": 0},
    "ai_chatbot":               {"label": "AI Chatbot for Your Event",           "base": 200000,"per_guest": 5,   "per_guest_after": 100},
    "whatsapp_notifications":   {"label": "WhatsApp Notifications (per send)",   "base": 0,     "per_guest": 50,  "per_guest_after": 0, "note": "₦50 × guests × number of sends"},
}

def calculate_price(service_key: str, guests: int, sends: int = 1) -> dict:
    """Calculate price for a single service given guest count."""
    s = PRICING.get(service_key)
    if not s:
        return {}

    base = s["base"]
    per_guest = s["per_guest"]
    after = s["per_guest_after"]

    if service_key == "whatsapp_notifications":
        total = per_guest * guests * sends
    elif after > 0 and guests <= after:
        total = base  # per-guest only kicks in above threshold
    else:
        billable_guests = guests - after if after > 0 else guests
        total = base + (per_guest * billable_guests)

    return {
        "label": s["label"],
        "total": total,
        "note": s.get("note", "")
    }

def build_pricing_summary(selected_services: list, guests: int) -> str:
    """Build a formatted pricing breakdown string."""
    lines = [f"📊 *Estimated Pricing for {guests} guests:*\n"]
    grand_total = 0

    for key in selected_services:
        result = calculate_price(key, guests)
        if result:
            price_str = f"₦{result['total']:,.0f}"
            line = f"• {result['label']}: {price_str}"
            if result["note"]:
                line += f"\n  _{result['note']}_"
            lines.append(line)
            grand_total += result["total"]

    lines.append(f"\n💰 *Estimated Total: ₦{grand_total:,.0f}*")
    lines.append("\n_Note: Final pricing may vary. Contact us to get a confirmed quote._")
    return "\n".join(lines)


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a friendly, professional WhatsApp assistant for Eventio Africa — an event management 
company that helps organizers deliver seamless, tech-powered experiences for their guests.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT EVENTIO AFRICA DOES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Eventio Africa offers the following services:

1. E-Invitations with QR Codes — digital invites sent via WhatsApp with a unique QR code for 
   check-in. No physical cards — everything is on the guest's phone.
2. Online RSVP — guests confirm attendance digitally; organizers track in real time.
3. Event Guest Management — full guest list, attendance tracking, check-in status.
4. Physical Check-In Team — trained Eventio staff on-site to scan QR codes at the entrance.
5. Table Arrangement & Floorplan Formatting — seating assignments and formatted floorplans.
6. Photo Wall (Love Wall) — interactive live photo display at the event.
7. Event Analytics & Reports — post-event attendance data and insights.
8. Live Streaming Integration — stream the event for guests attending remotely.
9. Onsite Badge Printing — name badges printed at the entrance during check-in.
10. Wristbands — physical wristbands for access management.
11. Event Surveys & Feedback Forms — post-event guest feedback collection.
12. Event Website — a dedicated webpage for the event.
13. AI Chatbot for Events — an AI assistant for a specific event to answer guest questions.
14. WhatsApp Notifications — bulk WhatsApp messages for reminders and updates.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HANDLING COMPLAINTS (wrong info / missing invite / QR not working)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If a guest says anything like:
  - "I didn't receive my invitation"
  - "My name is wrong on the invite"
  - "Wrong date or details on my invite"
  - "My QR code is not working"
  - "I got the wrong invite" / "my information is incorrect"

ALWAYS respond with a sincere apology and let them know the team will look into it 
and get back to them. Do NOT ask for their name (you already have it from the database) 
or any other details. Keep it short and reassuring.

Example: "We're really sorry about that! 😔 Our team has been notified and will look into 
this for you right away. We'll get back to you shortly. 🙏"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HANDLING PRICING ENQUIRIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If a guest or organizer asks about services, pricing, cost, or packages:

Step 1 — Ask which features they are interested in (list them clearly).
Step 2 — Ask for their expected guest count.
Step 3 — Once you have both, reply with: 
  "CALCULATE_PRICING:[service1,service2,...]:GUESTS:[number]"
  (The system will compute and send the breakdown automatically.)

Available service keys to use in the tag:
  online_rsvp, guest_management, e_invites, checkin_team, table_arrangement,
  photo_wall, analytics, live_streaming, badge_printing, wristbands,
  surveys, event_website, ai_chatbot, whatsapp_notifications

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERAL TONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Warm, friendly, and professional. This is WhatsApp — keep replies short (2–5 sentences).
- Use simple language. Light emojis are fine (1–2 max per message).
- If you don't know specific event details (venue, time, dress code), say the organizer 
  will share those details and to check their invitation.
- Never make up event-specific information.
"""

# ── Main function ─────────────────────────────────────────────────────────────

def get_ai_response(current_message: str, conversation_history: list, guest_name: str = None) -> str | None:
    """
    Generate an AI reply using Gemini, informed by conversation history.
    Handles pricing calculation tag if Gemini returns it.

    Args:
        current_message:      The latest text from the user.
        conversation_history: List of dicts from DB with 'direction' and 'body'.
                              Oldest first, last 20 messages.
        guest_name:           Guest's name from the database (optional).

    Returns:
        AI reply string, or None if the call fails.
    """
    try:
        # Build Gemini chat history from DB records
        history = []
        for msg in conversation_history:
            role = "user" if msg["direction"] == "inbound" else "model"
            body = msg.get("body") or ""
            if body.strip():
                history.append({"role": role, "parts": [body]})

        # Start chat with history for full context
        chat = model.start_chat(history=history)

        # Build the prompt — prepend system prompt on first message
        name_context = f"\n\nThe guest's name is: {guest_name}." if guest_name else ""
        if not history:
            prompt = f"{SYSTEM_PROMPT}{name_context}\n\n---\nGuest message: {current_message}"
        else:
            prompt = current_message

        response = chat.send_message(prompt)
        reply = response.text.strip()

        # ── Check if Gemini wants to calculate pricing ────────────────────
        if "CALCULATE_PRICING:" in reply:
            try:
                # Expected format: CALCULATE_PRICING:[s1,s2,...]:GUESTS:[n]
                parts = reply.split("CALCULATE_PRICING:")[1]
                services_part, guests_part = parts.split(":GUESTS:")
                services = [s.strip() for s in services_part.strip("[]").split(",")]
                guests = int(guests_part.strip())
                reply = build_pricing_summary(services, guests)
                logger.info(f"Pricing calculated for {guests} guests: {services}")
            except Exception as parse_err:
                logger.error(f"Failed to parse pricing tag: {parse_err}")
                # Fall back to the raw reply if parsing fails
        # ─────────────────────────────────────────────────────────────────

        logger.info(f"AI replied: {reply[:80]}...")
        return reply

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None