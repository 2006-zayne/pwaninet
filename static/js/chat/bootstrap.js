/**
 * Bootstrap - Single entry point with mandatory SOT data flow enforcement
 * Enforces: websocket → message-service → store → ui-controller → renderer
 */

import { appController } from './core/app-controller.js';
import { messageService } from './core/message-service.js';
import { webSocketManager } from './core/websocket.js';
import { store } from './core/store.js';
import { uiController } from './ui/ui-controller.js';
import { attachmentService } from './features/attachments/attachment.service.js';
import { attachmentUI } from './features/attachments/attachment-ui.js';
import { cameraService } from './features/camera/camera.service.js';
import { voiceService } from './features/voice/voice.service.js';
import { emojiService } from './features/emoji/emoji.service.js';
import { contextMenuService } from './features/context-menu/context-menu.service.js';

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
        currentUserId: parseInt(chatContainer?.dataset.userId || document.body.dataset.userId),
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

    // 5. Feature services (context menu, voice, emoji, camera, attachment)
    contextMenuService.init();
    console.log('✅ Context menu service initialized');
    
    attachmentService.init();
    cameraService.init();
    voiceService.init();
    emojiService.init();
    console.log('✅ Attachment and emoji services initialized');

    // 6. Attachment UI
    attachmentUI.init();
    console.log('✅ Attachment UI initialized');

    // 7. App controller (orchestration ONLY)
    appController.init(config);
    console.log('✅ App controller initialized (orchestration)');

    // Expose globally for debugging
    window.appController = appController;
    window.store = store;
    window.messageService = messageService;
    window.webSocketManager = webSocketManager;
    window.uiController = uiController;
    window.attachmentService = attachmentService;
    window.attachmentUI = attachmentUI;
    window.cameraService = cameraService;
    window.voiceService = voiceService;
    window.emojiService = emojiService;
    window.contextMenuService = contextMenuService;
    window.messageSoundManager = messageSoundManager;

    console.log('🎉 SOT architecture initialized with mandatory data flow enforcement');
    console.log('📊 Data flow: websocket → message-service → store → ui-controller → renderer');
});
