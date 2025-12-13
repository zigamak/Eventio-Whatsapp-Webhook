// WhatsApp.js - Comprehensive WhatsApp-like Chat Interface
// This file handles all chat functionality for Eventio, IgnitioHub, and Package with Sense

class WhatsAppChat {
    constructor(phoneId, brandColor = '#25D366') {
        this.phoneId = phoneId;
        this.brandColor = brandColor;
        this.currentWaId = null;
        this.currentContactName = null;
        this.lastChatData = null;
        this.lastMessageData = null;
        this.isTyping = false;
        this.typingTimeout = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.fetchChats();
        this.startPolling();
        this.handleResponsiveLayout();
    }

    // ==================== UTILITY FUNCTIONS ====================

    isScrolledToBottom(element) {
        return element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true 
        });
    }

    formatDate(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return date.toLocaleDateString('en-US', { weekday: 'long' });
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    getMessageStatusIcon(status) {
        const icons = {
            'pending': `<svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>`,
            'sent': `<svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>`,
            'delivered': `<svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                <path d="M19 7l-1.41-1.41L9 14.17l1.41 1.42L19 7z" transform="translate(2, 0)"/>
            </svg>`,
            'read': `<svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                <path d="M19 7l-1.41-1.41L9 14.17l1.41 1.42L19 7z" transform="translate(2, 0)"/>
            </svg>`
        };
        return icons[status] || icons['pending'];
    }

    formatContactStatus(lastTimestamp, isOnline) {
        if (isOnline) {
            return '<span class="text-green-400">● Online</span>';
        }
        if (lastTimestamp) {
            const date = new Date(lastTimestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.round(diffMs / (1000 * 60));

            if (diffMins < 1) return 'Active now';
            if (diffMins < 60) return `Last seen ${diffMins} min ago`;
            if (diffMins < (24 * 60)) {
                return `Last seen today at ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
            }
            return `Last seen ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
        }
        return 'Offline';
    }

    getInitials(name) {
        if (!name) return '#';
        const words = name.trim().split(' ');
        if (words.length === 1) return name.charAt(0).toUpperCase();
        return (words[0].charAt(0) + words[words.length - 1].charAt(0)).toUpperCase();
    }

    getAvatarColor(name) {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
        ];
        const index = (name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return colors[index % colors.length];
    }

    // ==================== API CALLS ====================

    async fetchChats() {
        try {
            const response = await fetch(`/api/chats?phone_id=${this.phoneId}`);
            const data = await response.json();
            
            if (response.ok) {
                data.chats.sort((a, b) => new Date(b.last_message_timestamp) - new Date(a.last_message_timestamp));
                
                if (JSON.stringify(data.chats) !== JSON.stringify(this.lastChatData)) {
                    this.displayChats(data.chats);
                    this.lastChatData = data.chats;
                }
            } else {
                console.error('Error fetching chats:', data.message);
            }
        } catch (error) {
            console.error('Error fetching chats:', error);
        }
    }

    async loadMessages(waId, contactName, isPolling = false) {
        const messagesContainer = document.getElementById('messages-container');
        const wasScrolledToBottom = this.isScrolledToBottom(messagesContainer);

        this.currentWaId = waId;
        this.currentContactName = contactName || waId;

        // Update active chat highlight
        document.querySelectorAll('#chats-container > div').forEach(el => {
            const waIdInEl = el.querySelector('.chat-wa-id')?.textContent.trim();
            if (waIdInEl === waId) {
                el.classList.add('bg-gray-100');
            } else {
                el.classList.remove('bg-gray-100');
            }
        });

        // Update header
        document.getElementById('chat-contact-name').textContent = this.currentContactName;
        document.getElementById('chat-contact-phone').textContent = waId;
        
        if (!isPolling) {
            document.getElementById('chat-contact-status').innerHTML = 'Loading...';
        }

        // Show chat area on mobile
        this.showChatArea();

        try {
            const response = await fetch(`/api/chats/${waId}?phone_id=${this.phoneId}`);
            const data = await response.json();
            
            if (response.ok) {
                // Update status
                const chatMetadata = this.lastChatData?.find(c => c.wa_id === waId) || {};
                const lastTimestamp = chatMetadata.last_message_timestamp;
                const isOnline = !isPolling && Math.random() < 0.2; // Simulate online status
                document.getElementById('chat-contact-status').innerHTML = this.formatContactStatus(lastTimestamp, isOnline);

                // Update messages
                if (JSON.stringify(data.messages) !== JSON.stringify(this.lastMessageData) || !isPolling) {
                    this.displayMessages(data.messages);
                    this.lastMessageData = data.messages;
                    
                    if (wasScrolledToBottom || !isPolling) {
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                }

                if (!isPolling) {
                    await this.markMessagesAsRead(waId);
                    this.fetchChats();
                }
            } else {
                console.error('Error fetching messages:', data.message);
            }
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    }

    async markMessagesAsRead(waId) {
        try {
            const response = await fetch('/api/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wa_id: waId, phone_id: this.phoneId })
            });
            
            if (!response.ok) {
                const data = await response.json();
                console.error('Error marking messages as read:', data.message);
            }
        } catch (error) {
            console.error('Error marking messages as read:', error);
        }
    }

    async sendTextMessage(message) {
        if (!message || !this.currentWaId || !this.currentContactName) return;

        // Optimistic UI update
        const tempMessage = {
            body: message,
            direction: 'outbound',
            timestamp: new Date().toISOString(),
            type: 'text',
            status: 'pending'
        };
        
        const tempMessages = this.lastMessageData ? [...this.lastMessageData, tempMessage] : [tempMessage];
        this.displayMessages(tempMessages);
        
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch('/api/respond', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    wa_id: this.currentWaId, 
                    message, 
                    phone_id: this.phoneId, 
                    name: this.currentContactName 
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.loadMessages(this.currentWaId, this.currentContactName);
                this.fetchChats();
            } else {
                console.error('Error sending message:', data.message);
                this.showError('Failed to send message. Please try again.');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Network error. Please check your connection.');
        }
    }

    async sendImageMessage(file, caption) {
        if (!file || !this.currentWaId || !this.currentContactName) return;

        // Optimistic UI update
        const tempImageMessage = {
            body: caption || '📷 Image',
            image_url: URL.createObjectURL(file),
            direction: 'outbound',
            timestamp: new Date().toISOString(),
            type: 'image',
            status: 'pending'
        };
        
        const tempMessages = this.lastMessageData ? [...this.lastMessageData, tempImageMessage] : [tempImageMessage];
        this.displayMessages(tempMessages);
        
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        const formData = new FormData();
        formData.append('wa_id', this.currentWaId);
        formData.append('phone_id', this.phoneId);
        formData.append('image', file);
        formData.append('caption', caption);
        formData.append('name', this.currentContactName);

        try {
            const response = await fetch('/api/send-image', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.loadMessages(this.currentWaId, this.currentContactName);
                this.fetchChats();
            } else {
                console.error('Error sending image:', data.message);
                this.showError('Failed to send image. Please try again.');
            }
        } catch (error) {
            console.error('Error sending image:', error);
            this.showError('Network error. Please check your connection.');
        }
    }

    // ==================== UI DISPLAY FUNCTIONS ====================

    displayChats(chats) {
        const chatsContainer = document.getElementById('chats-container');
        chatsContainer.innerHTML = '';
        
        if (chats.length === 0) {
            chatsContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-gray-500 p-8">
                    <svg class="w-24 h-24 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <p class="text-lg font-medium">No conversations yet</p>
                    <p class="text-sm mt-2">Your chats will appear here</p>
                </div>
            `;
            return;
        }

        chats.forEach(chat => {
            const chatElement = this.createChatElement(chat);
            chatsContainer.appendChild(chatElement);
        });
    }

    createChatElement(chat) {
        const lastMessageTime = chat.last_message_timestamp 
            ? this.formatTime(chat.last_message_timestamp)
            : '';
        
        const unreadCount = chat.unread_count || 0;
        const lastBody = chat.last_body 
            ? (chat.last_body.substring(0, 50) + (chat.last_body.length > 50 ? '...' : ''))
            : 'No messages';
        
        const nameClass = unreadCount > 0 ? 'font-semibold text-gray-900' : 'font-medium text-gray-800';
        const previewClass = unreadCount > 0 ? 'text-sm text-gray-900 font-medium' : 'text-sm text-gray-600';
        const avatarColor = this.getAvatarColor(chat.name);
        
        const chatElement = document.createElement('div');
        chatElement.className = `chat-item p-3 border-b border-gray-200 hover:bg-gray-50 cursor-pointer transition-all duration-200 ${
            this.currentWaId === chat.wa_id ? 'bg-gray-100' : ''
        }`;
        
        chatElement.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="w-12 h-12 rounded-full flex-shrink-0 flex items-center justify-center text-white font-semibold text-lg shadow-sm" 
                     style="background-color: ${avatarColor}">
                    ${this.getInitials(chat.name)}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex justify-between items-baseline mb-1">
                        <h3 class="${nameClass} truncate">${chat.name || 'Unknown Contact'}</h3>
                        <span class="text-xs text-gray-500 ml-2 flex-shrink-0">${lastMessageTime}</span>
                    </div>
                    <p class="chat-wa-id text-xs text-gray-500 mb-1">${chat.wa_id}</p>
                    <div class="flex justify-between items-center">
                        <p class="${previewClass} truncate flex-1 pr-2">${lastBody}</p>
                        ${unreadCount > 0 ? `
                            <span class="bg-green-500 text-white text-xs font-bold px-2 py-0.5 rounded-full min-w-[20px] text-center flex-shrink-0">
                                ${unreadCount}
                            </span>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        chatElement.addEventListener('click', () => this.loadMessages(chat.wa_id, chat.name));
        return chatElement;
    }

    displayMessages(messages) {
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';

        if (messages.length === 0) {
            messagesContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-gray-500">
                    <svg class="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <p class="text-sm">No messages yet</p>
                    <p class="text-xs mt-1">Send a message to start the conversation</p>
                </div>
            `;
            return;
        }

        let lastDate = null;
        
        messages.forEach(msg => {
            const messageDate = this.formatDate(msg.timestamp);
            
            // Add date separator if date changed
            if (messageDate !== lastDate) {
                const dateSeparator = document.createElement('div');
                dateSeparator.className = 'flex justify-center my-4';
                dateSeparator.innerHTML = `
                    <span class="bg-white px-3 py-1 rounded-full text-xs text-gray-600 shadow-sm">
                        ${messageDate}
                    </span>
                `;
                messagesContainer.appendChild(dateSeparator);
                lastDate = messageDate;
            }

            const messageElement = this.createMessageElement(msg);
            messagesContainer.appendChild(messageElement);
        });
    }

    createMessageElement(msg) {
        const messageElement = document.createElement('div');
        const isSent = msg.direction === 'outbound';
        
        messageElement.className = `flex ${isSent ? 'justify-end' : 'justify-start'} mb-2 px-2 message-fade-in`;
        
        let content = '';
        if (msg.type === 'image' && msg.image_url) {
            content = `
                <div class="message-image-container">
                    <img src="${msg.image_url}" 
                         alt="Image" 
                         class="rounded-lg max-w-full cursor-pointer hover:opacity-90 transition-opacity" 
                         style="max-height: 300px; max-width: 300px;"
                         onclick="window.open('${msg.image_url}', '_blank')">
                    ${msg.body && msg.body.trim() !== '📷 Image' ? `
                        <p class="mt-2 break-words">${this.escapeHtml(msg.body.replace('📷 Image', '').trim())}</p>
                    ` : ''}
                </div>
            `;
        } else {
            content = `<p class="break-words whitespace-pre-wrap">${this.escapeHtml(msg.body || 'Message content unavailable')}</p>`;
        }
        
        const time = this.formatTime(msg.timestamp);
        const statusIcon = isSent ? this.getMessageStatusIcon(msg.status) : '';
        
        messageElement.innerHTML = `
            <div class="chat-bubble ${isSent ? 'sent' : 'received'} max-w-[75%] md:max-w-[65%] p-2 px-3 rounded-lg shadow-sm">
                ${content}
                <div class="flex items-center justify-end gap-1 mt-1 text-xs text-gray-500">
                    <span>${time}</span>
                    ${statusIcon}
                </div>
            </div>
        `;
        
        return messageElement;
    }

    // ==================== EVENT LISTENERS ====================

    setupEventListeners() {
        // Message form submission
        const messageForm = document.getElementById('message-form');
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const messageInput = document.getElementById('message-input');
            const message = messageInput.value.trim();
            
            if (message) {
                messageInput.value = '';
                messageInput.style.height = 'auto';
                await this.sendTextMessage(message);
            }
        });

        // Auto-resize textarea
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
        });

        // Image attachment
        const attachButton = document.getElementById('attach-image');
        const imageInput = document.getElementById('image-input');
        
        attachButton.addEventListener('click', () => {
            imageInput.click();
        });

        imageInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                const caption = messageInput.value.trim();
                messageInput.value = '';
                messageInput.style.height = 'auto';
                imageInput.value = '';
                
                await this.sendImageMessage(file, caption);
            }
        });

        // Back button
        const backButton = document.getElementById('back-to-chats');
        backButton.addEventListener('click', () => {
            this.showChatList();
            this.currentWaId = null;
            this.currentContactName = null;
            this.lastMessageData = null;
            this.fetchChats();
        });

        // Search functionality
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', (e) => {
            this.searchChats(e.target.value);
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResponsiveLayout();
        });
    }

    searchChats(searchTerm) {
        const term = searchTerm.toLowerCase();
        const chatElements = document.querySelectorAll('.chat-item');
        
        chatElements.forEach(chat => {
            const name = chat.querySelector('h3').textContent.toLowerCase();
            const waId = chat.querySelector('.chat-wa-id').textContent.toLowerCase();
            const preview = chat.querySelector('p.truncate')?.textContent.toLowerCase() || '';
            
            const matches = name.includes(term) || waId.includes(term) || preview.includes(term);
            chat.style.display = matches ? 'block' : 'none';
        });
    }

    // ==================== RESPONSIVE LAYOUT ====================

    handleResponsiveLayout() {
        const chatList = document.getElementById('chat-list');
        const chatArea = document.getElementById('chat-area');
        const isMobile = window.innerWidth < 768;

        if (isMobile) {
            if (this.currentWaId) {
                chatList.classList.add('hidden');
                chatArea.classList.remove('hidden');
            } else {
                chatList.classList.remove('hidden');
                chatArea.classList.add('hidden');
            }
        } else {
            chatList.classList.remove('hidden');
            chatArea.classList.remove('hidden');
        }
    }

    showChatArea() {
        const chatList = document.getElementById('chat-list');
        const chatArea = document.getElementById('chat-area');
        const isMobile = window.innerWidth < 768;

        if (isMobile) {
            chatList.classList.add('hidden');
            chatArea.classList.remove('hidden');
        } else {
            chatArea.classList.remove('hidden');
        }
    }

    showChatList() {
        const chatList = document.getElementById('chat-list');
        const chatArea = document.getElementById('chat-area');
        const isMobile = window.innerWidth < 768;

        if (isMobile) {
            chatList.classList.remove('hidden');
            chatArea.classList.add('hidden');
        }
    }

    // ==================== POLLING ====================

    startPolling() {
        setInterval(async () => {
            await this.fetchChats();
            
            if (this.currentWaId && this.currentContactName) {
                await this.loadMessages(this.currentWaId, this.currentContactName, true);
            }
        }, 5000); // Poll every 5 seconds
    }

    // ==================== HELPER FUNCTIONS ====================

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        // You can implement a toast notification here
        console.error(message);
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const phoneId = document.getElementById('phone-id-data')?.value;
    const brandColor = document.getElementById('brand-color-data')?.value || '#25D366';
    
    if (phoneId) {
        window.chatApp = new WhatsAppChat(phoneId, brandColor);
    }
});