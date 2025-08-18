from flask import Blueprint, render_template, jsonify, request
from config import WHATSAPP_ACCESS_TOKEN, EVENTIO_PHONE_ID, PACKAGE_WITH_SENSE_PHONE_ID, VERSION, VERIFY_TOKEN
import requests
import logging
import os
from datetime import datetime
from utils.whatsapp_utils import process_whatsapp_message, is_valid_whatsapp_message, load_messages, save_message, get_text_message_input, send_message

bp = Blueprint('main', __name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define JSON file paths based on the provided phone IDs
# The key change is to use 'os.getcwd()' which returns the current working directory,
# where the 'run.py' script is executed.
EVENTIO_MESSAGES_FILE = os.path.join(os.getcwd(), 'eventio_messages.json')
PACKAGE_WITH_SENSE_MESSAGES_FILE = os.path.join(os.getcwd(), 'package_with_sense_messages.json')

# Map phone number IDs to their respective JSON files
# NOTE: The values here are fetched from your config.py, which in turn
# gets them from environment variables or uses the provided default values.
PHONE_ID_TO_FILE = {
    EVENTIO_PHONE_ID: EVENTIO_MESSAGES_FILE,
    PACKAGE_WITH_SENSE_PHONE_ID: PACKAGE_WITH_SENSE_MESSAGES_FILE
}

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/chats', methods=['GET'])
def get_chats():
    phone_id = request.args.get('phone_id')
    if phone_id not in PHONE_ID_TO_FILE:
        return jsonify({"message": "Invalid or missing phone_id"}), 400
    
    file_path = PHONE_ID_TO_FILE[phone_id]
    messages = load_messages(file_path)
    chats = {}
    for msg in messages:
        wa_id = msg['wa_id']
        if wa_id not in chats:
            chats[wa_id] = {
                "wa_id": wa_id,
                "name": msg['name'],
                "last_message": msg['body'],
                "last_message_timestamp": msg['timestamp']
            }
    return jsonify({"chats": list(chats.values())})

@bp.route('/api/chats/<wa_id>', methods=['GET'])
def get_messages(wa_id):
    phone_id = request.args.get('phone_id')
    if phone_id not in PHONE_ID_TO_FILE:
        return jsonify({"message": "Invalid or missing phone_id"}), 400
    
    file_path = PHONE_ID_TO_FILE[phone_id]
    messages = load_messages(file_path)
    user_messages = [
        {
            "direction": msg['direction'],
            "body": msg['body'],
            "timestamp": msg['timestamp'],
            "status": msg.get('status', 'delivered')
        }
        for msg in messages if msg['wa_id'] == wa_id
    ]
    return jsonify({"messages": user_messages})

@bp.route('/api/respond', methods=['POST'])
def respond():
    data = request.get_json()
    wa_id = data.get('wa_id')
    message = data.get('message')
    phone_id = data.get('phone_id')
    
    if not wa_id or not message or not phone_id:
        return jsonify({"message": "Missing wa_id, message, or phone_id"}), 400
    
    if phone_id not in PHONE_ID_TO_FILE:
        return jsonify({"message": "Invalid phone_id"}), 400
    
    file_path = PHONE_ID_TO_FILE[phone_id]
    
    payload = get_text_message_input(wa_id, message)
    response, status_code = send_message(payload, phone_id)
    
    # Check if the API call was successful
    if response and response.ok:
        try:
            # Correctly parse the JSON response
            response_data = response.json()
            message_data = {
                "id": response_data.get('messages', [{}])[0].get('id', 'N/A'),
                "wa_id": wa_id,
                "name": "Bot", 
                "type": "text",
                "body": message,
                "timestamp": datetime.now().isoformat(),
                "direction": "outbound",
                "status": "sent"
            }
            save_message(message_data, file_path)
            logger.info(f"Message sent to {wa_id} via phone_id {phone_id}: {message}")
            return jsonify({"status": "success", "message_id": message_data["id"]}), 200
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from WhatsApp API: {e}")
            return jsonify({"status": "error", "message": "Invalid response from WhatsApp API"}), 500
    else:
        # Handle unsuccessful API response
        try:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
        except:
            error_msg = response.text
        logger.error(f"Failed to send message. Status: {status_code}, Response: {error_msg}")
        return jsonify({"status": "error", "message": f"Failed to send message: {error_msg}"}), status_code

@bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            return challenge
        logger.error("Webhook verification failed")
        return "Verification failed", 403
    
    if request.method == 'POST':
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        if is_valid_whatsapp_message(data):
            # Check if phone number ID exists in the metadata
            phone_number_id = data["entry"][0]["changes"][0]["value"].get("metadata", {}).get("phone_number_id")
            if not phone_number_id or phone_number_id not in PHONE_ID_TO_FILE:
                logger.error(f"Unknown phone_number_id: {phone_number_id}")
                return jsonify({"status": "error", "message": "Unknown phone_number_id"}), 400
            
            file_path = PHONE_ID_TO_FILE[phone_number_id]
            process_whatsapp_message(data, file_path)
            return jsonify({"status": "received"})
        else:
            logger.error("Invalid WhatsApp message structure")
            return jsonify({"status": "error", "message": "Invalid message structure"}), 400
