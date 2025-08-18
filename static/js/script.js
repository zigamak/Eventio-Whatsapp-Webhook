let currentWaId = null;
let currentContactName = null;
let currentPhoneId = '608867502309431';
let lastMessageCounts = {};
let unreadCounts = {};
let isTyping = false;
let typingTimeout;

// DOM Elements
const phoneSelector = document.getElementById('phone-selector');
const searchInput = document.getElementById('search-input');
const contactsList = document.getElementById('contacts-list');
const messagesDiv = document.getElementById('messages');
const conversationTitle = document.getElementById('conversation-title');
const chatStatus = document.getElementById('chat-status');
const chatAvatar = document.getElementById('chat-avatar');
const statusIndicator = document.getElementById('status-indicator');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const notificationSound = document.getElementById('notification-sound');

// Notification functions
function showNotification(name, message, avatar) {
    const notification = document.getElementById('notification');
    document.getElementById('notification-name').textContent = name;
    document.getElementById('notification-message').textContent = message;
    document.getElementById('notification-avatar').textContent = avatar;
    
    notification.classList.add('show');
    
    // Auto hide after 4 seconds
    setTimeout(() => {
        hideNotification();
    }, 4000);
}

function hideNotification() {
    document.getElementById('notification').classList.remove('show');
}

function playNotificationSound() {
    try {
        notificationSound.currentTime = 0;
        notificationSound.play().catch(e => console.log('Sound play failed:', e));
    } catch (e) {
        console.log('Sound not available:', e);
    }
}

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
});

// Search functionality
searchInput.addEventListener('input', function() {
    const searchTerm = this.value.toLowerCase();
    const contacts = contactsList.querySelectorAll('.contact-item');
    
    contacts.forEach(contact => {
        const name = contact.querySelector('.contact-name')?.textContent.toLowerCase() || '';
        const lastMessage = contact.querySelector('.last-message')?.textContent.toLowerCase() || '';
        
        if (name.includes(searchTerm) || lastMessage.includes(searchTerm)) {
            contact.style.display = 'flex';
        } else {
            contact.style.display = 'none';
        }
    });
});

function renderTicks(status) {
    if (status === 'sent') {
        return '<i class="fas fa-check tick-status"></i>';
    } else if (status === 'delivered') {
        return '<i class="fas fa-check-double tick-status"></i>';
    } else if (status === 'read') {
        return '<i class="fas fa-check-double tick-status read"></i>';
    } else if (status === 'sending') {
        return '<i class="fas fa-clock tick-status"></i>';
    }
    return '';
}

function appendMessageToChat(msg) {
    const isNewMessage = !messagesDiv.querySelector(`[data-message-id="${msg.id || msg.timestamp}"]`);
    
    if (messagesDiv.querySelector('.h-full')) {
        messagesDiv.innerHTML = '';
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = `flex ${msg.direction === 'inbound' ? 'justify-start' : 'justify-end'} mb-1`;
    msgDiv.setAttribute('data-message-id', msg.id || msg.timestamp);
    
    const avatar = msg.direction === 'inbound' ? (currentContactName ? currentContactName.charAt(0).toUpperCase() : '?') : '';
    
    msgDiv.innerHTML = `
        <div class="message-bubble ${msg.direction === 'inbound' ? 'inbound' : 'outbound'}">
            <p class="text-sm whitespace-pre-wrap">${msg.body}</p>
            <div class="message-time">
                <span>${new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                ${msg.direction === 'outbound' ? renderTicks(msg.status) : ''}
            </div>
        </div>
    `;
    
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Play notification sound for new inbound messages
    if (isNewMessage && msg.direction === 'inbound' && currentWaId) {
        playNotificationSound();
        if (currentWaId !== msg.wa_id) {
            showNotification(
                currentContactName || 'Unknown Contact', 
                msg.body.length > 50 ? msg.body.substring(0, 50) + '...' : msg.body,
                avatar
            );
        }
    }
}

async function loadMessages(waId, name, phoneId) {
    if (!phoneId) return;
    
    currentWaId = waId;
    currentContactName = name;
    currentPhoneId = phoneId;
    
    // Update UI
    conversationTitle.textContent = name || 'Unknown Contact';
    chatStatus.textContent = 'last seen recently';
    chatAvatar.querySelector('span').textContent = name ? name.charAt(0).toUpperCase() : '?';
    statusIndicator.classList.remove('hidden');
    
    // Show loading
    messagesDiv.innerHTML = `
        <div class="flex items-center justify-center h-full">
            <div class="text-center text-gray-500">
                <i class="fas fa-spinner fa-spin text-2xl mb-2"></i>
                <div>Loading messages...</div>
            </div>
        </div>
    `;

    try {
        const response = await fetch(`/api/chats/${waId}?phone_id=${phoneId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        const messages = data.messages || [];
        
        messagesDiv.innerHTML = '';
        if (messages.length === 0) {
            messagesDiv.innerHTML = `
                <div class="flex items-center justify-center h-full text-gray-500">
                    <div class="text-center">
                        <i class="fab fa-whatsapp text-6xl text-green-100 mb-4"></i>
                        <p>Start a conversation with ${name}</p>
                    </div>
                </div>
            `;
        } else {
            messages.forEach(msg => appendMessageToChat(msg));
        }
        
        // Mark messages as read
        if (unreadCounts[waId] > 0) {
            unreadCounts[waId] = 0;
            updateUnreadBadges();
        }
        
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
        
    } catch (error) {
        console.error('Error loading messages:', error);
        messagesDiv.innerHTML = `
            <div class="flex items-center justify-center h-full text-red-500">
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                    <p>Failed to load messages</p>
                </div>
            </div>
        `;
    }
}

function updateUnreadBadges() {
    const contacts = contactsList.querySelectorAll('.contact-item');
    contacts.forEach(contact => {
        const waId = contact.getAttribute('data-wa-id');
        const badge = contact.querySelector('.unread-badge');
        
        if (unreadCounts[waId] > 0) {
            if (!badge) {
                const timeDiv = contact.querySelector('.last-message-time');
                if (timeDiv) {
                    const badge = document.createElement('div');
                    badge.className = 'unread-badge';
                    badge.textContent = unreadCounts[waId];
                    timeDiv.insertAdjacentElement('afterend', badge);
                }
            } else {
                badge.textContent = unreadCounts[waId];
            }
        } else if (badge) {
            badge.remove();
        }
    });
}

function showTyping(show = true) {
    if (show && currentContactName) {
        document.getElementById('typing-name').textContent = currentContactName;
        document.getElementById('typing-avatar').textContent = currentContactName.charAt(0).toUpperCase();
        typingIndicator.classList.remove('hidden');
        chatStatus.textContent = 'typing...';
    } else {
        typingIndicator.classList.add('hidden');
        chatStatus.textContent = 'last seen recently';
    }
}

async function sendMessage() {
    if (!currentWaId || !currentPhoneId) return;
    
    const messageBody = messageInput.value.trim();
    if (!messageBody) return;
    
    // Optimistic UI update
    const tempMessage = {
        body: messageBody,
        direction: 'outbound',
        timestamp: new Date().toISOString(),
        status: 'sending'
    };
    appendMessageToChat(tempMessage);

    messageInput.value = '';
    messageInput.style.height = 'auto';
    messageInput.disabled = true;
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    try {
        const response = await fetch('/api/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                wa_id: currentWaId, 
                message: messageBody, 
                phone_id: currentPhoneId 
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Server error: ${response.status}`);
        }
        
        // Simulate typing response
        setTimeout(() => {
            showTyping(true);
            setTimeout(() => {
                showTyping(false);
                loadMessages(currentWaId, currentContactName, currentPhoneId);
            }, 2000);
        }, 1000);
        
    } catch (error) {
        console.error('Error sending message:', error);
        // Remove the temporary message on error
        const tempMsg = messagesDiv.querySelector(`[data-message-id="${tempMessage.timestamp}"]`);
        if (tempMsg) tempMsg.remove();
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        messageInput.focus();
    }
}

async function loadContacts() {
    if (!currentPhoneId) return;
    
    try {
        const response = await fetch(`/api/chats?phone_id=${currentPhoneId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        contactsList.innerHTML = '';
        
        if (data.chats && data.chats.length > 0) {
            data.chats.forEach(contact => {
                const previousCount = lastMessageCounts[contact.wa_id] || 0;
                const newMessages = (contact.message_count || 0) - previousCount;
                
                if (newMessages > 0 && currentWaId !== contact.wa_id) {
                    unreadCounts[contact.wa_id] = (unreadCounts[contact.wa_id] || 0) + newMessages;
                }
                
                lastMessageCounts[contact.wa_id] = contact.message_count || 0;
                
                const isOnline = Math.random() > 0.7; // Simulate online status
                
                const contactItem = document.createElement('div');
                contactItem.className = `contact-item p-4 cursor-pointer flex items-center gap-3 ${currentWaId === contact.wa_id ? 'active' : ''}`;
                contactItem.setAttribute('data-wa-id', contact.wa_id);
                
                const avatar = contact.name ? contact.name.charAt(0).toUpperCase() : '?';
                const timeAgo = contact.last_message_timestamp ? 
                    new Date(contact.last_message_timestamp).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    }) : '';
                
                contactItem.innerHTML = `
                    <div class="relative">
                        <div class="profile-picture">
                            <span>${avatar}</span>
                            ${isOnline ? '<div class="status-indicator status-online"></div>' : ''}
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between mb-1">
                            <h3 class="contact-name font-medium text-gray-900 truncate">${contact.name || 'Unknown Contact'}</h3>
                            <div class="flex items-center gap-2">
                                <span class="last-message-time text-xs text-gray-500">${timeAgo}</span>
                                ${unreadCounts[contact.wa_id] > 0 ? `<div class="unread-badge">${unreadCounts[contact.wa_id]}</div>` : ''}
                            </div>
                        </div>
                        <p class="last-message text-sm text-gray-600 truncate">${contact.last_message || 'No messages yet'}</p>
                    </div>
                `;
                
                contactItem.addEventListener('click', () => {
                    // Remove active class from all contacts
                    document.querySelectorAll('.contact-item').forEach(item => 
                        item.classList.remove('active'));
                    
                    // Add active class to clicked contact
                    contactItem.classList.add('active');
                    
                    // Load messages
                    loadMessages(contact.wa_id, contact.name || 'Unknown Contact', currentPhoneId);
                });
                
                contactsList.appendChild(contactItem);
            });
        } else {
            contactsList.innerHTML = `
                <div class="flex items-center justify-center h-32 text-gray-500">
                    <div class="text-center">
                        <i class="fab fa-whatsapp text-4xl text-green-100 mb-2"></i>
                        <p>No conversations yet</p>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading contacts:', error);
        contactsList.innerHTML = `
            <div class="flex items-center justify-center h-32 text-red-500">
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                    <p>Failed to load contacts</p>
                </div>
            </div>
        `;
    }
}

// Event Listeners
phoneSelector.addEventListener('change', () => {
    currentPhoneId = phoneSelector.value;
    currentWaId = null;
    currentContactName = null;
    unreadCounts = {};
    
    // Reset UI
    conversationTitle.textContent = 'Select a chat';
    chatStatus.textContent = 'Choose a conversation to start messaging';
    chatAvatar.querySelector('span').textContent = '?';
    statusIndicator.classList.add('hidden');
    messagesDiv.innerHTML = `
        <div class="flex items-center justify-center h-full text-gray-500">
            <div class="text-center">
                <i class="fab fa-whatsapp text-8xl text-green-100 mb-4"></i>
                <h3 class="text-xl font-medium mb-2">Keep your phone connected</h3>
                <p class="text-sm max-w-sm">WhatsApp connects to your phone to sync messages. To reduce data usage, connect your phone to Wi-Fi.</p>
            </div>
        </div>
    `;
    
    messageInput.disabled = true;
    sendButton.disabled = true;
    searchInput.value = '';
    
    loadContacts();
});

sendButton.addEventListener('click', sendMessage);
sendButton.addEventListener('click', createRipple);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadContacts();

    // Auto-refresh every 8 seconds
    setInterval(() => {
        if (currentPhoneId) {
            loadContacts();
            if (currentWaId) {
                // Check for new messages without full reload
                fetch(`/api/chats/${currentWaId}?phone_id=${currentPhoneId}`)
                    .then(response => response.json())
                    .then(data => {
                        const messages = data.messages || [];
                        const currentMessages = messagesDiv.querySelectorAll('[data-message-id]');
                        
                        // Only add new messages
                        messages.forEach(msg => {
                            const exists = Array.from(currentMessages).some(el => 
                                el.getAttribute('data-message-id') === (msg.id || msg.timestamp));
                            
                            if (!exists) {
                                appendMessageToChat(msg);
                            }
                        });
                    })
                    .catch(console.error);
            }
        }
    }, 8000);

    // Simulate random online status changes
    setInterval(() => {
        const indicators = document.querySelectorAll('.status-indicator');
        indicators.forEach(indicator => {
            if (Math.random() > 0.8) {
                const classes = ['status-online', 'status-away', 'status-busy'];
                indicator.className = `status-indicator ${classes[Math.floor(Math.random() * classes.length)]}`;
            }
        });
    }, 15000);
});

// Handle notification clicks
document.getElementById('notification').addEventListener('click', () => {
    hideNotification();
});

// Close notification on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideNotification();
    }
});

// Prevent form submission on Enter in search
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
    }
});

// Add some nice hover effects
document.addEventListener('mouseover', (e) => {
    if (e.target.classList.contains('send-button') && !e.target.disabled) {
        e.target.style.transform = 'scale(1.05)';
    }
});

document.addEventListener('mouseout', (e) => {
    if (e.target.classList.contains('send-button')) {
        e.target.style.transform = 'scale(1)';
    }
});

// Ripple effect for buttons
function createRipple(event) {
    const button = event.currentTarget;
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
    circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
    circle.classList.add('ripple');

    const ripple = button.getElementsByClassName('ripple')[0];
    if (ripple) {
        ripple.remove();
    }

    button.appendChild(circle);
}