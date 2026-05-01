/**
 * Bootstrap - Single entry point for chat system
 * Initializes AppController with configuration from Django template
 * Follows strict layered architecture with event-driven data flow
 */

import { appController } from './core/app-controller.js';
import { syncEngine } from './core/sync-engine.js';
import { uiController } from './ui/ui-controller.js';
import { emojiService } from './features/emoji/emoji.service.js';
import { cameraService } from './features/camera/camera.service.js';
import { voiceService } from './features/voice/voice.service.js';
import { attachmentService } from './features/attachments/attachment.service.js';
import { themeService } from './ui/theme/theme.service.js';

// Load encryption module if available
if (typeof E2EEncryption === 'undefined') {
    console.warn('E2EEncryption module not loaded');
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Get configuration from data attributes
    const config = {
        conversationId: parseInt(document.body.dataset.conversationId),
        currentUserId: parseInt(document.body.dataset.userId),
        isEncrypted: document.body.dataset.isEncrypted === 'true'
    };

    // Validate configuration
    if (!config.conversationId || !config.currentUserId) {
        console.error('Invalid chat configuration:', config);
        return;
    }

    // Initialize services
    syncEngine.init();
    emojiService.init();
    cameraService.init();
    voiceService.init();
    attachmentService.init();
    themeService.init();

    // Initialize UI controller
    uiController.init(config);

    // Initialize app controller (core orchestration)
    appController.init(config);

    // Expose globally for debugging
    window.appController = appController;
    window.uiController = uiController;
    window.store = appController.getStore();
    window.eventBus = appController.getEventBus();

    console.log('Chat system initialized with layered architecture');
});
