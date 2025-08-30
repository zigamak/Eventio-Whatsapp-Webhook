import logging
import os
from datetime import datetime
import requests
from .db_manager import db_manager
from config import WHATSAPP_ACCESS_TOKEN, VERSION

# Set up logging
logger = logging.getLogger(__name__)

# Map phone IDs to table names
PHONE_ID_TO_TABLE = {
    'EVENTIO_PHONE_ID': 'eventio_messages',
    'PACKAGE_WITH_SENSE_PHONE_ID': 'package_with_sense_messages'
}

def get_table_name(phone_id):
    """
    Get the appropriate table name for a given phone ID.
    
    Args:
        phone_id (str): Phone number ID.
    
    Returns:
        str: Corresponding table name.
    """
    return PHONE_ID_TO_TABLE.get(phone_id, 'eventio_messages')

def save_message(message_data, phone_id):
    """
    Save a message to the PostgreSQL database.
    
    Args:
        message_data (dict): Message data to save.
        phone_id (str): Phone number ID to determine the table.
    """
    try:
        table_name = get_table_name(phone_id)
        # Updated to include image fields
        query = """
            SELECT insert_message(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        params = (
            table_name,
            message_data['id'],
            message_data['wa_id'],
            message_data['name'],
            message_data['type'],
            message_data['body'],
            message_data['timestamp'],
            message_data['direction'],
            message_data['status'],
            message_data['read'],
            message_data.get('image_url'),
            message_data.get('image_id')
        )
        db_manager.execute_query(query, params)
        logger.info(f"Message saved to {table_name}: {message_data}")
    except Exception as e:
        logger.error(f"Error saving message to {table_name}: {e}")

def get_text_message_input(recipient, text):
    """
    Prepare the payload for sending a text message via WhatsApp API.
    
    Args:
        recipient (str): WhatsApp ID of the recipient.
        text (str): Message text.
    
    Returns:
        dict: Payload for the WhatsApp API.
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }

def get_image_message_input(recipient, image_url, caption=""):
    """
    Prepare the payload for sending an image message via WhatsApp API.
    
    Args:
        recipient (str): WhatsApp ID of the recipient.
        image_url (str): URL of the image to send.
        caption (str): Optional caption for the image.
    
    Returns:
        dict: Payload for the WhatsApp API.
    """
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    
    if caption:
        payload["image"]["caption"] = caption
    
    return payload

def send_message(data, phone_id):
    """
    Send a message via the WhatsApp API.
    
    Args:
        data (dict): Payload for the WhatsApp API.
        phone_id (str): Phone number ID for the API request.
    
    Returns:
        tuple: (Response object, HTTP status code)
    """
    url = f"https://graph.facebook.com/{VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response, response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message: {e}")
        return {"error": str(e)}, 500

def send_image_message(recipient, image_url, caption="", phone_id=None):
    """
    Send an image message via WhatsApp Business API.
    
    Args:
        recipient (str): WhatsApp ID of the recipient.
        image_url (str): URL of the image to send.
        caption (str): Optional caption for the image.
        phone_id (str): Phone number ID for the API request.
    
    Returns:
        tuple: (Response object, HTTP status code)
    """
    payload = get_image_message_input(recipient, image_url, caption)
    return send_message(payload, phone_id)

def download_whatsapp_image(image_id, phone_id):
    """
    Download image from WhatsApp Media API and return local file path.
    
    Args:
        image_id (str): WhatsApp media ID.
        phone_id (str): Phone number ID for authentication.
    
    Returns:
        str or None: Local file path if successful, None if failed.
    """
    try:
        # Step 1: Get media URL
        url = f"https://graph.facebook.com/{VERSION}/{image_id}"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        }
        
        response = requests.get(url, headers=headers)
        if not response.ok:
            logger.error(f"Failed to get media URL: {response.text}")
            return None
            
        media_data = response.json()
        media_url = media_data.get('url')
        
        if not media_url:
            logger.error("No media URL in response")
            return None
        
        # Step 2: Download the actual image
        image_response = requests.get(media_url, headers=headers)
        if not image_response.ok:
            logger.error(f"Failed to download image: {image_response.text}")
            return None
        
        # Step 3: Save to local file
        uploads_dir = "static/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Determine file extension from content type
        content_type = image_response.headers.get('content-type', '')
        if 'jpeg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        else:
            ext = '.jpg'  # default
        
        filename = f"{image_id}{ext}"
        filepath = os.path.join(uploads_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_response.content)
        
        # Return web-accessible path
        return f"/static/uploads/{filename}"
        
    except Exception as e:
        logger.error(f"Error downloading image {image_id}: {e}")
        return None

def process_image_message(message_data, contact_info, phone_id):
    """
    Process incoming image message.
    
    Args:
        message_data (dict): Image message data from webhook.
        contact_info (dict): Contact information.
        phone_id (str): Phone number ID.
    
    Returns:
        dict or None: Message info if successful, None if failed.
    """
    try:
        image_id = message_data.get('image', {}).get('id')
        mime_type = message_data.get('image', {}).get('mime_type')
        sha256 = message_data.get('image', {}).get('sha256')
        
        # Download the image
        image_url = download_whatsapp_image(image_id, phone_id)
        
        message_info = {
            "id": message_data["id"],
            "wa_id": contact_info["wa_id"],
            "name": contact_info["name"],
            "type": "image",
            "body": f"📷 Image ({mime_type})" if mime_type else "📷 Image",
            "timestamp": datetime.fromtimestamp(int(message_data["timestamp"])).isoformat(),
            "direction": "inbound",
            "status": "delivered",
            "read": False,
            "image_url": image_url,
            "image_id": image_id
        }
        
        save_message(message_info, phone_id)
        logger.info(f"Image message processed and saved: {message_info['id']}")
        return message_info
        
    except Exception as e:
        logger.error(f"Error processing image message: {e}")
        return None

def is_valid_whatsapp_message(body):
    """
    Validate the structure of a WhatsApp webhook payload.
    
    Args:
        body (dict): Webhook payload.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        value = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        is_message = "messages" in value and len(value.get("messages", [])) > 0
        is_status = "statuses" in value and len(value.get("statuses", [])) > 0
        
        return (
            body.get("object") == "whatsapp_business_account" and
            (is_message or is_status)
        )
    except (TypeError, IndexError):
        return False

def process_whatsapp_message(body, phone_id):
    """
    Process an incoming WhatsApp message or status update and save it to the database.
    
    Args:
        body (dict): Webhook payload.
        phone_id (str): Phone number ID to determine the table.
    """
    try:
        change = body["entry"][0]["changes"][0]["value"]
        table_name = get_table_name(phone_id)
        
        if "messages" in change:
            messages = change.get("messages", [])
            contacts = change.get("contacts", [])
            
            if not messages or not contacts:
                logger.warning("No messages or contacts found in webhook payload")
                return
            
            message = messages[0]
            contact = contacts[0]
            
            wa_id = message["from"]
            name = contact.get("profile", {}).get("name", "Unknown Contact")
            
            contact_info = {
                "wa_id": wa_id,
                "name": name
            }
            
            message_type = message.get('type')
            
            # Handle only supported message types (text and image)
            if message_type == "text":
                message_body = message["text"]["body"]
                
                message_data = {
                    "id": message["id"],
                    "wa_id": wa_id,
                    "name": name,
                    "type": "text",
                    "body": message_body,
                    "timestamp": datetime.fromtimestamp(int(message["timestamp"])).isoformat(),
                    "direction": "inbound",
                    "status": "delivered",
                    "read": False,
                    "image_url": None,
                    "image_id": None
                }
                
                save_message(message_data, phone_id)
                logger.info(f"Processed incoming text message from {wa_id}: {message_body}")
                
            elif message_type == "image":
                # Process image message
                process_image_message(message, contact_info, phone_id)
                logger.info(f"Processed incoming image message from {wa_id}")
                
            else:
                # Ignore unsupported message types
                logger.debug(f"Ignoring unsupported message type: {message_type} from {wa_id}")
                return
        
        elif "statuses" in change:
            status = change["statuses"][0]
            message_id = status.get('id')
            new_status = status.get('status')
            
            query = """
                SELECT update_message_status(%s, %s, %s, %s)
            """
            params = (
                table_name,
                message_id,
                new_status,
                new_status == 'read'
            )
            db_manager.execute_query(query, params)
            logger.info(f"Updated message status. ID: {message_id}, Status: {new_status}")
        
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error processing WhatsApp message: Invalid payload structure - {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing WhatsApp message: {e}")