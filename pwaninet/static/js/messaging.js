console.log('messaging.js loaded');

class MessagingManager {
    constructor() {
        console.log('MessagingManager constructor called');
        this.socket = null;
        this.conversationId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.messageQueue = [];
        this.typingTimeout = null;
        this.currentUserId = null;
        this.e2eEncryption = null;
        this.isEncrypted = false;
        this.recipientPublicKey = null;

        this.init();
    }

    async init() {
        console.log('MessagingManager init() called');
        this.currentUserId = document.body.dataset.userId;
        this.conversationId = document.body.dataset.conversationId;
        this.isEncrypted = document.body.dataset.isEncrypted === 'true';

        console.log('MessagingManager init values:', {
            currentUserId: this.currentUserId,
            conversationId: this.conversationId,
            isEncrypted: this.isEncrypted
        });

        // Initialize E2E encryption if enabled
        if (this.isEncrypted && this.conversationId) {
            await this.initEncryption();
        }

        this.setupEventListeners();
        this.connectWebSocket();
    }

    async initEncryption() {
        try {
            this.e2eEncryption = new E2EEncryption();
            const { publicKey, privateKey, isNew } = await this.e2eEncryption.initForConversation(this.conversationId);

            // If new keys were generated, send public key to server
            if (isNew && publicKey) {
                await this.sendPublicKey(publicKey);
            }

            // Load recipient's public key for encryption
            await this.loadRecipientPublicKey();

            console.log('E2E encryption initialized');
        } catch (error) {
            console.error('Error initializing E2E encryption:', error);
        }
    }

    async sendPublicKey(publicKey) {
        try {
            const response = await fetch(`/messaging/v1/conversations/${this.conversationId}/set_public_key/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]')?.value || ''
                },
                body: JSON.stringify({ public_key: publicKey })
            });

            if (!response.ok) {
                console.error('Error sending public key:', response.status);
            }
        } catch (error) {
            console.error('Error sending public key:', error);
        }
    }

    async loadRecipientPublicKey() {
        try {
            const response = await fetch(`/messaging/v1/conversations/${this.conversationId}/members/`);
            if (response.ok) {
                const members = await response.json();
                // Find the other member (not current user)
                const otherMember = members.results?.find(m => m.user.id !== this.currentUserId);
                if (otherMember && otherMember.public_key) {
                    this.recipientPublicKey = otherMember.public_key;
                    await this.e2eEncryption.importPublicKey(this.recipientPublicKey);
                }
            }
        } catch (error) {
            console.error('Error loading recipient public key:', error);
        }
    }
    
    setupEventListeners() {
        // Message input
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
                this.handleTyping();
            });
            
            // Auto-expand textarea as user types
            messageInput.addEventListener('input', function() {
                this.style.height = 'auto';
                const newHeight = Math.min(this.scrollHeight, 120);
                this.style.height = newHeight + 'px';
            });
        }
        
        // Send button
        const sendButton = document.getElementById('sendBtn');
        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        // Cancel reply
        const cancelReply = document.getElementById('cancelReply');
        if (cancelReply) {
            cancelReply.addEventListener('click', () => this.cancelReply());
        }
        
        // Reaction buttons
        document.querySelectorAll('.add-reaction').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const emoji = e.target.dataset.emoji;
                const messageId = e.target.closest('[data-message-id]').dataset.messageId;
                this.addReaction(messageId, emoji);
            });
        });
        
        // Create conversation
        const createBtn = document.getElementById('createConversation');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.createConversation());
        }
        
        // Search conversations
        const searchInput = document.getElementById('searchConversations');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.searchConversations(e.target.value));
        }
        
        // Back to list (mobile)
        const backBtn = document.getElementById('backToList');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                document.getElementById('chatWindow').classList.add('d-none');
                document.querySelector('.col-md-4').classList.remove('d-none');
            });
        }
    }
    
    connectWebSocket() {
        if (this.conversationId) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.processMessageQueue();
            };
            
            this.socket.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this.handleMessage(data);
            };
            
            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.attemptReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                this.connectWebSocket();
            }, 3000 * this.reconnectAttempts);
        }
    }
    
    async handleMessage(data) {
        switch (data.type) {
            case 'message':
                // Decrypt message if encrypted
                if (data.data.is_encrypted && this.e2eEncryption) {
                    try {
                        data.data.content = await this.e2eEncryption.decryptMessage(data.data.encrypted_content);
                    } catch (error) {
                        console.error('Failed to decrypt message:', error);
                        data.data.content = '[Encrypted message - unable to decrypt]';
                    }
                }
                this.displayMessage(data.data);
                this.updateConversationPreview(data.data);
                break;
            case 'typing':
                this.handleTypingIndicator(data);
                break;
            case 'read_receipt':
                this.handleReadReceipt(data);
                break;
        }
    }
    
    async sendMessage(messageContent = null) {
        const input = document.getElementById('messageInput');
        const content = messageContent || input.value.trim();

        if (!content) return;

        let messageData = {
            type: 'chat_message',
            content: content,
            reply_to: this.replyToMessageId || null
        };

        // Encrypt message if E2E encryption is enabled and we have recipient's key
        if (this.isEncrypted && this.e2eEncryption && this.recipientPublicKey) {
            try {
                const encryptedContent = await this.e2eEncryption.encryptMessage(content, this.recipientPublicKey);
                messageData = {
                    type: 'chat_message',
                    content: null,  // Don't send plaintext
                    encrypted_content: encryptedContent,
                    is_encrypted: true,
                    reply_to: this.replyToMessageId || null
                };
            } catch (error) {
                console.error('Encryption failed, sending plaintext:', error);
            }
        }

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(messageData));
            if (!messageContent) {
                input.value = '';
            }
            this.cancelReply();
        } else {
            this.messageQueue.push(messageData);
            console.log('Message queued (socket not connected)');
        }
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.socket.readyState === WebSocket.OPEN) {
            const message = this.messageQueue.shift();
            this.socket.send(JSON.stringify(message));
        }
    }
    
    displayMessage(message) {
        const container = document.getElementById('messagesContainer');
        if (!container) return;

        const isOwn = message.sender.id === this.currentUserId;
        const messageDate = new Date(message.created_at).toDateString();
        
        // Check if this is a consecutive message from the same sender
        const lastMessage = container.querySelector('.message-bubble:last-child');
        const isConsecutive = lastMessage && 
                            lastMessage.dataset.senderId === message.sender.id &&
                            lastMessage.classList.contains(isOwn ? 'sent' : 'received');
        
        // Check if we need to add a date separator
        const lastDateSeparator = container.querySelector('.date-separator:last-child');
        const needsDateSeparator = !lastDateSeparator || 
                                   (lastMessage && this.getMessageDate(lastMessage) !== messageDate);
        
        // Remove last-sent class from previous last message
        const prevLastMessage = container.querySelector('.message-bubble.last-sent');
        if (prevLastMessage) {
            prevLastMessage.classList.remove('last-sent');
            const oldIndicator = prevLastMessage.querySelector('.read-receipt-indicator');
            if (oldIndicator) oldIndicator.remove();
        }
        
        // Add date separator if needed
        if (needsDateSeparator) {
            const dateLabel = this.formatDateLabel(message.created_at);
            const dateHtml = `<div class="date-separator"><span>${dateLabel}</span></div>`;
            container.insertAdjacentHTML('beforeend', dateHtml);
        }
        
        const messageHtml = `
            <div class="message-bubble ${isOwn ? 'sent' : 'received'} ${isConsecutive ? 'consecutive-message' : 'first-in-group'} ${isOwn ? 'last-sent' : ''}" 
                 data-message-id="${message.id}" 
                 data-sender-id="${message.sender.id}"
                 data-read-status="sent">
                <p class="message-content">${message.content || ''}</p>
                <div class="message-time">
                    ${new Date(message.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
                ${isOwn ? `
                <div class="read-receipt-indicator" data-status="sent">
                    <div class="read-receipt-circle">
                        <span class="read-receipt-icon">&#10003;</span>
                    </div>
                </div>
                ` : ''}
            </div>
        `;

        container.insertAdjacentHTML('beforeend', messageHtml);
        container.scrollTop = container.scrollHeight;

        // Re-attach event listeners for new reaction buttons
        this.attachReactionListeners();
    }
    
    getMessageDate(messageElement) {
        // Try to get date from data attribute or infer from context
        return messageElement.dataset.messageDate || new Date().toDateString();
    }
    
    formatDateLabel(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).replace(/\//g, '/');
        }
    }
    
    attachReactionListeners() {
        document.querySelectorAll('.add-reaction').forEach(btn => {
            if (!btn.dataset.listenerAttached) {
                btn.addEventListener('click', (e) => {
                    const emoji = e.target.dataset.emoji;
                    const messageId = e.target.dataset.messageId;
                    this.addReaction(messageId, emoji);
                });
                btn.dataset.listenerAttached = 'true';
            }
        });
    }
    
    handleTyping() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'typing_indicator',
                is_typing: true
            }));
            
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => {
                this.socket.send(JSON.stringify({
                    type: 'typing_indicator',
                    is_typing: false
                }));
            }, 500);
        }
    }
    
    handleTypingIndicator(data) {
        const indicator = document.getElementById('typingIndicator');
        if (!indicator) return;
        
        if (data.is_typing && data.user_id !== this.currentUserId) {
            indicator.textContent = `${data.username} is typing...`;
        } else {
            indicator.textContent = '';
        }
    }
    
    addReaction(messageId, emoji) {
        fetch(`/messaging/v1/messages/${messageId}/add_reaction/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
            },
            body: JSON.stringify({ emoji })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Reaction added:', data);
        })
        .catch(error => console.error('Error adding reaction:', error));
    }
    
    createConversation() {
        const type = document.querySelector('#conversationTypeTabs .nav-link.active').dataset.bsTarget === '#direct' ? 'direct' : 'group';
        const data = { type };

        if (type === 'direct') {
            const userId = document.getElementById('directUserSelect').value;
            if (!userId) {
                alert('Please select a user');
                return;
            }
            data.member_ids = [userId];
        } else {
            const name = document.getElementById('groupName').value;
            const members = Array.from(document.getElementById('groupMembersSelect').selectedOptions).map(opt => opt.value);

            if (!name) {
                alert('Please enter a group name');
                return;
            }
            if (members.length === 0) {
                alert('Please add at least one member');
                return;
            }

            data.name = name;
            data.member_ids = members;
        }

        fetch('/messaging/v1/conversations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.id) {
                // Check if this is an existing conversation
                if (data.existing) {
                    this.showNotification('Existing conversation found. Redirecting...', 'info');
                }
                window.location.href = `/messaging/conversation/${data.id}/`;
            } else {
                console.error('Invalid response:', data);
                alert('Failed to create conversation. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error creating conversation:', error);
            alert('Failed to create conversation. Please try again.');
        });
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'info' ? 'primary' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    searchConversations(query) {
        const items = document.querySelectorAll('#conversationList .list-group-item');
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(query.toLowerCase()) ? 'flex' : 'none';
        });
    }
    
    updateConversationPreview(message) {
        const conversationItem = document.querySelector(`[data-conversation-id="${message.conversation}"]`);
        if (conversationItem) {
            const preview = conversationItem.querySelector('.text-truncate.small');
            if (preview) {
                preview.textContent = `${message.sender.username}: ${message.content.substring(0, 30)}`;
            }
        }
    }
    
    setConversation(conversationId) {
        this.conversationId = conversationId;
        if (this.socket) {
            this.socket.close();
        }
        this.connectWebSocket();
    }
    
    cancelReply() {
        this.replyToMessageId = null;
        const replyDiv = document.querySelector('[data-reply-to-message]');
        if (replyDiv) {
            replyDiv.remove();
        }
    }
    
    handleReadReceipt(data) {
        const { message_id, status, user_avatar } = data;
        this.updateReadReceiptStatus(message_id, status, user_avatar);
    }
    
    updateReadReceiptStatus(messageId, status, userAvatar = null) {
        // Update message bubble read receipt
        const messageBubble = document.querySelector(`.message-bubble[data-message-id="${messageId}"]`);
        if (messageBubble) {
            const indicator = messageBubble.querySelector('.read-receipt-indicator');
            if (indicator) {
                this.updateReadReceiptIndicator(indicator, status, userAvatar);
            }
        }
        
        // Update conversation list read receipt for last message
        this.updateConversationListReadReceipt(status, userAvatar);
    }
    
    updateReadReceiptIndicator(indicator, status, userAvatar = null) {
        indicator.dataset.status = status;
        
        const circle = indicator.querySelector('.read-receipt-circle');
        const icon = indicator.querySelector('.read-receipt-icon');
        
        switch (status) {
            case 'sent':
                circle.style.background = 'white';
                circle.style.borderColor = '#ddd';
                icon.style.color = '#888';
                icon.textContent = '✓';
                break;
            case 'delivered':
                circle.style.background = 'white';
                circle.style.borderColor = '#ddd';
                icon.style.color = '#888';
                icon.textContent = '✓✓';
                break;
            case 'online':
                circle.style.background = 'var(--brand)';
                circle.style.borderColor = 'var(--brand)';
                icon.style.color = 'white';
                icon.textContent = '✓';
                break;
            case 'read':
                // Show avatar instead of checkmark
                icon.style.display = 'none';
                if (userAvatar) {
                    let avatar = circle.querySelector('.read-receipt-avatar');
                    if (!avatar) {
                        avatar = document.createElement('img');
                        avatar.className = 'read-receipt-avatar';
                        circle.appendChild(avatar);
                    }
                    avatar.src = userAvatar;
                }
                break;
        }
    }
    
    updateConversationListReadReceipt(status, userAvatar = null) {
        // Find the current conversation's read receipt in the conversation list
        const currentConversationLink = document.querySelector(`a[href*="/conversation/${this.conversationId}/"]`);
        if (!currentConversationLink) return;
        
        const indicator = currentConversationLink.querySelector('.read-receipt-indicator');
        if (!indicator) return;
        
        this.updateReadReceiptIndicator(indicator, status, userAvatar);
    }
    
    // Helper method to check if recipient is online and update indicator
    checkRecipientOnlineStatus(isOnline) {
        const lastSentMessage = document.querySelector('.message-bubble.last-sent.sent');
        if (!lastSentMessage) return;
        
        const currentStatus = lastSentMessage.dataset.readStatus;
        // Only update if currently 'sent' (not yet read)
        if (currentStatus === 'sent' && isOnline) {
            this.updateReadReceiptStatus(lastSentMessage.dataset.messageId, 'online');
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.messagingManager = new MessagingManager();
});
