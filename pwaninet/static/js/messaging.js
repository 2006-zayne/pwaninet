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
        
        // STATE LAYER: Single source of truth
        this.messages = [];
        this.isRendering = false;

        this.init();
    }

    async init() {
        console.log('MessagingManager init() called');
        this.currentUserId = Number(document.body.dataset.userId);
        this.conversationId = Number(document.body.dataset.conversationId);
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
        this.loadInitialMessages();
    }

    // STATE LAYER METHODS
    
    async loadInitialMessages() {
        try {
            const response = await fetch(`/messaging/v1/conversations/${this.conversationId}/messages/`);
            if (response.ok) {
                const data = await response.json();
                this.messages = data.results || [];
                this.render();
            }
        } catch (error) {
            console.error('Error loading initial messages:', error);
        }
    }
    
    addMessage(messageData) {
        try {
            console.log('addMessage called with:', messageData);

            // Check if this is a confirmation of an optimistic message
            if (messageData.sender_id === parseInt(this.currentUserId) && !messageData.is_optimistic) {
                // Find and remove the optimistic message
                const optimisticIndex = this.messages.findIndex(m =>
                    m.is_optimistic &&
                    m.content === messageData.content &&
                    (new Date(messageData.created_at) - new Date(m.created_at)) < 10000
                );

                if (optimisticIndex !== -1) {
                    console.log('Replacing optimistic message with server confirmed message');
                    this.messages[optimisticIndex] = messageData;
                    this.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                    this.render();
                    return;
                }
            }

            // Normalize message data structure to match state expectations
            const normalizedMessage = {
                ...messageData,
                sender_id: messageData.sender_id || messageData.sender?.id,
                created_at: messageData.created_at || messageData.timestamp
            };

            console.log('Normalized message:', normalizedMessage);

            // Validate required fields
            if (!normalizedMessage.id || !normalizedMessage.content || !normalizedMessage.sender_id) {
                console.error('Invalid message data:', normalizedMessage);
                return;
            }

            // Add message to state array
            this.messages.push(normalizedMessage);
            // Sort messages by created_at to maintain order
            this.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
            this.render();

            console.log('Message added successfully. Total messages:', this.messages.length);
        } catch (error) {
            console.error('Error in addMessage:', error, messageData);
        }
    }

    // VIEW MODEL LAYER: Pure function for derived data
buildView(messages) {
    const viewItems = [];
    let lastDate = null;
    let lastSenderId = null;
    let lastOwnMessageIndex = -1;

    const currentUserId = Number(this.currentUserId);

    for (const message of messages) {
        const messageDate = new Date(message.created_at).toDateString();

        const senderId = Number(message.sender?.id ?? message.sender_id);
        const isOwn = senderId === currentUserId;

        // Date separator
        if (messageDate !== lastDate) {
            viewItems.push({
                type: 'date',
                label: this.formatDateLabel(message.created_at)
            });
            lastDate = messageDate;
        }

        // Consecutive grouping (safer)
        const isConsecutive =
            lastSenderId === senderId &&
            messageDate === lastDate;

        lastSenderId = senderId;

        // Push message first (we need index stability)
        const viewItem = {
            type: 'message',
            ...message,
            sender_id: senderId,
            isOwn,
            isConsecutive,
            isLastSent: false // set after index calc
        };

        viewItems.push(viewItem);

        const currentIndex = viewItems.length - 1;

        // Track last own message index
        if (isOwn) {
            lastOwnMessageIndex = currentIndex;
        }

        // Mark last sent message correctly
        viewItem.isLastSent = isOwn && currentIndex === lastOwnMessageIndex;
    }

    return viewItems;
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
    
    // RENDER LAYER: Pure DOM rendering without logic
    render() {
        if (this.isRendering) return;
        this.isRendering = true;
        
        try {
            const container = document.getElementById('messagesContainer');
            if (!container) return;
            
            // Clear container safely
            container.innerHTML = '';
            
            // Build view from state
            const viewItems = this.buildView(this.messages);
            
            // Render each item
            viewItems.forEach(item => {
                if (item.type === 'date') {
                    const dateElement = document.createElement('div');
                    dateElement.className = 'date-separator';
                    dateElement.innerHTML = `<span>${item.label}</span>`;
                    container.appendChild(dateElement);
                } else if (item.type === 'message') {
                    const messageElement = this.createMessageElement(item);
                    container.appendChild(messageElement);
                }
            });
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
            
        } finally {
            this.isRendering = false;
        }
    }
    
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} ${message.isConsecutive ? 'consecutive-message' : 'first-in-group'} ${message.isLastSent ? 'last-sent' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.sender_id);
        messageDiv.setAttribute('data-read-status', message.read_status || 'sent');
        
        const readStatus = message.read_status || 'sent';
        
        messageDiv.innerHTML = `
            <p class="message-content">${message.content || ''}</p>
            <div class="message-time">
                ${new Date(message.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
            </div>
            ${message.isOwn ? `
            <div class="read-receipt-indicator" data-status="${readStatus}">
                <div class="read-receipt-circle">
                    ${readStatus === 'read' && message.read_avatar ? 
                        `<img src="${message.read_avatar}" class="read-receipt-avatar" />` :
                        `<span class="read-receipt-icon">${this.getReadReceiptIcon(readStatus)}</span>`
                    }
                </div>
            </div>
            ` : ''}
        `;
        
        return messageDiv;
    }
    
    getReadReceiptIcon(status) {
        switch (status) {
            case 'sent': return '&#10003;';
            case 'delivered': return '&#10003;&#10003;';
            case 'online': return '&#10003;';
            default: return '&#10003;';
        }
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
            
            console.log('Connecting WebSocket to:', wsUrl);
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected successfully');
                this.reconnectAttempts = 0;
                this.processMessageQueue();
            };
            
            this.socket.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error, e.data);
                }
            };
            
            this.socket.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.attemptReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } else {
            console.warn('No conversation ID available for WebSocket connection');
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
        console.log('WebSocket message received:', data);
        
        try {
            switch (data.type) {
                case 'message':
                    console.log('Processing message:', data.data);
                    
                    // Decrypt message if encrypted
                    let content = data.data.content;

                    if (data.data.is_encrypted && this.e2eEncryption) {
                        try {
                            content = await this.e2eEncryption.decryptMessage(data.data.encrypted_content);
                        } catch (error) {
                            console.error('Failed to decrypt message:', error);
                            content = '[Encrypted message - unable to decrypt]';
                        }
                    }
                    
                    // STATE-DRIVEN: Add to state and render
                    console.log('Adding message to state:', data.data);
                    // Normalize sender structure before adding to state
                    const normalizedMessage = {
                    id: data.data.id,
                    conversation: Number(data.data.conversation),

                    content,
                    encrypted_content: data.data.encrypted_content || null,

                    sender_id: Number(data.data.sender?.id ?? data.data.sender_id),

                    sender: data.data.sender
                        ? {
                            ...data.data.sender,
                            id: Number(data.data.sender.id)
                        }
                        : null,

                    reply_to: data.data.reply_to || null,

                    attachment: data.data.attachment || null,
                    attachment_type: data.data.attachment_type || null,

                    reactions: data.data.reactions || [],
                    read_receipts: data.data.read_receipts || [],

                    read_status: data.data.read_status || 'sent',
                    read_avatar: data.data.read_avatar || null,

                    is_deleted: data.data.is_deleted ?? false,
                    is_optimistic: data.data.is_optimistic ?? false,

                    created_at: new Date(data.data.created_at).toISOString(),
                    edited_at: data.data.edited_at
                        ? new Date(data.data.edited_at).toISOString()
                        : null
                };
                    this.addMessage(normalizedMessage);
                    this.updateConversationPreview(normalizedMessage);
                    break;
                case 'typing':
                    this.handleTypingIndicator(data);
                    break;
                case 'read_receipt':
                    this.handleReadReceipt(data);
                    break;
                default:
                    console.warn('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error, data);
        }
    }
    
    async sendMessage(messageContent = null) {
        const input = document.getElementById('messageInput');
        const content = messageContent || input.value.trim();
        const userId = Number(this.currentUserId);

        if (!content) return;

        // Create optimistic message for immediate UI feedback
        const tempId = `temp_${Date.now()}_${Math.random()}`;
        const optimisticMessage = {
            id: tempId,
            conversation: Number(this.conversationId),
            sender_id: userId,
            sender: {
                id: userId,
                username: 'You'
            },
            content: content,
            encrypted_content: null,
            is_encrypted: false,
            attachment: null,
            attachment_type: null,
            reply_to: this.replyToMessageId || null,
            reactions: [],
            read_receipts: [],
            created_at: new Date().toISOString(),
            edited_at: null,
            is_deleted: false,
            is_optimistic: true
        };

        // Add optimistic message to state
        this.addMessage(optimisticMessage);

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
            this.messageQueue.push({
                ...messageData,
                conversation: Number(this.conversationId),
                sender_id: Number(this.currentUserId),
                sender: {
                    id: Number(this.currentUserId),
                    username: 'You'
                },
                content: content,
                encrypted_content: messageData.encrypted_content || null,
                is_encrypted: messageData.is_encrypted || false,
                reply_to: this.replyToMessageId || null,
                created_at: new Date().toISOString(),
                is_optimistic: true
            });
            console.log('Message queued (socket not connected)');
        }
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.socket.readyState === WebSocket.OPEN) {
            const message = this.messageQueue.shift();
            this.socket.send(JSON.stringify(message));
        }
    }
    
    // REMOVED: displayMessage() - replaced by state-driven render()
    
    // REMOVED: getMessageDate() - now handled in buildView()
    
    // REMOVED: formatDateLabel() - moved to view model layer
    
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
        const conversationItem = document.querySelector(`[data-conversation-id="${message.conversation || message.conversation_id}"]`);
        if (conversationItem) {
            const preview = conversationItem.querySelector('.text-truncate.small');
            if (preview) {
                const senderName = message.sender?.username || message.sender_name || 'Unknown';
                preview.textContent = `${senderName}: ${message.content.substring(0, 30)}`;
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
        
        // Update message in state
        const messageIndex = this.messages.findIndex(m => m.id == message_id);
        if (messageIndex !== -1) {
            this.messages[messageIndex].read_status = status;
            this.messages[messageIndex].read_avatar = user_avatar;
            this.render(); // Re-render to show updated read receipt
        }
        
        // Update conversation list read receipt
        this.updateConversationListReadReceipt(status, user_avatar);
    }
    
    // REMOVED: updateReadReceiptStatus() - now handled in state-driven render()
    // REMOVED: updateReadReceiptIndicator() - now handled in createMessageElement()
    
    updateConversationListReadReceipt(status, userAvatar = null) {
        // Find the current conversation's read receipt in the conversation list
        const currentConversationLink = document.querySelector(`a[href*="/conversation/${this.conversationId}/"]`);
        if (!currentConversationLink) return;
        
        const indicator = currentConversationLink.querySelector('.read-receipt-indicator');
        if (!indicator) return;
        
        // Update indicator based on status
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
    
    // REMOVED: checkRecipientOnlineStatus() - now handled through state-driven read receipts
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.messagingManager = new MessagingManager();
});
