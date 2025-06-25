// portal.js
let currentWaId = null;
let currentContactName = null; // Store current contact name for reload consistency

/**
 * Loads messages for a given WhatsApp ID and updates the conversation display.
 * @param {string} waId - The WhatsApp ID of the contact.
 * @param {string} name - The name of the contact.
 */
async function loadMessages(waId, name) {
    currentWaId = waId;
    currentContactName = name; // Store the name
    document.getElementById('conversation-title').innerText = `Conversation with ${name} (${waId})`;
    
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = '<p class="text-center text-gray-500">Loading messages...</p>'; // Show loading indicator

    try {
        const response = await fetch(`/api/chats/${waId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const messages = data.messages || [];
        
        messagesDiv.innerHTML = ''; // Clear loading indicator
        
        if (messages.length === 0) {
            messagesDiv.innerHTML = '<p class="text-center text-gray-500">No messages yet for this conversation.</p>';
        } else {
            messages.forEach(msg => {
                const msgDiv = document.createElement('div');
                // Apply Tailwind classes for styling messages
                msgDiv.className = `p-3 mb-2 rounded-lg max-w-xl break-words whitespace-pre-wrap shadow-sm transition-all duration-200 ease-in-out ${
                    msg.type === 'sent' 
                        ? 'bg-blue-500 text-white ml-auto' // Outgoing messages
                        : 'bg-gray-200 text-gray-800 mr-auto' // Incoming messages
                }`;
                
                const timestamp = new Date(msg.timestamp).toLocaleString();
                msgDiv.innerHTML = `<p class="text-sm">${msg.text}</p><p class="text-xs opacity-75 mt-1">${timestamp}</p>`;
                
                messagesDiv.appendChild(msgDiv);
            });
        }
        
        // Scroll to the bottom to show the latest messages
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (error) {
        console.error('Error loading messages:', error);
        messagesDiv.innerHTML = `<p class="text-center text-red-500">Failed to load messages: ${error.message}</p>`;
        // Use a more user-friendly modal or message box instead of alert if possible
        // For now, sticking to the existing pattern:
        alert('Failed to load messages. Please check console for details.');
    }
}

/**
 * Sends a message from the portal to the currently selected WhatsApp ID.
 */
async function sendMessage() {
    if (!currentWaId) {
        alert('Please select a contact first to send a message.');
        return;
    }
    
    const messageInput = document.getElementById('message-input');
    const messageBody = messageInput.value.trim();
    
    if (!messageBody) {
        // Optionally provide user feedback like a shake or temporary border highlight
        messageInput.placeholder = "Message cannot be empty!";
        setTimeout(() => messageInput.placeholder = "Type your message here...", 1500);
        return;
    }
    
    // Disable input and button to prevent double-sending
    messageInput.disabled = true;
    document.getElementById('send-button').disabled = true;
    document.getElementById('send-button').innerText = 'Sending...';

    try {
        const response = await fetch('/api/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                wa_id: currentWaId, 
                message: messageBody 
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Server responded with status: ${response.status}`);
        }
        
        messageInput.value = ''; // Clear the input field
        
        // Reload messages to show the newly sent one.
        // Use currentContactName for consistency.
        await loadMessages(currentWaId, currentContactName);
    } catch (error) {
        console.error('Error sending message:', error);
        alert(`Failed to send message: ${error.message}`);
    } finally {
        // Re-enable input and button
        messageInput.disabled = false;
        document.getElementById('send-button').disabled = false;
        document.getElementById('send-button').innerText = 'Send';
        messageInput.focus(); // Keep focus on the input
    }
}

/**
 * Loads the list of contacts from the API and populates the contacts list.
 */
async function loadContacts() {
    try {
        const response = await fetch('/api/chats');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const contactsList = document.getElementById('contacts-list');
        contactsList.innerHTML = ''; // Clear existing list
        
        if (data.chats && data.chats.length > 0) {
            data.chats.forEach(contact => {
                const contactItem = document.createElement('div');
                // Apply Tailwind classes for contact items
                contactItem.className = 'contact-item p-3 rounded-lg hover:bg-blue-100 cursor-pointer transition duration-150 ease-in-out border border-gray-100 hover:border-blue-300';
                contactItem.innerHTML = `
                    <span class="contact-name font-semibold text-gray-800">${contact.name || 'Unknown Contact'}</span>
                    <span class="contact-wa-id text-sm text-gray-500 block">${contact.wa_id}</span>
                    <span class="text-xs text-gray-400 block mt-1">Last message: ${contact.last_message_timestamp ? new Date(contact.last_message_timestamp).toLocaleString() : 'N/A'}</span>
                `;
                
                contactItem.addEventListener('click', () => {
                    // Remove 'active' class from all contact items
                    document.querySelectorAll('.contact-item').forEach(item => {
                        item.classList.remove('bg-blue-200', 'border-blue-500');
                    });
                    // Add 'active' class to the clicked item
                    contactItem.classList.add('bg-blue-200', 'border-blue-500');

                    loadMessages(contact.wa_id, contact.name || 'Unknown Contact');
                });
                
                contactsList.appendChild(contactItem);
            });
        } else {
            contactsList.innerHTML = '<p class="text-gray-500 text-sm text-center">No contacts found yet.</p>';
        }
    } catch (error) {
        console.error('Error loading contacts:', error);
        const contactsList = document.getElementById('contacts-list');
        contactsList.innerHTML = `<p class="text-red-500 text-sm text-center">Failed to load contacts: ${error.message}</p>`;
        alert('Failed to load contacts. Please check console for details.');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadContacts();
    
    // Set up send button click handler
    document.getElementById('send-button').addEventListener('click', sendMessage);
    
    // Set up Enter key to send message from the input field
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Optionally set up auto-refresh for contacts/messages, e.g., every 30 seconds
    // This is good for a portal that needs to show real-time updates without user interaction
    // setInterval(() => {
    //     loadContacts();
    //     if (currentWaId) {
    //         loadMessages(currentWaId, currentContactName);
    //     }
    // }, 30000); // Refresh every 30 seconds
});

