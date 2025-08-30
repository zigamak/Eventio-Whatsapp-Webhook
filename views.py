from flask import Blueprint, render_template, jsonify, request
from config import WHATSAPP_ACCESS_TOKEN, EVENTIO_PHONE_ID, PACKAGE_WITH_SENSE_PHONE_ID, VERSION, VERIFY_TOKEN
import logging
import requests  # Add this import
import os  # Add this import
from datetime import datetime
from utils.whatsapp_utils import process_whatsapp_message, is_valid_whatsapp_message, get_text_message_input, send_message, get_table_name
from utils.db_manager import db_manager

bp = Blueprint('main', __name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map phone number IDs to their respective tables
PHONE_ID_TO_TABLE = {
    EVENTIO_PHONE_ID: 'eventio_messages',
    PACKAGE_WITH_SENSE_PHONE_ID: 'package_with_sense_messages'
}

def save_message(message_data, phone_id):
    """Save a message to the database"""
    if phone_id not in PHONE_ID_TO_TABLE:
        raise ValueError("Invalid phone_id")
    
    table_name = PHONE_ID_TO_TABLE[phone_id]
    try:
        db_manager.execute_query(
            "SELECT insert_message(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                table_name,
                message_data["id"],
                message_data["wa_id"],
                message_data["name"],
                message_data["type"],
                message_data["body"],
                message_data["timestamp"],
                message_data["direction"],
                message_data["status"],
                message_data["read"],
                message_data.get("image_url"),
                message_data.get("image_id")
            )
        )
        logger.info(f"Message saved to {table_name}: {message_data['id']}")
    except Exception as e:
        logger.error(f"Error saving message to {table_name}: {e}")
        raise

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/chats', methods=['GET'])
def get_chats():
    phone_id = request.args.get('phone_id')
    if phone_id not in PHONE_ID_TO_TABLE:
        return jsonify({"message": "Invalid or missing phone_id"}), 400
    
    table_name = PHONE_ID_TO_TABLE[phone_id]
    try:
        chats = db_manager.execute_query(
            "SELECT * FROM get_chats(%s)",
            (table_name,),
            fetch=True
        )
        return jsonify({"chats": chats})
    except Exception as e:
        logger.error(f"Error fetching chats from {table_name}: {e}")
        return jsonify({"message": "Error fetching chats", "error": str(e)}), 500

@bp.route('/api/chats/<wa_id>', methods=['GET'])
def get_messages(wa_id):
    phone_id = request.args.get('phone_id')
    if phone_id not in PHONE_ID_TO_TABLE:
        return jsonify({"message": "Invalid or missing phone_id"}), 400
    
    table_name = PHONE_ID_TO_TABLE[phone_id]
    try:
        messages = db_manager.execute_query(
            "SELECT * FROM get_messages(%s, %s)",
            (table_name, wa_id),
            fetch=True
        )
        return jsonify({"messages": messages})
    except Exception as e:
        logger.error(f"Error fetching messages for wa_id {wa_id} from {table_name}: {e}")
        return jsonify({"message": "Error fetching messages", "error": str(e)}), 500

@bp.route('/api/send-image', methods=['POST'])
def send_image():
    try:
        # Get form data
        wa_id = request.form.get('wa_id')
        phone_id = request.form.get('phone_id')
        image = request.files.get('image')
        caption = request.form.get('caption', '')
        
        if not wa_id or not phone_id or not image:
            return jsonify({"message": "Missing wa_id, phone_id, or image"}), 400
        
        if phone_id not in PHONE_ID_TO_TABLE:
            return jsonify({"message": "Invalid phone_id"}), 400
        
        # Save uploaded image
        uploads_dir = "static/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        filepath = os.path.join(uploads_dir, filename)
        image.save(filepath)
        
        # Create full URL for WhatsApp API (you'll need to adjust this based on your domain)
        image_url = f"{request.url_root}static/uploads/{filename}"
        
        # Send image via WhatsApp API
        from utils.whatsapp_utils import send_image_message
        response, status_code = send_image_message(wa_id, image_url, caption, phone_id)
        
        if response and response.ok:
            try:
                response_data = response.json()
                message_data = {
                    "id": response_data.get('messages', [{}])[0].get('id', 'N/A'),
                    "wa_id": wa_id,
                    "name": "Bot",
                    "type": "image",
                    "body": f"📷 Image: {caption}" if caption else "📷 Image",
                    "timestamp": datetime.now().isoformat(),
                    "direction": "outbound",
                    "status": "sent",
                    "read": True,
                    "image_url": f"/static/uploads/{filename}",
                    "image_id": None
                }
                save_message(message_data, phone_id)
                logger.info(f"Image sent to {wa_id} via phone_id {phone_id}")
                return jsonify({"status": "success", "message_id": message_data["id"]}), 200
            except (requests.exceptions.JSONDecodeError, ValueError) as e:
                logger.error(f"Error decoding JSON response from WhatsApp API: {e}")
                return jsonify({"status": "error", "message": "Invalid response from WhatsApp API"}), 500
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except:
                error_msg = response.text
            logger.error(f"Failed to send image. Status: {status_code}, Response: {error_msg}")
            return jsonify({"status": "error", "message": f"Failed to send image: {error_msg}"}), status_code
            
    except Exception as e:
        logger.error(f"Error in send_image endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/api/respond', methods=['POST'])
def respond():
    data = request.get_json()
    wa_id = data.get('wa_id')
    message = data.get('message')
    phone_id = data.get('phone_id')
    
    if not wa_id or not message or not phone_id:
        return jsonify({"message": "Missing wa_id, message, or phone_id"}), 400
    
    if phone_id not in PHONE_ID_TO_TABLE:
        return jsonify({"message": "Invalid phone_id"}), 400
    
    table_name = PHONE_ID_TO_TABLE[phone_id]
    
    payload = get_text_message_input(wa_id, message)
    response, status_code = send_message(payload, phone_id)
    
    if response and response.ok:
        try:
            response_data = response.json()
            message_data = {
                "id": response_data.get('messages', [{}])[0].get('id', 'N/A'),
                "wa_id": wa_id,
                "name": "Bot",
                "type": "text",
                "body": message,
                "timestamp": datetime.now().isoformat(),
                "direction": "outbound",
                "status": "sent",
                "read": True
            }
            save_message(message_data, phone_id)
            logger.info(f"Message sent to {wa_id} via phone_id {phone_id}: {message}")
            return jsonify({"status": "success", "message_id": message_data["id"]}), 200
        except (requests.exceptions.JSONDecodeError, ValueError) as e:
            logger.error(f"Error decoding JSON response from WhatsApp API: {e}")
            return jsonify({"status": "error", "message": "Invalid response from WhatsApp API"}), 500
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return jsonify({"status": "error", "message": "Message sent but failed to save"}), 500
    else:
        try:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
        except:
            error_msg = response.text
        logger.error(f"Failed to send message. Status: {status_code}, Response: {error_msg}")
        return jsonify({"status": "error", "message": f"Failed to send message: {error_msg}"}), status_code

@bp.route('/api/mark-read', methods=['POST'])
def mark_read():
    data = request.get_json()
    wa_id = data.get('wa_id')
    phone_id = data.get('phone_id')
    
    if not wa_id or not phone_id:
        return jsonify({"message": "Missing wa_id or phone_id"}), 400
    
    if phone_id not in PHONE_ID_TO_TABLE:
        return jsonify({"message": "Invalid phone_id"}), 400
    
    table_name = PHONE_ID_TO_TABLE[phone_id]
    try:
        db_manager.execute_query(
            "SELECT mark_messages_read(%s, %s)",
            (table_name, wa_id)
        )
        logger.info(f"Marked messages as read for wa_id: {wa_id}, phone_id: {phone_id}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error marking messages as read for wa_id {wa_id} in {table_name}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
            phone_number_id = data["entry"][0]["changes"][0]["value"].get("metadata", {}).get("phone_number_id")
            if not phone_number_id or phone_number_id not in PHONE_ID_TO_TABLE:
                logger.error(f"Unknown phone_number_id: {phone_number_id}")
                return jsonify({"status": "error", "message": "Unknown phone_number_id"}), 400
            
            process_whatsapp_message(data, phone_number_id)
            return jsonify({"status": "received"})
        else:
            logger.error("Invalid WhatsApp message structure")
            return jsonify({"status": "error", "message": "Invalid message structure"}), 400