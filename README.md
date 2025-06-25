WhatsApp Message Portal
This Flask-based application provides a simple web interface to view incoming WhatsApp messages and send replies using the WhatsApp Business Cloud API. It acts as a basic customer support portal, allowing you to manage conversations from a centralized dashboard.

✨ Features
View Incoming Messages: See all messages received by your WhatsApp Business number.

Conversation Grouping: Messages are grouped by sender for easy conversation tracking.

Send Replies: Respond to users directly from the web interface.

Local JSON Storage: Messages are stored in a local messages.json file (suitable for prototyping).

Responsive UI: Basic web interface designed with Tailwind CSS for readability on different screen sizes.

🚀 Prerequisites
Before you begin, ensure you have the following:

Python 3.x: Installed on your machine.

pip: Python package installer (usually comes with Python).

A Meta (Facebook) Developer Account: Required to access the Meta Developers Dashboard.

A WhatsApp Business Account (WABA): Set up and linked to your Meta Developer App.

A WhatsApp Business API Phone Number: Configured within your WABA.

ACCESS_TOKEN: A valid and non-expired access token from your Meta Developers App Dashboard (under WhatsApp > API Setup).

PHONE_NUMBER_ID: The ID of your WhatsApp Business API phone number.

VERIFY_TOKEN: A custom string you will define and use for webhook verification.

ngrok (for local testing): A tool to expose your local Flask server to the internet, allowing Meta to send webhook notifications to your local machine. Download from ngrok.com.

📁 Project Structure
whatsapp-portal/
├── APP/
│   ├── __init__.py           # Flask app creation and blueprint registration
│   ├── config.py             # Configuration settings for WhatsApp API
│   ├── messages.json         # Stores all incoming/outgoing messages (created automatically)
│   ├── UTILS/
│   │   └── whatsapp_utils.py # Utility functions for WhatsApp API interaction and message handling
│   ├── STATIC/
│   │   └── index.html        # The main web interface for the portal
│   └── views.py              # Flask blueprints for webhook and portal routes
└── run.py                    # Main script to run the Flask application

⚙️ Setup and Installation
Follow these steps to get the WhatsApp Portal running on your local machine:

Clone the repository (or set up the files manually):

git clone https://github.com/your-username/whatsapp-portal.git # Replace with your repo URL
cd whatsapp-portal

If you've been working with the files directly, ensure your local directory structure matches the one above.

Create a Python Virtual Environment (Recommended):

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install Dependencies:

pip install -r requirements.txt

If you don't have requirements.txt, create one in the whatsapp-portal/ root directory with the following content and then run the command above:

Flask
requests
gunicorn  # Only needed for production deployment, but good to include

Configure APP/config.py:
Open the APP/config.py file and update the following variables with your actual credentials from the Meta Developers Dashboard:

# APP/config.py
ACCESS_TOKEN = "YOUR_WHATSAPP_ACCESS_TOKEN"         # From Meta Developers > WhatsApp > API Setup
VERIFY_TOKEN = "YOUR_CHOSEN_WEBHOOK_VERIFY_TOKEN"   # A string you make up (e.g., "mysecrettoken123")
PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"           # From Meta Developers > WhatsApp > API Setup

# Optional, but recommended to fill out if you intend to use them later or for completeness
RECIPIENT_WAID = "OPTIONAL_DEFAULT_RECIPIENT_WA_ID" # For testing, e.g., your own WhatsApp number (with country code, no '+')
VERSION = "v19.0"                                   # Current WhatsApp API version (check Meta docs)
APP_ID = "YOUR_FACEBOOK_APP_ID"                     # From Meta Developers > App Settings > Basic
APP_SECRET = "YOUR_FACEBOOK_APP_SECRET"             # From Meta Developers > App Settings > Basic
WEBHOOK_URL = "YOUR_PUBLIC_WEBHOOK_URL"             # Will be filled after ngrok/deployment

SECRET_KEY = "YOUR_VERY_STRONG_FLASK_SECRET_KEY"    # Crucial for Flask security
DEBUG = True                                        # Set to False for production

Make sure all YOUR_... placeholders are replaced with actual values.

🏃 Running the Application Locally
Start ngrok (for webhook receiving):
Open a new terminal window (leave your Flask app terminal open) and run:

ngrok http 8000
```ngrok` will give you a public HTTPS URL (e.g., `[https://abcdef12345.ngrok-free.app](https://abcdef12345.ngrok-free.app)`). **Copy this URL**, as you'll need it for the webhook setup. This URL will forward requests to your local Flask app running on port 8000.


Start the Flask App:
In your original terminal where your virtual environment is active, run:

python run.py

You should see Flask's development server starting up, typically on http://127.0.0.1:8000/.

Access the Web Portal:
Open your web browser and navigate to http://127.0.0.1:8000/. You should see the WhatsApp Portal interface.

🔗 Webhook Configuration in Meta Developers Dashboard
For your portal to receive messages from WhatsApp users, you need to tell Meta where to send them (your webhook URL).

Go to your Meta Developers App Dashboard.

Select your application.

In the left sidebar, navigate to WhatsApp > API Setup.

Scroll down to the "Webhooks" section.

Click Configure a webhook (or "Edit webhook" if already configured).

Callback URL: Paste the ngrok HTTPS URL you copied (e.g., https://abcdef12345.ngrok-free.app) followed by /webhook.
Example: https://abcdef12345.ngrok-free.app/webhook

Verify Token: Enter the exact VERIFY_TOKEN string you defined in your APP/config.py.

Click Verify and Save.

After verification, click Manage next to "Webhooks" to subscribe to events.

Find the messages field and click Subscribe. This will ensure your application receives notifications for incoming user messages and message status updates (sent, delivered, read).

👨‍💻 Usage
Receiving Messages: Once the webhook is configured, send a message to your WhatsApp Business phone number from any personal WhatsApp account. You should see the message appear in your portal's conversation list and the chat display after a few seconds (due to the 5-second refresh interval).

Sending Replies:

Click on a conversation in the left panel.

Type your message into the input field at the bottom.

Click the "Send" button (or press Enter).

The message will be sent to the user and recorded in your portal.

☁️ Hosting Online (Deployment)
The local setup is great for development, but for a live, always-on portal, you'll need to deploy it to a hosting provider.

Important Considerations for Online Hosting:

Production WSGI Server: You must use a production-ready WSGI server like Gunicorn (already included in requirements.txt) to serve your Flask app. You'll typically use a command like gunicorn run:app on your server.

Environment Variables: Crucially, do not commit your config.py with sensitive data directly to a public Git repository. Use environment variables on your hosting platform to store ACCESS_TOKEN, VERIFY_TOKEN, PHONE_NUMBER_ID, APP_SECRET, and SECRET_KEY. The APP/__init__.py is designed to read from environment variables first, then config.py.

Persistent Storage: The messages.json file is not persistent on most cloud hosting platforms (it will be reset on restarts or redeployments). For production, you will need to replace this with a proper database solution like:

Firestore (Recommended by the AI for collaborative apps): A NoSQL cloud database that integrates well with Google Cloud.

PostgreSQL/MySQL: Relational databases.

SQLite: Simpler, file-based, but still subject to ephemeral storage issues if not configured carefully for cloud environments.

Recommended Hosting Platforms for Flask:

Render.com: User-friendly PaaS (Platform as a Service) with a free tier for web services. Ideal for getting started quickly.

PythonAnywhere: Another excellent option for Python web apps, offering a free tier.

Google Cloud Run / AWS Fargate / Azure Container Apps: Serverless container platforms that offer high scalability but require Docker knowledge.

After deploying, remember to update your WhatsApp webhook URL in the Meta Developers App Dashboard to your new public URL (e.g., https://your-app-name.render.com/webhook).

⚠️ Troubleshooting
401 Client Error: Unauthorized:

Issue: Your ACCESS_TOKEN is incorrect, expired, or lacks the necessary permissions.

Solution: Go to your Meta Developers Dashboard, generate a new ACCESS_TOKEN (especially if you're using a temporary one), and update it in your APP/config.py. Restart your Flask app.

.../None/messages in URL:

Issue: Your PHONE_NUMBER_ID is not being loaded correctly.

Solution: Ensure PHONE_NUMBER_ID is correctly defined in APP/config.py and has no typos. Restart your Flask app.

No messages appearing in the portal:

Issue: Webhook not correctly configured or your server isn't reachable by Meta.

Solution:

Verify ngrok is running and providing an HTTPS URL if local.

Double-check the "Callback URL" and "Verify Token" in your Meta Developers Dashboard webhook settings.

Ensure your Flask app is running and your /webhook endpoint is accessible.

Check your Flask console logs for any errors when Meta tries to hit your webhook.

✨ Future Enhancements
Database Integration: Migrate from messages.json to a proper database (e.g., Firestore, PostgreSQL) for persistent and scalable storage.

Authentication: Add user authentication to the web portal to restrict access.

Real-time Updates: Implement WebSockets to push new messages to the frontend instantly instead of relying on polling (5-second refresh).

Media Handling: Enhance the portal to display images, videos, and other media types received from WhatsApp, and allow sending them.

Message Templates: Implement the ability to send pre-approved message templates for business-initiated conversations.

Improved UI/UX: Enhance the portal's design, add search, filtering, and more detailed conversation views.

Error Handling in UI: Provide more user-friendly error messages in the frontend.

📄 License
This project is open-source and available under the MIT License.