/**
 * Simple Chat Theme Handler
 * Handles theme switching for chat conversations
 */
class ChatThemeHandler {
    constructor() {
        this.currentConversationId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadCurrentTheme();
    }

    setupEventListeners() {
        // Theme button in dropdown
        const themeBtn = document.getElementById('themeBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.showThemeModal();
            });
        }

        // Close modal
        const closeBtn = document.getElementById('closeThemeModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideThemeModal());
        }

        // Close on backdrop click
        const modal = document.getElementById('themeModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideThemeModal();
                }
            });
        }

        // Theme tabs
        document.querySelectorAll('.theme-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Theme options (backgrounds)
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', () => {
                this.applyBackgroundTheme(option.dataset.theme);
            });
        });

        // Apply background button
        const applyBackgroundBtn = document.getElementById('applyBackgroundBtn');
        if (applyBackgroundBtn) {
            applyBackgroundBtn.addEventListener('click', () => {
                this.saveTheme();
            });
        }

        // Overlay controls
        const overlayEnabled = document.getElementById('overlayEnabled');
        const overlayOpacitySlider = document.getElementById('overlayOpacitySlider');
        const overlayOpacityValue = document.getElementById('overlayOpacityValue');
        
        if (overlayOpacitySlider && overlayOpacityValue) {
            overlayOpacitySlider.addEventListener('input', (e) => {
                overlayOpacityValue.textContent = e.target.value + '%';
                this.updateOverlay();
            });
        }

        if (overlayEnabled) {
            overlayEnabled.addEventListener('change', () => {
                this.updateOverlay();
            });
        }

        // Overlay color
        const overlayColorPicker = document.getElementById('overlayColorPicker');
        const overlayColorHex = document.getElementById('overlayColorHex');
        
        if (overlayColorPicker && overlayColorHex) {
            overlayColorPicker.addEventListener('input', (e) => {
                overlayColorHex.textContent = e.target.value;
                this.updateOverlay();
            });
        }

        // Opacity presets
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (overlayOpacitySlider) {
                    overlayOpacitySlider.value = btn.dataset.opacity;
                    overlayOpacityValue.textContent = btn.dataset.opacity + '%';
                }
                this.updateOverlay();
            });
        });

        // Color presets
        document.querySelectorAll('.color-preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (overlayColorPicker) {
                    overlayColorPicker.value = btn.dataset.color;
                    overlayColorHex.textContent = btn.dataset.color;
                }
                this.updateOverlay();
            });
        });

        // Wallpaper upload button
        const uploadWallpaperBtn = document.getElementById('uploadWallpaperBtn');
        const wallpaperImageInput = document.getElementById('wallpaperImageInput');
        
        if (uploadWallpaperBtn && wallpaperImageInput) {
            uploadWallpaperBtn.addEventListener('click', () => {
                wallpaperImageInput.click();
            });
            
            wallpaperImageInput.addEventListener('change', (e) => {
                this.handleWallpaperUpload(e);
            });
        }

        // Bubble options
        document.querySelectorAll('.bubble-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.bubble-option').forEach(o => o.classList.remove('active'));
                option.classList.add('active');
                this.previewBubbleStyle(option.dataset.bubble);
            });
        });

        // Apply bubbles button
        const applyBubblesBtn = document.getElementById('applyBubblesBtn');
        if (applyBubblesBtn) {
            applyBubblesBtn.addEventListener('click', () => {
                this.applyBubbleTheme();
            });
        }

        // Bubble color pickers
        const sentBubbleColor = document.getElementById('sentBubbleColor');
        const sentBubbleHex = document.getElementById('sentBubbleHex');
        const receivedBubbleColor = document.getElementById('receivedBubbleColor');
        const receivedBubbleHex = document.getElementById('receivedBubbleHex');

        if (sentBubbleColor && sentBubbleHex) {
            sentBubbleColor.addEventListener('input', (e) => {
                sentBubbleHex.textContent = e.target.value;
                this.previewBubbleColors();
            });
        }

        if (receivedBubbleColor && receivedBubbleHex) {
            receivedBubbleColor.addEventListener('input', (e) => {
                receivedBubbleHex.textContent = e.target.value;
                this.previewBubbleColors();
            });
        }
    }

    showThemeModal() {
        const modal = document.getElementById('themeModal');
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    hideThemeModal() {
        const modal = document.getElementById('themeModal');
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    switchTab(tabName) {
        // Update tabs
        document.querySelectorAll('.theme-tab').forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            }
        });

        // Update content
        document.querySelectorAll('.theme-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const activeContent = document.getElementById(tabName + '-tab');
        if (activeContent) {
            activeContent.classList.add('active');
        }
    }

    applyBackgroundTheme(themeName) {
        const messagesArea = document.getElementById('messagesContainer');
        if (!messagesArea) return;

        // Remove active class from all options
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('active');
            if (option.dataset.theme === themeName) {
                option.classList.add('active');
            }
        });

        // Apply theme
        const themeMap = {
            'light': () => {
                messagesArea.style.background = '#f8fafc';
                messagesArea.style.backgroundImage = 'none';
            },
            'dark': () => {
                messagesArea.style.background = '#1f2937';
                messagesArea.style.backgroundImage = 'none';
            },
            'wallpaper-1': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            },
            'wallpaper-2': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
            },
            'wallpaper-3': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
            },
            'wallpaper-4': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)';
            },
            'wallpaper-5': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)';
            },
            'wallpaper-6': () => {
                messagesArea.style.backgroundImage = 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)';
            }
        };

        if (themeMap[themeName]) {
            themeMap[themeName]();
            this.currentTheme = themeName;
        }
    }

    updateOverlay() {
        const messagesArea = document.getElementById('messagesContainer');
        if (!messagesArea) return;

        const overlayEnabled = document.getElementById('overlayEnabled');
        const overlayOpacitySlider = document.getElementById('overlayOpacitySlider');
        const overlayColorPicker = document.getElementById('overlayColorPicker');

        // Remove existing overlay
        let overlay = messagesArea.querySelector('.chat-overlay');
        if (overlay) {
            overlay.remove();
        }

        // Only add overlay if enabled AND opacity > 0
        const isEnabled = overlayEnabled && overlayEnabled.checked;
        const opacity = overlayOpacitySlider ? overlayOpacitySlider.value / 100 : 0.3;
        
        if (isEnabled && opacity > 0) {
            overlay = document.createElement('div');
            overlay.className = 'chat-overlay';
            const color = overlayColorPicker ? overlayColorPicker.value : '#ffffff';
            overlay.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: ${color};
                opacity: ${opacity};
                pointer-events: none;
                z-index: 1;
            `;
            messagesArea.style.position = 'relative';
            messagesArea.appendChild(overlay);
        }

        // Update CSS variables to match settings
        if (messagesArea) {
            const overlayColor = overlayColorPicker ? overlayColorPicker.value : '#ffffff';
            const overlayOpacity = isEnabled && opacity > 0 ? opacity : 0;
            messagesArea.style.setProperty('--chat-overlay-color', overlayColor);
            messagesArea.style.setProperty('--chat-overlay-opacity', overlayOpacity);
        }
    }

    previewBubbleStyle(bubbleStyle) {
        const demoArea = document.getElementById('demoMessageArea');
        if (!demoArea) return;

        document.querySelectorAll('.demo-bubble').forEach(bubble => {
            switch(bubbleStyle) {
                case 'rounded':
                    bubble.style.borderRadius = '25px';
                    break;
                case 'square':
                    bubble.style.borderRadius = '4px';
                    break;
                default:
                    bubble.style.borderRadius = '';
            }
        });
    }

    previewBubbleColors() {
        const sentColor = document.getElementById('sentBubbleColor').value;
        const receivedColor = document.getElementById('receivedBubbleColor').value;

        document.querySelectorAll('.demo-bubble.sent').forEach(bubble => {
            bubble.style.backgroundColor = sentColor;
            bubble.style.color = this.getContrastColor(sentColor);
        });

        document.querySelectorAll('.demo-bubble.received').forEach(bubble => {
            bubble.style.backgroundColor = receivedColor;
            bubble.style.color = this.getContrastColor(receivedColor);
        });
    }

    applyBubbleTheme() {
        const messagesArea = document.getElementById('messagesContainer');
        if (!messagesArea) return;

        const activeBubbleOption = document.querySelector('.bubble-option.active');
        const bubbleStyle = activeBubbleOption ? activeBubbleOption.dataset.bubble : 'default';
        const sentColor = document.getElementById('sentBubbleColor').value;
        const receivedColor = document.getElementById('receivedBubbleColor').value;

        // Apply to actual message bubbles directly (correct selector)
        document.querySelectorAll('.message-bubble.sent').forEach(bubble => {
            bubble.style.backgroundColor = sentColor;
            bubble.style.color = this.getContrastColor(sentColor);
            switch(bubbleStyle) {
                case 'rounded':
                    bubble.style.borderRadius = '25px';
                    break;
                case 'square':
                    bubble.style.borderRadius = '4px';
                    break;
                default:
                    bubble.style.borderRadius = '';
            }
        });

        document.querySelectorAll('.message-bubble.received').forEach(bubble => {
            bubble.style.backgroundColor = receivedColor;
            bubble.style.color = this.getContrastColor(receivedColor);
            switch(bubbleStyle) {
                case 'rounded':
                    bubble.style.borderRadius = '25px';
                    break;
                case 'square':
                    bubble.style.borderRadius = '4px';
                    break;
                default:
                    bubble.style.borderRadius = '';
            }
        });

        this.hideThemeModal();
        this.showNotification('Bubble theme applied!');
    }

    getContrastColor(hexColor) {
        // Convert hex to RGB
        const r = parseInt(hexColor.substr(1, 2), 16);
        const g = parseInt(hexColor.substr(3, 2), 16);
        const b = parseInt(hexColor.substr(5, 2), 16);

        // Calculate luminance
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

        return luminance > 0.5 ? '#000000' : '#ffffff';
    }

    handleWallpaperUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select an image file', 'error');
            return;
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showNotification('File size must be less than 5MB', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const messagesArea = document.getElementById('messagesContainer');
            if (messagesArea) {
                messagesArea.style.backgroundImage = `url(${e.target.result})`;
                messagesArea.style.backgroundSize = 'cover';
                messagesArea.style.backgroundPosition = 'center';
                messagesArea.style.backgroundRepeat = 'no-repeat';

                // Store as custom wallpaper
                this.currentTheme = 'custom-wallpaper';
                this.customWallpaperData = e.target.result;

                // Update active state
                document.querySelectorAll('.theme-option').forEach(option => {
                    option.classList.remove('active');
                });

                this.showNotification('Wallpaper uploaded successfully!');
            }
        };
        reader.onerror = () => {
            this.showNotification('Failed to read image file', 'error');
        };
        reader.readAsDataURL(file);
    }

    saveTheme() {
        // Save to localStorage
        const themeData = {
            background: this.currentTheme,
            overlayEnabled: document.getElementById('overlayEnabled').checked,
            overlayOpacity: document.getElementById('overlayOpacitySlider').value,
            overlayColor: document.getElementById('overlayColorPicker').value
        };

        // Include custom wallpaper data if present
        if (this.currentTheme === 'custom-wallpaper' && this.customWallpaperData) {
            themeData.customWallpaper = this.customWallpaperData;
        }

        const conversationId = this.getConversationId();
        if (conversationId) {
            localStorage.setItem(`chat_theme_${conversationId}`, JSON.stringify(themeData));
        }

        this.hideThemeModal();
        this.showNotification('Theme saved!');
    }

    loadCurrentTheme() {
        const conversationId = this.getConversationId();
        if (!conversationId) return;

        const savedTheme = localStorage.getItem(`chat_theme_${conversationId}`);
        if (savedTheme) {
            try {
                const themeData = JSON.parse(savedTheme);
                if (themeData.background) {
                    // Handle custom wallpaper restoration
                    if (themeData.background === 'custom-wallpaper' && themeData.customWallpaper) {
                        this.customWallpaperData = themeData.customWallpaper;
                        const messagesArea = document.getElementById('messagesContainer');
                        if (messagesArea) {
                            messagesArea.style.backgroundImage = `url(${themeData.customWallpaper})`;
                            messagesArea.style.backgroundSize = 'cover';
                            messagesArea.style.backgroundPosition = 'center';
                            messagesArea.style.backgroundRepeat = 'no-repeat';
                        }
                    } else {
                        this.applyBackgroundTheme(themeData.background);
                    }
                }
                if (themeData.overlayEnabled !== undefined) {
                    document.getElementById('overlayEnabled').checked = themeData.overlayEnabled;
                }
                if (themeData.overlayOpacity) {
                    document.getElementById('overlayOpacitySlider').value = themeData.overlayOpacity;
                    document.getElementById('overlayOpacityValue').textContent = themeData.overlayOpacity + '%';
                }
                if (themeData.overlayColor) {
                    document.getElementById('overlayColorPicker').value = themeData.overlayColor;
                    document.getElementById('overlayColorHex').textContent = themeData.overlayColor;
                }
                this.updateOverlay();
            } catch (e) {
                console.error('Failed to load theme:', e);
            }
        }
    }

    getConversationId() {
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            return chatContainer.dataset.conversationId;
        }
        return document.body.dataset.conversationId;
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: var(--primary);
            color: white;
            border-radius: 8px;
            z-index: 10001;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatThemeHandler = new ChatThemeHandler();
});

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
