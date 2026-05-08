"""
ai_responder.py — Gemini AI auto-reply is currently DISABLED.
To re-enable: pip install google-generativeai, set GEMINI_API_KEY in .env,
and restore the full implementation.
"""

import logging

logger = logging.getLogger(__name__)


def get_ai_response(current_message: str, conversation_history: list, guest_name: str = None):
    """AI responder is disabled. Returns None so no auto-reply is sent."""
    logger.info("AI responder is disabled — skipping auto-reply")
    return None