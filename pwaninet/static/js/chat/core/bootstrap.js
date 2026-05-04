/**
 * Bootstrap - Single entry point with mandatory SOT data flow enforcement
 * Enforces: websocket → message-service → store → ui-controller → renderer
 */

import { appController } from './app-controller.js';
import { messageService } from './message-service.js';
import { webSocketManager } from './websocket.js';
import { store } from './store.js';
import { uiController } from '../ui/ui-controller.js';
import { voiceService } from '../features/voice/voice.service.js';
import { attachmentUI } from '../features/attachments/attachment-ui.js';

// Load encryption module if available
if (typeof E2EEncryption === 'undefined') {
    console.warn('E2EEncryption module not loaded');
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Get configuration from data attributes
    const chatContainer = document.querySelector('.chat-container');
    const config = {
        conversationId: parseInt(chatContainer?.dataset.conversationId || document.body.dataset.conversationId),
        currentUserId: parseInt(document.body.dataset.userId),
        isEncrypted: (chatContainer?.dataset.isEncrypted || document.body.dataset.isEncrypted) === 'true'
    };

    // Validate configuration
    if (!config.conversationId || !config.currentUserId) {
        console.error('Invalid chat configuration:', config);
        return;
    }

    // Initialize with strict SOT data flow order
    console.log('🔒 Initializing with strict SOT architecture...');

    // 1. Store first (SOT) - ONLY mutation source
    store.init(config);
    console.log('✅ Store initialized (SOT)');

    // 2. Message service (ONLY ingestion layer)
    messageService.init();
    console.log('✅ Message service initialized (ingestion layer)');

    // 3. WebSocket (transport ONLY)
    webSocketManager.init(config.conversationId);
    console.log('✅ WebSocket initialized (transport layer)');

    // 4. UI controller (read-only consumer)
    uiController.init();
    console.log('✅ UI controller initialized (read-only consumer)');

    // 5. App controller (orchestration ONLY)
    appController.init(config);
    console.log('✅ App controller initialized (orchestration)');

    // 6. Voice service
    voiceService.init();
    console.log('✅ Voice service initialized');

    // 7. Attachment UI
    attachmentUI.init();
    console.log('✅ Attachment UI initialized');

    // Expose globally for debugging
    window.appController = appController;
    window.store = store;
    window.messageService = messageService;
    window.webSocketManager = webSocketManager;
    window.uiController = uiController;
    window.voiceService = voiceService;
    window.attachmentUI = attachmentUI;

    console.log('🎉 SOT architecture initialized with mandatory data flow enforcement');
    console.log('📊 Data flow: websocket → message-service → store → ui-controller → renderer');
});
