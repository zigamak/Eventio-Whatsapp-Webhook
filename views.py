from flask import Blueprint, request, render_template, jsonify
from utils.whatsapp_utils import process_whatsapp_message, send_message, send_image_message, download_whatsapp_image, get_table_name
from utils.db_manager import db_manager
from config import (
    VERIFY_TOKEN, ACCOUNT1_PHONE_ID_EVENTIO, ACCOUNT1_PHONE_ID_PACKAGE, ACCOUNT2_PHONE_ID
)
import logging
import base64

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

@bp.route('/') # Changed from '/package_with_sense' to '/' to make it the default
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