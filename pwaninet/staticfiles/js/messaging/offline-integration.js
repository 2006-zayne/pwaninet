/**
 * Offline Integration Layer for PwaniNet Messaging
 * Integrates offline capabilities with existing messaging system
 */

class OfflineIntegration {
    constructor() {
        this.messagingManager = null;
        this.isOfflineMode = false;
        this.initialized = false;
        
        this.init();
    }

    async init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    async setup() {
        // Initialize all offline components
        await Promise.all([
            window.offlineCache?.init(),
            this.waitForMessagingManager()
        ]);

        if (window.networkStatus && window.syncManager && window.offlineUI) {
            this.setupEventListeners();
            this.enhanceMessagingManager();
            this.initialized = true;
            
            console.log('Offline integration initialized successfully');
        }
    }

    async waitForMessagingManager() {
        // Wait for the existing messaging manager to be available
        const maxWait = 5000; // 5 seconds max wait
        const startTime = Date.now();
        
        while (!window.messagingManager && Date.now() - startTime < maxWait) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        this.messagingManager = window.messagingManager;
        return this.messagingManager;
    }

    setupEventListeners() {
        // Listen to network status changes
        window.networkStatus.addListener((event, data) => {
            this.handleNetworkChange(event, data);
        });

        // Listen to page unload to save state
        window.addEventListener('beforeunload', () => {
            this.saveCurrentState();
        });

        // Listen to page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.initialized) {
                this.checkAndRefreshData();
            }
        });
    }

    handleNetworkChange(event, data) {
        this.isOfflineMode = event === 'offline';
        
        if (this.isOfflineMode) {
            this.switchToOfflineMode();
        } else {
            this.switchToOnlineMode();
        }
    }

    switchToOfflineMode() {
        console.log('Switching to offline mode');
        
        // Load conversations from cache if needed
        this.loadConversationsFromCache();
        
        // Load messages for current conversation if needed
        this.loadCurrentConversationFromCache();
        
        // Update UI
        window.offlineUI.showOfflineIndicators();
    }

    switchToOnlineMode() {
        console.log('Switching to online mode');
        
        // Start sync process
        window.syncManager.syncAll();
        
        // Update UI
        window.offlineUI.hideOfflineIndicators();
    }

    enhanceMessagingManager() {
        if (!this.messagingManager) return;

        // Override message sending to support offline
        const originalSendMessage = this.messagingManager.sendMessage;
        this.messagingManager.sendMessage = async (content, type = 'text', attachments = []) => {
            if (window.networkStatus?.isOnline) {
                // Online: use original method
                const result = await originalSendMessage.call(this.messagingManager, content, type, attachments);
                
                // Cache the sent message
                if (result && result.message) {
                    await window.offlineCache.saveMessage(result.message);
                }
                
                return result;
            } else {
                // Offline: save to outbox
                return this.sendOfflineMessage(content, type, attachments);
            }
        };

        // Override message loading to support cache
        const originalLoadMessages = this.messagingManager.loadInitialMessages;
        this.messagingManager.loadInitialMessages = async () => {
            if (window.networkStatus?.isOnline) {
                // Online: try server first, fallback to cache
                try {
                    const result = await originalLoadMessages.call(this.messagingManager);
                    
                    // Cache loaded messages
                    if (result && result.length > 0) {
                        await window.offlineCache.saveMessages(result);
                    }
                    
                    return result;
                } catch (error) {
                    console.log('Server load failed, using cache:', error);
                    return this.loadMessagesFromCache();
                }
            } else {
                // Offline: load from cache
                return this.loadMessagesFromCache();
            }
        };

        // Enhance WebSocket handling
        const originalConnectWebSocket = this.messagingManager.connectWebSocket;
        this.messagingManager.connectWebSocket = () => {
            if (window.networkStatus?.isOnline) {
                return originalConnectWebSocket.call(this.messagingManager);
            } else {
                console.log('Skipping WebSocket connection while offline');
                return Promise.resolve();
            }
        };
    }

    async sendOfflineMessage(content, type = 'text', attachments = []) {
        const conversationId = this.messagingManager.conversationId;
        const tempId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const messageData = {
            conversationId,
            content,
            type,
            attachments,
            tempId,
            sender: this.messagingManager.currentUserId,
            timestamp: new Date().toISOString()
        };

        try {
            // Save to outbox
            const outboxId = await window.syncManager.saveToOutbox(messageData);
            
            // Show pending message in UI
            window.offlineUI.showPendingMessage({ ...messageData, id: outboxId });
            
            // Add to local messages array
            this.messagingManager.messages.push(messageData);
            
            return {
                success: true,
                tempId,
                offline: true,
                message: messageData
            };
            
        } catch (error) {
            console.error('Failed to save offline message:', error);
            throw error;
        }
    }

    async loadMessagesFromCache() {
        if (!this.messagingManager.conversationId) return [];
        
        try {
            const messages = await window.offlineCache.getMessages(
                this.messagingManager.conversationId,
                100
            );
            
            // Update messaging manager state
            this.messagingManager.messages = messages;
            
            // Render messages
            this.renderMessages(messages);
            
            return messages;
            
        } catch (error) {
            console.error('Failed to load messages from cache:', error);
            return [];
        }
    }

    async loadConversationsFromCache() {
        try {
            const conversations = await window.offlineCache.getConversations(50);
            
            // Update conversation list if it exists
            this.updateConversationList(conversations);
            
            return conversations;
            
        } catch (error) {
            console.error('Failed to load conversations from cache:', error);
            return [];
        }
    }

    async loadCurrentConversationFromCache() {
        if (!this.messagingManager.conversationId) return;
        
        try {
            const conversation = await window.offlineCache.getConversation(
                this.messagingManager.conversationId
            );
            
            if (conversation) {
                this.updateConversationHeader(conversation);
            }
            
        } catch (error) {
            console.error('Failed to load conversation from cache:', error);
        }
    }

    renderMessages(messages) {
        const messagesArea = document.querySelector('.messages-area');
        if (!messagesArea) return;
        
        // Clear existing messages
        messagesArea.innerHTML = '';
        
        // Render each message
        messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            messagesArea.appendChild(messageElement);
        });
        
        // Scroll to bottom
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    createMessageElement(message) {
        const isSent = message.sender === this.messagingManager.currentUserId;
        const div = document.createElement('div');
        div.className = `message ${isSent ? 'sent' : 'received'}`;
        div.dataset.messageId = message.id;
        
        div.innerHTML = `
            <div class="message-bubble ${isSent ? 'sent' : 'received'}">
                <div class="message-text">${this.escapeHtml(message.content)}</div>
            </div>
            <div class="message-meta">
                <span class="timestamp">${this.formatTime(message.timestamp)}</span>
            </div>
        `;
        
        return div;
    }

    updateConversationList(conversations) {
        const conversationList = document.querySelector('.conversation-list');
        if (!conversationList) return;
        
        // This would update the conversation list UI
        // Implementation depends on the existing conversation list structure
        conversations.forEach(conversation => {
            const element = this.createConversationElement(conversation);
            conversationList.appendChild(element);
        });
    }

    createConversationElement(conversation) {
        const div = document.createElement('div');
        div.className = 'conversation-item';
        div.dataset.conversationId = conversation.id;
        
        div.innerHTML = `
            <div class="conversation-avatar">
                <img src="${conversation.other_user_profile_pic || '/static/images/default-avatar.png'}" 
                     alt="${conversation.other_user_name}" 
                     class="rounded-circle">
            </div>
            <div class="conversation-details">
                <div class="conversation-name">${conversation.other_user_name}</div>
                <div class="conversation-preview">${conversation.last_message_content || 'No messages yet'}</div>
            </div>
            <div class="conversation-time">${this.formatTime(conversation.updated_at)}</div>
        `;
        
        return div;
    }

    updateConversationHeader(conversation) {
        const header = document.querySelector('.chat-header');
        if (!header) return;
        
        const nameElement = header.querySelector('.chat-header-name');
        if (nameElement) {
            nameElement.textContent = conversation.other_user_name;
        }
        
        const avatarElement = header.querySelector('.chat-header-avatar img');
        if (avatarElement) {
            avatarElement.src = conversation.other_user_profile_pic || '/static/images/default-avatar.png';
        }
    }

    async checkAndRefreshData() {
        if (window.networkStatus?.isOnline) {
            // Refresh current conversation if needed
            if (this.messagingManager.conversationId) {
                await this.syncCurrentConversation();
            }
        }
    }

    async syncCurrentConversation() {
        try {
            // Get latest cached message timestamp
            const cachedMessages = await window.offlineCache.getMessages(
                this.messagingManager.conversationId, 
                1
            );
            
            const lastCachedTime = cachedMessages.length > 0 
                ? cachedMessages[0].timestamp 
                : null;
            
            // Fetch new messages
            const url = lastCachedTime 
                ? `/messaging/v1/conversations/${this.messagingManager.conversationId}/messages/?after=${lastCachedTime}`
                : `/messaging/v1/conversations/${this.messagingManager.conversationId}/messages/`;
            
            const response = await fetch(url);
            
            if (response.ok) {
                const newMessages = await response.json();
                
                if (newMessages.length > 0) {
                    // Cache new messages
                    await window.offlineCache.saveMessages(newMessages);
                    
                    // Add to UI
                    newMessages.forEach(message => {
                        this.messagingManager.messages.push(message);
                        const element = this.createMessageElement(message);
                        document.querySelector('.messages-area').appendChild(element);
                    });
                    
                    // Scroll to bottom
                    document.querySelector('.messages-area').scrollTop = 
                        document.querySelector('.messages-area').scrollHeight;
                }
            }
            
        } catch (error) {
            console.error('Failed to sync current conversation:', error);
        }
    }

    async saveCurrentState() {
        try {
            // Save current conversation to cache
            if (this.messagingManager.conversationId) {
                const conversation = await this.getConversationFromServer();
                if (conversation) {
                    await window.offlineCache.saveConversation(conversation);
                }
            }
            
            // Save current messages to cache
            if (this.messagingManager.messages.length > 0) {
                await window.offlineCache.saveMessages(this.messagingManager.messages);
            }
            
        } catch (error) {
            console.error('Failed to save current state:', error);
        }
    }

    async getConversationFromServer() {
        try {
            const response = await fetch(
                `/messaging/v1/conversations/${this.messagingManager.conversationId}/`
            );
            
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to get conversation from server:', error);
        }
        
        return null;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public API for external use
    isOffline() {
        return this.isOfflineMode;
    }

    async clearCache() {
        if (window.offlineCache) {
            await window.offlineCache.clearCache();
        }
    }

    getCacheInfo() {
        return {
            initialized: this.initialized,
            isOffline: this.isOfflineMode,
            hasCache: !!window.offlineCache?.db,
            cacheSize: window.offlineCache?.getCacheSize() || 0
        };
    }
}

// Global instance
window.offlineIntegration = new OfflineIntegration();
