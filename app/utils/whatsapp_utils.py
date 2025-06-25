import logging
from flask import current_app, jsonify
import json
import requests
import re
import os
from datetime import datetime

# Define the path for the JSON file to store messages
# This path makes it relative to the 'APP' directory
MESSAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'messages.json')

def log_http_response(response):
    """
    Logs the HTTP response details for debugging and monitoring.
    """
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    """
    Constructs the JSON payload required by the WhatsApp Business API
    for sending a standard text message.
    """
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    """
    Sends a message to the WhatsApp API. This function is used by both
    the webhook (if you decide to auto-respond) and the portal's send_reply endpoint.
    It now returns a Flask-compatible jsonify response and status code.
    """
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['WHATAPP_ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": f"Failed to send message: {e}"}), 500
    else:
        log_http_response(response)
        # Return success with the WhatsApp API response data
        return jsonify({"status": "ok", "message": "Message sent successfully", "whatsapp_response": response.json()}), 200


def process_text_for_whatsapp(text):
    """
    Prepares text for WhatsApp by removing specific patterns (e.g., brackets)
    and converting double asterisks to single asterisks for bold formatting,
    as WhatsApp uses single asterisks for bold.
    """
    # Remove brackets like 【text】
    pattern = r"\【.*?\】"
    text = re.sub(pattern, "", text).strip()

    # Convert **bold** to *bold*
    pattern = r"\*\*(.*?)\*\*"
    replacement = r"*\1*"
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def load_messages():
    """
    Loads all messages from the messages.json file.
    Initializes an empty file if it doesn't exist or is invalid.
    """
    if not os.path.exists(MESSAGES_FILE):
        # Create an empty JSON file if it doesn't exist
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
            # Ensure messages is a list even if the file was empty or malformed
            if not isinstance(messages, list):
                logging.warning(f"{MESSAGES_FILE} content is not a list. Resetting file.")
                messages = []
                with open(MESSAGES_FILE, 'w', encoding='utf-8') as f_reset:
                    json.dump([], f_reset)
            return messages
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {MESSAGES_FILE}. File might be corrupt. Resetting file.")
        # If the file is corrupted, re-initialize it as an empty list
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading messages from {MESSAGES_FILE}: {e}")
        return []

def save_message(message_data):
    """
    Appends a new message (inbound or outbound) to the messages.json file.
    Ensures the file is properly handled.
    """
    messages = load_messages() # Load current messages to append
    messages.append(message_data)
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4) # Use indent for readability
    except Exception as e:
        logging.error(f"An error occurred while saving message to {MESSAGES_FILE}: {e}")


def process_whatsapp_message(body):
    """
    Processes an incoming WhatsApp webhook message.
    Extracts relevant details like sender ID, name, message body, type, and timestamp,
    then saves this information to the messages.json file.
    """
    try:
        # Extract contact information
        contacts = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        wa_id = contacts["wa_id"]
        name = contacts["profile"]["name"]

        # Extract message information
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_id = message.get("id")
        message_type = message["type"]
        timestamp = datetime.fromtimestamp(int(message["timestamp"])).isoformat() # Convert epoch to ISO format

        message_body = "Unsupported message type" # Default for unhandled types

        # Handle different message types
        if message_type == "text":
            message_body = message["text"]["body"]
        elif message_type == "image":
            message_body = f"Image message (ID: {message['image']['id']})"
        elif message_type == "video":
            message_body = f"Video message (ID: {message['video']['id']})"
        elif message_type == "audio":
            message_body = f"Audio message (ID: {message['audio']['id']})"
        elif message_type == "document":
            message_body = f"Document message (ID: {message['document']['id']}, Filename: {message['document'].get('filename', 'N/A')})"
        elif message_type == "location":
            message_body = f"Location message (Latitude: {message['location']['latitude']}, Longitude: {message['location']['longitude']})"
        elif message_type == "sticker":
            message_body = f"Sticker message (ID: {message['sticker']['id']})"
        elif message_type == "contacts":
            contact_names = ", ".join([c['profile']['name'] for c in message['contacts']])
            message_body = f"Contact message: {contact_names}"
        elif message_type == "button":
            message_body = f"Button click: {message['button']['text']} (payload: {message['button']['payload']})"
        elif message_type == "interactive":
            interactive_type = message['interactive']['type']
            if interactive_type == 'button_reply':
                message_body = f"Interactive button reply: {message['interactive']['button_reply']['title']} (ID: {message['interactive']['button_reply']['id']})"
            elif interactive_type == 'list_reply':
                message_body = f"Interactive list reply: {message['interactive']['list_reply']['title']} (ID: {message['interactive']['list_reply']['id']})"
            else:
                message_body = f"Interactive message type: {interactive_type}"
        else:
            logging.warning(f"Unhandled WhatsApp message type: {message_type}. Full message: {json.dumps(message)}")


        # Construct the message data to be stored
        message_data = {
            "id": message_id, # WhatsApp message ID
            "wa_id": wa_id,   # Sender's WhatsApp ID
            "name": name,     # Sender's name
            "type": message_type,
            "body": message_body,
            "timestamp": timestamp,
            "direction": "inbound" # Mark as inbound message
        }
        save_message(message_data) # Save to JSON file
        logging.info(f"Incoming message from {name} ({wa_id}) stored: {message_body}")

    except KeyError as e:
        logging.error(f"Missing key in WhatsApp message payload: {e}. Body: {json.dumps(body, indent=2)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing WhatsApp message: {e}. Body: {json.dumps(body, indent=2)}")


def is_valid_whatsapp_message(body):
    """
    Checks if the incoming webhook event payload has the expected structure
    for a valid WhatsApp message.
    """
    return (
        body.get("object") == "whatsapp_business_account" # Ensure it's from a WABA
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
        and body["entry"][0]["changes"][0]["value"].get("contacts") # Ensure contacts exist
        and body["entry"][0]["changes"][0]["value"]["contacts"][0]
    )

