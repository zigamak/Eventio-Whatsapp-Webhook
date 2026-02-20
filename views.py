from flask import Blueprint, request, render_template, jsonify
from utils.whatsapp_utils import (
    process_whatsapp_message, send_message, send_image_message, 
    download_whatsapp_image, get_table_name, get_text_message_input
)
from utils.db_manager import db_manager
from config import (
    VERIFY_TOKEN, ACCOUNT1_PHONE_ID_EVENTIO, ACCOUNT1_PHONE_ID_PACKAGE, ACCOUNT2_PHONE_ID
)
from datetime import datetime
import logging
import base64
import os
from werkzeug.utils import secure_filename

bp = Blueprint('whatsapp', __name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Webhook for both Meta Business Accounts (Eventio/Package and Ignitio)."""
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        if verify_token == VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            return request.args.get('hub.challenge')
        logger.error(f"Webhook verification failed: Invalid token {verify_token}")
        return "Verification failed", 403

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            logger.error("No data received in webhook")
            return jsonify({'status': 'error', 'message': 'No data received'}), 400

        phone_number_id = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('metadata', {}).get('phone_number_id')
        if not phone_number_id:
            logger.error("No phone_number_id in webhook data")
            return jsonify({'status': 'error', 'message': 'Invalid webhook data'}), 400

        logger.debug(f"Processing webhook for phone_number_id: {phone_number_id}")
        result = process_whatsapp_message(db_manager, data, phone_number_id)
        if result:
            return jsonify(result), 200
        return jsonify({'status': 'error', 'message': 'Failed to process message'}), 500

@bp.route('/eventio')
def eventio():
    """Render Eventio page."""
    logger.debug(f"Rendering eventio page with phone_id: {ACCOUNT1_PHONE_ID_EVENTIO}")
    return render_template('eventio.html', phone_id=ACCOUNT1_PHONE_ID_EVENTIO)

@bp.route('/')
def package_with_sense():
    """Render Package with Sense page (now the default root page)."""
    logger.debug(f"Rendering package_with_sense page with phone_id: {ACCOUNT1_PHONE_ID_PACKAGE}")
    return render_template('index.html', phone_id=ACCOUNT1_PHONE_ID_PACKAGE)

@bp.route('/ignitiohub')
def ignitiohub():
    """Render Ignitio Hub page."""
    logger.debug(f"Rendering ignitiohub page with phone_id: {ACCOUNT2_PHONE_ID}")
    return render_template('ignitiohub.html', phone_id=ACCOUNT2_PHONE_ID)

@bp.route('/send_message', methods=['POST'])
def send_message_route():
    """Send a WhatsApp message (text or image)."""
    data = request.get_json()
    phone_id = data.get('phone_id')
    if not phone_id:
        logger.error("No phone_id provided in send_message request")
        return jsonify({'status': 'error', 'message': 'Phone ID required'}), 400

    message_type = data.get('type')
    logger.debug(f"Sending message with phone_id: {phone_id}, type: {message_type}")

    if message_type == 'image':
        recipient = data.get('to')
        image_url = data.get('image', {}).get('link')
        caption = data.get('image', {}).get('caption', '')
        result = send_image_message(recipient, image_url, caption, phone_id)
    else:
        result = send_message(data, phone_id)

    if result:
        return jsonify(result), 200
    return jsonify({'status': 'error', 'message': 'Failed to send message'}), 500

@bp.route('/get_image/<image_id>/<phone_id>')
def get_image(image_id, phone_id):
    """Download and return a WhatsApp image URL."""
    logger.debug(f"Downloading image {image_id} for phone_id {phone_id}")
    image_url = download_whatsapp_image(image_id, phone_id)
    if image_url:
        return jsonify({
            'status': 'success',
            'image_url': image_url
        })
    return jsonify({'status': 'error', 'message': 'Failed to download image'}), 500

@bp.route('/messages/<phone_id>')
def get_messages(phone_id):
    """Retrieve messages for a given phone_id."""
    try:
        table_name = get_table_name(phone_id)
        logger.debug(f"Fetching messages from {table_name} for phone_id {phone_id}")
        messages = db_manager.execute_query(
            f"SELECT * FROM {table_name} ORDER BY timestamp DESC",
            fetch=True
        )
        return jsonify(messages)
    except Exception as e:
        logger.error(f"Error fetching messages for phone_id {phone_id}: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to fetch messages'}), 500

# NEW API ENDPOINTS FOR THE CHAT INTERFACE

@bp.route('/api/chats', methods=['GET'])
def get_chats():
    """Get all chats grouped by wa_id with last message info."""
    try:
        phone_id = request.args.get('phone_id')
        if not phone_id:
            return jsonify({'status': 'error', 'message': 'Phone ID required'}), 400
        
        table_name = get_table_name(phone_id)
        logger.debug(f"Fetching chats from {table_name}")
        
        # Use subquery to get last message per wa_id
        query = f"""
            WITH latest_messages AS (
                SELECT DISTINCT ON (wa_id)
                    wa_id,
                    name,
                    timestamp as last_message_timestamp,
                    body as last_body
                FROM {table_name}
                ORDER BY wa_id, timestamp DESC
            ),
            unread_counts AS (
                SELECT 
                    wa_id,
                    COUNT(*) as unread_count
                FROM {table_name}
                WHERE direction = 'inbound' AND read = FALSE
                GROUP BY wa_id
            )
            SELECT 
                lm.wa_id,
                lm.name,
                lm.last_message_timestamp,
                lm.last_body,
                COALESCE(uc.unread_count, 0) as unread_count
            FROM latest_messages lm
            LEFT JOIN unread_counts uc ON lm.wa_id = uc.wa_id
            ORDER BY lm.last_message_timestamp DESC
        """
        
        chats = db_manager.execute_query(query, fetch=True)
        return jsonify({'status': 'success', 'chats': chats})
    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/chats/<wa_id>', methods=['GET'])
def get_chat_messages(wa_id):
    """Get all messages for a specific chat."""
    try:
        phone_id = request.args.get('phone_id')
        if not phone_id:
            return jsonify({'status': 'error', 'message': 'Phone ID required'}), 400
        
        table_name = get_table_name(phone_id)
        logger.debug(f"Fetching messages for wa_id {wa_id} from {table_name}")
        
        query = f"""
            SELECT * FROM {table_name}
            WHERE wa_id = %s
            ORDER BY timestamp ASC
        """
        
        messages = db_manager.execute_query(query, (wa_id,), fetch=True)
        return jsonify({'status': 'success', 'messages': messages})
    except Exception as e:
        logger.error(f"Error fetching messages for wa_id {wa_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/mark-read', methods=['POST'])
def mark_read():
    """Mark all messages from a wa_id as read."""
    try:
        data = request.get_json()
        wa_id = data.get('wa_id')
        phone_id = data.get('phone_id')
        
        if not wa_id or not phone_id:
            return jsonify({'status': 'error', 'message': 'wa_id and phone_id required'}), 400
        
        table_name = get_table_name(phone_id)
        logger.debug(f"Marking messages as read for wa_id {wa_id} in {table_name}")
        
        query = f"""
            UPDATE {table_name}
            SET read = TRUE
            WHERE wa_id = %s AND direction = 'inbound' AND read = FALSE
        """
        
        db_manager.execute_query(query, (wa_id,))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
@bp.route('/api/respond', methods=['POST'])
def respond():
    """Send a text message response."""
    try:
        data = request.get_json()
        wa_id = data.get('wa_id')
        message = data.get('message')
        phone_id = data.get('phone_id')
        name = data.get('name', 'Unknown')
        
        logger.info(f"=== RESPOND ENDPOINT CALLED ===")
        logger.info(f"wa_id: {wa_id}")
        logger.info(f"message: {message}")
        logger.info(f"phone_id: {phone_id}")
        logger.info(f"name: {name}")
        
        if not wa_id or not message or not phone_id:
            logger.error("Missing required fields")
            return jsonify({'status': 'error', 'message': 'wa_id, message, and phone_id required'}), 400
        
        # Send via WhatsApp API
        payload = get_text_message_input(wa_id, message)
        logger.info(f"Sending message with payload: {payload}")
        
        result = send_message(payload, phone_id)
        
        if result and result.get('messages'):
            # Extract the message ID from WhatsApp response
            whatsapp_message_id = result.get('messages', [{}])[0].get('id')
            
            if not whatsapp_message_id:
                logger.error("No message ID in WhatsApp response")
                return jsonify({'status': 'error', 'message': 'No message ID returned from WhatsApp'}), 500
            
            # Save to database
            table_name = get_table_name(phone_id)
            message_data = {
                'id': whatsapp_message_id,  # Use the actual WhatsApp message ID
                'wa_id': wa_id,
                'name': name,
                'type': 'text',
                'body': message,
                'timestamp': datetime.now(),
                'direction': 'outbound',
                'status': 'sent',
                'read': True,
                'image_url': None,
                'image_id': None
            }
            
            logger.info(f"Saving message to database: {message_data}")
            db_manager.insert_message(table_name, message_data)
            logger.info("Message saved successfully")
            
            return jsonify({'status': 'success', 'result': result})
        else:
            error_msg = 'Failed to send message - no response from WhatsApp API'
            if result:
                error_msg = f'Failed to send message - WhatsApp response: {result}'
            logger.error(error_msg)
            return jsonify({'status': 'error', 'message': error_msg}), 500
            
    except Exception as e:
        logger.error(f"Error in respond endpoint: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@bp.route('/api/send-image', methods=['POST'])
def send_image():
    """Send an image message."""
    try:
        wa_id = request.form.get('wa_id')
        phone_id = request.form.get('phone_id')
        caption = request.form.get('caption', '')
        name = request.form.get('name', 'Unknown')
        image_file = request.files.get('image')
        
        if not wa_id or not phone_id or not image_file:
            return jsonify({'status': 'error', 'message': 'wa_id, phone_id, and image required'}), 400
        
        # Save image temporarily
        uploads_dir = "static/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        filename = secure_filename(f"{datetime.now().timestamp()}_{image_file.filename}")
        filepath = os.path.join(uploads_dir, filename)
        image_file.save(filepath)
        
        # Get full URL (you may need to adjust this based on your deployment)
        image_url = request.url_root.rstrip('/') + f"/static/uploads/{filename}"
        
        # Send via WhatsApp API
        result = send_image_message(wa_id, image_url, caption, phone_id)
        
        if result:
            # Save to database
            table_name = get_table_name(phone_id)
            message_data = {
                'id': result.get('messages', [{}])[0].get('id', f"out_{datetime.now().timestamp()}"),
                'wa_id': wa_id,
                'name': name,
                'type': 'image',
                'body': f"📷 Image{(' - ' + caption) if caption else ''}",
                'timestamp': datetime.now(),
                'direction': 'outbound',
                'status': 'sent',
                'read': True,
                'image_url': f"/static/uploads/{filename}",
                'image_id': None
            }
            db_manager.insert_message(table_name, message_data)
            return jsonify({'status': 'success', 'result': result})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send image'}), 500
    except Exception as e:
        logger.error(f"Error sending image: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/log-outbound', methods=['POST'])
def log_outbound():
    """Receive outbound message log from Apps Script or PHP dashboard."""
    try:
        data = request.get_json()
        wa_id = data.get('wa_id')
        phone_id = data.get('phone_id')
        name = data.get('name', 'Unknown')
        message_body = data.get('body', '')
        message_id = data.get('message_id')  # WhatsApp message ID returned after send
        message_type = data.get('type', 'template')

        if not wa_id or not phone_id or not message_id:
            return jsonify({'status': 'error', 'message': 'wa_id, phone_id, and message_id required'}), 400

        table_name = get_table_name(phone_id)
        message_data = {
            'id': message_id,
            'wa_id': wa_id,
            'name': name,
            'type': message_type,
            'body': message_body,
            'timestamp': datetime.now(),
            'direction': 'outbound',
            'status': 'sent',
            'read': False,
            'image_url': None,
            'image_id': None
        }

        db_manager.insert_message(table_name, message_data)
        logger.info(f"Logged outbound message {message_id} for {wa_id}")
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Error logging outbound message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500