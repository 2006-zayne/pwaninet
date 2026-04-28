class MessagingManager {
    constructor() {
        this.socket = null;
        this.conversationId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.messageQueue = [];
        this.typingTimeout = null;
        this.currentUserId = null;
        
        this.init();
    }
    
    init() {
        this.currentUserId = document.body.dataset.userId;
        this.conversationId = document.body.dataset.conversationId;
        this.setupEventListeners();
        this.connectWebSocket();
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
        }
        
        // Send button
        const sendButton = document.getElementById('sendMessage');
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
    
    handleMessage(data) {
        switch (data.type) {
            case 'message':
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
    
    sendMessage(messageContent = null) {
        const input = document.getElementById('messageInput');
        const content = messageContent || input.value.trim();
        
        if (!content) return;
        
        const messageData = {
            type: 'chat_message',
            content: content,
            reply_to: this.replyToMessageId || null
        };
        
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
        const messageHtml = `
            <div class="d-flex ${isOwn ? 'justify-content-end' : 'justify-content-start'} mb-3" data-message-id="${message.id}">
                <div class="d-flex flex-column ${isOwn ? 'align-items-end' : 'align-items-start'}" style="max-width: 70%;">
                    <div class="card" style="background-color: ${isOwn ? '#0095f6' : '#efefef'}; color: ${isOwn ? '#fff' : '#000'}; border: none; border-radius: 22px; ${isOwn ? 'border-bottom-right-radius: 4px;' : 'border-bottom-left-radius: 4px;'}">
                        <div class="card-body py-2 px-3">
                            ${message.reply_to ? `
                                <div class="small mb-1 border-bottom pb-1" style="color: ${isOwn ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.5)'};">
                                    <i class="bi bi-reply"></i> ${message.reply_to.sender.username}: ${message.reply_to.content.substring(0, 20)}...
                                </div>
                            ` : ''}
                            <p class="mb-0">${message.content}</p>
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-2 mt-1">
                        <small style="font-size: 0.7rem; color: rgba(0,0,0,0.5);">
                            ${new Date(message.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </small>
                        ${isOwn ? '<i class="bi bi-check2-all" style="font-size: 0.7rem; color: #0095f6;"></i>' : ''}
                        <button class="btn btn-link p-0" style="font-size: 0.8rem; color: #000;" data-bs-toggle="dropdown">
                            <i class="bi bi-emoji-smile"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item add-reaction" data-emoji="👍" data-message-id="${message.id}">👍</a></li>
                            <li><a class="dropdown-item add-reaction" data-emoji="❤️" data-message-id="${message.id}">❤️</a></li>
                            <li><a class="dropdown-item add-reaction" data-emoji="😂" data-message-id="${message.id}">😂</a></li>
                            <li><a class="dropdown-item add-reaction" data-emoji="😮" data-message-id="${message.id}">😮</a></li>
                            <li><a class="dropdown-item add-reaction" data-emoji="😢" data-message-id="${message.id}">😢</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', messageHtml);
        container.scrollTop = container.scrollHeight;
        
        // Re-attach event listeners for new reaction buttons
        this.attachReactionListeners();
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
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.messagingManager = new MessagingManager();
});
