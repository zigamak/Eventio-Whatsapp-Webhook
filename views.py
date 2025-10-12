from flask import Blueprint, render_template, jsonify, request
from config import WHATSAPP_ACCESS_TOKEN, EVENTIO_PHONE_ID, PACKAGE_WITH_SENSE_PHONE_ID, VERSION, VERIFY_TOKEN
import logging
import requests
import os
from datetime import datetime
from utils.whatsapp_utils import process_whatsapp_message, is_valid_whatsapp_message, get_text_message_input, send_message, get_table_name, save_message, send_image_message
from utils.db_manager import db_manager

bp = Blueprint('main', __name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/chats', methods=['GET'])
def get_chats():
    phone_id = request.args.get('phone_id')
    if not phone_id:
        logger.error("Missing phone_id in request")
        return jsonify({"message": "Missing phone_id"}), 400
    
    try:
        table_name = get_table_name(phone_id)
        
        # Direct query to get chats with last message timestamp
        # This bypasses the get_chats() function and queries directly
        chats = db_manager.execute_query(
            f"""
            SELECT DISTINCT 
                m.wa_id,
                m.name,
                MAX(m.timestamp) as last_message_timestamp
            FROM {table_name} m
            GROUP BY m.wa_id, m.name
            ORDER BY last_message_timestamp DESC
            """,
            fetch=True
        )
        
        # Debug: Log the actual structure of the returned data
        if chats:
            logger.info(f"Sample chat structure: {dict(chats[0])}")
            logger.info(f"Available columns: {list(chats[0].keys())}")
        
        formatted_chats = []
        for chat in chats:
            try:
                # Handle different possible column names for timestamp
                timestamp_value = None
                available_keys = list(chat.keys())
                
                # Check for various timestamp column names
                timestamp_keys = ['last_message_timestamp', 'timestamp', 'max_timestamp', 'latest_timestamp']
                for key in timestamp_keys:
                    if key in chat:
                        timestamp_value = chat[key]
                        break
                
                if timestamp_value is None:
                    logger.warning(f"No timestamp found in chat data. Available keys: {available_keys}")
                
                formatted_chat = {
                    'wa_id': chat.get('wa_id', ''),
                    'name': chat.get('name') or f"Unknown Contact ({chat.get('wa_id', 'Unknown')})",
                    'last_message_timestamp': timestamp_value.isoformat() if timestamp_value else None
                }
                formatted_chats.append(formatted_chat)
                
            except Exception as chat_error:
                logger.error(f"Error processing individual chat: {chat_error}, Chat data: {dict(chat)}")
                continue
        
        logger.info(f"Fetched {len(formatted_chats)} chats for phone_id: {phone_id}")
        return jsonify({"chats": formatted_chats})
        
    except Exception as e:
        logger.error(f"Error fetching chats for phone_id {phone_id}: {e}")
        # Add more detailed error information
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"message": "Error fetching chats", "error": str(e)}), 500

@bp.route('/api/chats/<wa_id>', methods=['GET'])
def get_messages(wa_id):
    phone_id = request.args.get('phone_id')
    if not phone_id:
        logger.error("Missing phone_id in request")
        return jsonify({"message": "Missing phone_id"}), 400
    
    try:
        table_name = get_table_name(phone_id)
        
        # Direct query to get messages
        messages = db_manager.execute_query(
            f"""
            SELECT 
                id,
                wa_id,
                name,
                type,
                body,
                timestamp,
                direction,
                status,
                read,
                image_url,
                image_id
            FROM {table_name} 
            WHERE wa_id = %s 
            ORDER BY timestamp ASC
            """,
            (wa_id,),
            fetch=True
        )
        
        formatted_messages = []
        for msg in messages:
            try:
                formatted_message = {
                    'id': msg.get('id', 'N/A'),
                    'wa_id': msg.get('wa_id', ''),
                    'body': msg.get('body') or '',
                    'image_url': msg.get('image_url'),
                    'image_id': msg.get('image_id'),
                    'type': msg.get('type', 'text'),
                    'direction': msg.get('direction', 'inbound'),
                    'timestamp': msg.get('timestamp').isoformat() if msg.get('timestamp') else None,
                    'status': msg.get('status', 'delivered'),
                    'read': msg.get('read', False)
                }
                formatted_messages.append(formatted_message)
            except Exception as msg_error:
                logger.error(f"Error processing individual message: {msg_error}, Message data: {dict(msg)}")
                continue
        
        logger.info(f"Fetched {len(formatted_messages)} messages for wa_id: {wa_id}, phone_id: {phone_id}")
        return jsonify({"messages": formatted_messages})
        
    except Exception as e:
        logger.error(f"Error fetching messages for wa_id {wa_id} from phone_id {phone_id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"message": "Error fetching messages", "error": str(e)}), 500

@bp.route('/api/respond', methods=['POST'])
def respond():
    data = request.get_json()
    wa_id = data.get('wa_id')
    message = data.get('message')
    phone_id = data.get('phone_id')
    
    if not wa_id or not message or not phone_id:
        logger.error("Missing wa_id, message, or phone_id in request")
        return jsonify({"message": "Missing wa_id, message, or phone_id"}), 400
    
    try:
        payload = get_text_message_input(wa_id, message)
        response, status_code = send_message(payload, phone_id)
        
        if response and response.ok:
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
                "read": True,
                "image_url": None,
                "image_id": None
            }
            save_message(db_manager, message_data, phone_id)
            logger.info(f"Message sent to {wa_id} via phone_id {phone_id}: {message}")
            return jsonify({
                "status": "success",
                "message_id": message_data["id"],
                "wa_id": message_data["wa_id"],
                "body": message_data["body"],
                "type": message_data["type"],
                "direction": message_data["direction"],
                "timestamp": message_data["timestamp"],
                "status": message_data["status"],
                "read": message_data["read"],
                "image_url": message_data["image_url"],
                "image_id": message_data["image_id"]
            }), 200
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error') if response else response.text
            logger.error(f"Failed to send message. Status: {status_code}, Response: {error_msg}")
            return jsonify({"status": "error", "message": f"Failed to send message: {error_msg}"}), status_code
    except Exception as e:
        logger.error(f"Error in respond endpoint: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/api/send-image', methods=['POST'])
def send_image():
    try:
        wa_id = request.form.get('wa_id')
        phone_id = request.form.get('phone_id')
        image = request.files.get('image')
        caption = request.form.get('caption', '')
        
        if not wa_id or not phone_id or not image:
            logger.error("Missing wa_id, phone_id, or image")
            return jsonify({"message": "Missing wa_id, phone_id, or image"}), 400
        
        uploads_dir = "static/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        filepath = os.path.join(uploads_dir, filename)
        image.save(filepath)
        image_url = f"{request.url_root}static/uploads/{filename}"
        
        response, status_code = send_image_message(wa_id, image_url, caption, phone_id)
        
        if response and response.ok:
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
            save_message(db_manager, message_data, phone_id)
            logger.info(f"Image sent to {wa_id} via phone_id {phone_id}")
            return jsonify({
                "status": "success",
                "message_id": message_data["id"],
                "wa_id": message_data["wa_id"],
                "body": message_data["body"],
                "type": message_data["type"],
                "direction": message_data["direction"],
                "timestamp": message_data["timestamp"],
                "status": message_data["status"],
                "read": message_data["read"],
                "image_url": message_data["image_url"],
                "image_id": message_data["image_id"]
            }), 200
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error') if response else response.text
            logger.error(f"Failed to send image. Status: {status_code}, Response: {error_msg}")
            return jsonify({"status": "error", "message": f"Failed to send image: {error_msg}"}), status_code
    except Exception as e:
        logger.error(f"Error in send_image endpoint: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/api/mark-read', methods=['POST'])
def mark_read():
    data = request.get_json()
    wa_id = data.get('wa_id')
    phone_id = data.get('phone_id')
    
    if not wa_id or not phone_id:
        logger.error("Missing wa_id or phone_id in request")
        return jsonify({"message": "Missing wa_id or phone_id"}), 400
    
    try:
        table_name = get_table_name(phone_id)
        
        # Direct query to mark messages as read
        db_manager.execute_query(
            f"""
            UPDATE {table_name} 
            SET read = true 
            WHERE wa_id = %s AND direction = 'inbound'
            """,
            (wa_id,)
        )
        
        logger.info(f"Marked messages as read for wa_id: {wa_id}, phone_id: {phone_id}")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error marking messages as read for wa_id {wa_id} in phone_id {phone_id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
            if not phone_number_id:
                logger.error("Missing phone_number_id in webhook payload")
                return jsonify({"status": "error", "message": "Missing phone_number_id"}), 400
            try:
                process_whatsapp_message(db_manager, data, phone_number_id)
                return jsonify({"status": "received"})
            except Exception as e:
                logger.error(f"Error processing webhook for phone_number_id {phone_number_id}: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            logger.error("Invalid WhatsApp message structure")
            return jsonify({"status": "error", "message": "Invalid message structure"}), 400