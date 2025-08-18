import json
import os
import logging
import requests
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def load_messages(file_path):
    """
    Load messages from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file.
    
    Returns:
        list: List of message dictionaries.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading messages from {file_path}: {e}")
        return []

def save_message(message_data, file_path):
    """
    Save a message to the specified JSON file.
    
    Args:
        message_data (dict): Message data to save.
        file_path (str): Path to the JSON file.
    """
    try:
        messages = load_messages(file_path)
        messages.append(message_data)
        with open(file_path, 'w') as f:
            json.dump(messages, f, indent=4)
        logger.info(f"Message saved to {file_path}: {message_data}")
    except Exception as e:
        logger.error(f"Error saving message to {file_path}: {e}")

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

def send_message(data, phone_id):
    """
    Send a message via the WhatsApp API.
    
    Args:
        data (dict): Payload for the WhatsApp API.
        phone_id (str): Phone number ID for the API request.
    
    Returns:
        tuple: (Response object, HTTP status code)
    """
    from config import WHATSAPP_ACCESS_TOKEN, VERSION  # Import here to avoid circular imports
    url = f"https://graph.facebook.com/{VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        return response, response.status_code
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return {"error": str(e)}, 500

def is_valid_whatsapp_message(body):
    """
    Validate the structure of a WhatsApp webhook payload.
    
    Args:
        body (dict): Webhook payload.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        # Check for both incoming messages and status updates
        value = body["entry"][0]["changes"][0]["value"]
        is_message = "messages" in value and len(value["messages"]) > 0
        is_status = "statuses" in value and len(value["statuses"]) > 0
        
        return (
            "object" in body and
            body["object"] == "whatsapp_business_account" and
            "entry" in body and
            len(body["entry"]) > 0 and
            "changes" in body["entry"][0] and
            len(body["entry"][0]["changes"]) > 0 and
            (is_message or is_status)
        )
    except (KeyError, TypeError):
        return False

def process_whatsapp_message(body, file_path):
    """
    Process an incoming WhatsApp message and save it to the JSON file.
    
    Args:
        body (dict): Webhook payload.
        file_path (str): Path to the JSON file.
    """
    try:
        entry = body["entry"][0]
        change = entry["changes"][0]["value"]
        
        # Check if the webhook is for a new incoming message
        if "messages" in change:
            messages = change.get("messages", [])
            contacts = change.get("contacts", [])
            
            if not messages or not contacts:
                logger.warning("No messages or contacts found in webhook payload")
                return
            
            wa_id = messages[0]["from"]
            name = contacts[0].get("profile", {}).get("name", "Unknown Contact")
            message_body = messages[0]["text"]["body"]
            timestamp = messages[0]["timestamp"]
            
            message_data = {
                "id": messages[0]["id"],
                "wa_id": wa_id,
                "name": name,
                "type": "text",
                "body": message_body,
                "timestamp": datetime.fromtimestamp(int(timestamp)).isoformat(),
                "direction": "inbound",
                "status": "delivered"
            }
            
            save_message(message_data, file_path)
            logger.info(f"Processed incoming message from {wa_id}: {message_body}")
        
        # Check if the webhook is for a message status update
        elif "statuses" in change:
            status = change["statuses"][0]
            logger.info(f"Received message status update. ID: {status.get('id')}, Status: {status.get('status')}")
            # You could add code here to update the message status in your JSON file.

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
