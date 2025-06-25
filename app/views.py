import logging
import json
from datetime import datetime # Import datetime for timestamping outbound messages

from flask import Blueprint, request, jsonify, current_app, send_from_directory

# Import security decorator and WhatsApp utility functions
from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
    send_message,
    get_text_message_input,
    load_messages,
    save_message # Ensure save_message is imported to store outbound messages
)

# Blueprints for modular routing
webhook_blueprint = Blueprint("webhook", __name__)
# The portal blueprint will serve static files from the 'static' folder inside 'APP'
# The static_url_path means files will be accessible at /static/filename.ext
portal_blueprint = Blueprint("portal", __name__, static_folder='static', static_url_path='/static')


@portal_blueprint.route("/")
def index():
    """
    Serves the main HTML page for the WhatsApp portal.
    This route will render 'index.html' located in the 'APP/STATIC' directory.
    """
    return send_from_directory(portal_blueprint.static_folder, "index.html")

@portal_blueprint.route("/api/messages", methods=["GET"])
def get_all_messages():
    """
    API endpoint to retrieve all stored WhatsApp messages.
    This endpoint is called by the frontend (index.html) to display conversations.
    Returns:
        JSON response containing a list of all message objects.
    """
    messages = load_messages()
    return jsonify(messages), 200

@portal_blueprint.route("/api/send_reply", methods=["POST"])
def send_reply():
    """
    API endpoint to send a reply message to a specific WhatsApp user.
    This endpoint is called by the frontend when a user types a message and clicks send.
    It expects a JSON payload containing 'recipient_waid' (the WhatsApp ID of the user)
    and 'message_text' (the content of the reply).
    """
    data = request.get_json()
    recipient_waid = data.get("recipient_waid")
    message_text = data.get("message_text")

    if not recipient_waid or not message_text:
        return jsonify({"status": "error", "message": "Missing recipient_waid or message_text"}), 400

    # Prepare the message payload for the WhatsApp Business API
    whatsapp_data_payload = get_text_message_input(recipient_waid, message_text)
    
    # Send the message using the utility function
    # send_message returns a tuple: (jsonify_response, status_code)
    response_json_data, status_code = send_message(whatsapp_data_payload)

    if status_code == 200:
        # If the message was successfully sent via WhatsApp API,
        # save this outbound message to our local messages.json store.
        outbound_message_data = {
            # WhatsApp API provides a message ID in its success response,
            # but for simplicity here, we can set a placeholder or use the API's returned ID if needed.
            "id": response_json_data.json.get("whatsapp_response", {}).get("messages", [{}])[0].get("id"),
            "wa_id": recipient_waid,
            "name": "You", # Name representing the portal user sending the message
            "type": "text",
            "body": message_text,
            "timestamp": datetime.now().isoformat(), # Current time for the sent message
            "direction": "outbound" # Mark as an outbound message
        }
        save_message(outbound_message_data)
    
    # Return the response received from the send_message utility function
    return response_json_data, status_code


def handle_message():
    """
    Handles incoming webhook events from the WhatsApp API.
    This function is called when WhatsApp sends a message or status update to your webhook URL.
    It now focuses on processing and storing incoming messages, rather than generating an immediate reply.
    """
    body = request.get_json()
    logging.info(f"Received webhook body: {json.dumps(body, indent=2)}")

    # Check if the incoming payload is a WhatsApp status update (e.g., message sent, delivered, read)
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update. No action taken for display.")
        return jsonify({"status": "ok"}), 200

    try:
        # Check if it's a valid incoming WhatsApp message
        if is_valid_whatsapp_message(body):
            process_whatsapp_message(body) # Process and store the message
            return jsonify({"status": "ok", "message": "Message received and stored"}), 200
        else:
            # If the request is not a recognized WhatsApp API message event
            logging.warning("Received a non-WhatsApp API event or invalid message structure.")
            return (
                jsonify({"status": "error", "message": "Not a valid WhatsApp API message event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON from webhook request.")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400
    except Exception as e:
        logging.error(f"An unhandled error occurred in handle_message: {e}")
        return jsonify({"status": "error", "message": f"Server error: {e}"}), 500


# Required webhook verification for WhatsApp
def verify():
    """
    Handles the webhook verification request from WhatsApp when setting up the webhook.
    It validates the 'hub.mode' and 'hub.verify_token'.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.info("VERIFICATION_FAILED: Mode or token mismatch.")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        logging.info("MISSING_PARAMETER: Webhook verification parameters missing.")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    """
    GET endpoint for WhatsApp webhook verification.
    """
    return verify()

@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required # Ensures the incoming webhook request is from Meta/WhatsApp
def webhook_post():
    """
    POST endpoint for incoming WhatsApp messages and other events.
    """
    return handle_message()

