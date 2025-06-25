# app/decorators/security.py

from functools import wraps
from flask import current_app, jsonify, request
import logging
import hashlib
import hmac


def validate_signature(payload, signature):
    """
    Validate the incoming payload's signature against our expected signature
    """
    # TEMPORARILY DISABLED: For development purposes
    logging.warning("Signature validation is temporarily disabled for development.")
    return True # This line temporarily disables signature validation

    # Original code (uncomment to re-enable):
    # expected_signature = hmac.new(
    #     bytes(current_app.config["APP_SECRET"], "latin-1"),
    #     msg=payload.encode("utf-8"),
    #     digestmod=hashlib.sha256,
    # ).hexdigest()
    # return hmac.compare_digest(expected_signature, signature)


def signature_required(f):
    """
    Decorator to ensure that the incoming requests to our webhook are valid and signed with the correct signature.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Even with validation disabled, the header parsing might still occur if the decorator is used
        signature = request.headers.get("X-Hub-Signature-256", "")[
            7:
        ]   # Removing 'sha256='
        if not validate_signature(request.data.decode("utf-8"), signature):
            logging.info("Signature verification failed!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403
        return f(*args, **kwargs)

    return decorated_function