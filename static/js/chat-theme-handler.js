/**
 * WhatsApp-Style Chat Theme & Appearance Handler
 * Supports:
 * 1. Curated Atmosphere Presets (7 complete harmonies)
 * 2. Custom Gradients & Picture Wallpapers
 * 3. Overlay Tint & Readability Dimming
 * 4. Custom Bubble Styling & Radii
 * 5. Per-Chat Theme Persistence with User Default Fallback
 * 6. "Apply to all chats" Global Setting
 * 7. Guaranteed Composer Contrast Engine
 */
class ChatThemeHandler {
    constructor() {
        this.currentConversationId = null;
        this.activeConfig = {
            type: 'preset', // 'preset' or 'wallpaper'
            preset: 'ocean-wave',
            wallpaper: null,
            customWallpaperData: null,
            overlayEnabled: false,
            overlayOpacity: 0,
            overlayColor: '#ffffff',
            customOverlayActive: false,
            bubbleStyle: 'default',
            bubbleSentColor: '',
            bubbleReceivedColor: ''
        };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadCurrentTheme();
        this.setupThemeModeObserver();
    }

    reinit() {
        this.currentConversationId = this.getConversationId();
        this.setupEventListeners();
        this.loadCurrentTheme();
    }

    setupThemeModeObserver() {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'attributes' && (mutation.attributeName === 'data-theme' || mutation.attributeName === 'data-bs-theme')) {
                    // Re-apply current configuration to refresh contrast calculations for the new mode
                    this.applyThemeConfig(this.activeConfig, false);
                    // Guarantee any backdrop/overlay is completely eliminated
                    const overlay = document.getElementById('overlay');
                    if (overlay) overlay.classList.remove('show');
                    document.querySelectorAll('.overlay.show, .theme-modal-backdrop, .modal-backdrop, .dropdown-backdrop').forEach(el => {
                        el.classList.remove('show');
                        if (el.classList.contains('theme-modal-backdrop') || el.classList.contains('modal-backdrop') || el.classList.contains('dropdown-backdrop')) {
                            el.remove();
                        }
                    });
                }
            }
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-bs-theme'] });
    }

    getChatTarget() {
        return document.getElementById('chatMainArea') || document.querySelector('.chat-container') || document.getElementById('messagesContainer');
    }

    getConversationId() {
        const chatContainer = document.getElementById('chatMainArea') || document.querySelector('.chat-container');
        if (chatContainer && chatContainer.dataset.conversationId) {
            return chatContainer.dataset.conversationId;
        }
        return document.body.dataset.conversationId || null;
    }

    getDefaultTheme() {
        const chatContainer = document.getElementById('chatMainArea');
        const defaultFromDataset = chatContainer?.dataset?.defaultChatTheme;
        return localStorage.getItem('default_chat_theme') || defaultFromDataset || 'ocean-wave';
    }

    setupEventListeners() {
        // Dropdown Theme Button trigger
        const themeBtn = document.getElementById('themeBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const dropdownEl = document.getElementById('chatHeaderOptionsBtn');
                if (dropdownEl && window.bootstrap && bootstrap.Dropdown) {
                    const dd = bootstrap.Dropdown.getInstance(dropdownEl);
                    if (dd) dd.hide();
                }
                document.querySelectorAll('.dropdown-menu.show').forEach(m => m.classList.remove('show'));
                this.showThemePanel();
            });
        }

        // Close Panel Buttons
        const closePanelBtn = document.getElementById('closeThemePanelBtn');
        if (closePanelBtn) {
            closePanelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.hideThemePanel();
            });
        }
        const legacyCloseBtn = document.getElementById('closeThemeModal');
        if (legacyCloseBtn) {
            legacyCloseBtn.addEventListener('click', () => this.hideThemePanel());
        }

        // Save Theme Buttons
        const saveThemeBtn = document.getElementById('saveThemeBtn');
        if (saveThemeBtn) {
            saveThemeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveTheme();
            });
        }
        const saveThemePanelBtn = document.getElementById('saveThemePanelBtn');
        if (saveThemePanelBtn) {
            saveThemePanelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveTheme();
            });
        }

        // Reset Theme Button
        const resetThemeBtn = document.getElementById('resetThemeBtn');
        if (resetThemeBtn) {
            resetThemeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.resetThemeToDefault();
            });
        }

        // Tab Navigation
        document.querySelectorAll('#chatThemeNavPills [data-theme-tab], .theme-tabs [data-tab]').forEach(tabBtn => {
            tabBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const tabKey = tabBtn.dataset.themeTab || tabBtn.dataset.tab;
                this.switchTab(tabKey);
            });
        });

        // Atmosphere Presets (Curated)
        document.querySelectorAll('.preset-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const preset = option.dataset.preset;
                if (preset) {
                    this.activeConfig.type = 'preset';
                    this.activeConfig.preset = preset;
                    this.activeConfig.wallpaper = null;
                    this.activeConfig.customWallpaperData = null;
                    this.activeConfig.overlayEnabled = false;
                    this.activeConfig.overlayOpacity = 0;
                    this.activeConfig.customOverlayActive = false;
                    this.applyThemeConfig(this.activeConfig, false);
                    this.syncActiveUI();
                }
            });
        });

        // Wallpaper & Gradient options
        document.querySelectorAll('.bg-option, .theme-option:not(.preset-option)').forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const wp = option.dataset.wallpaper || option.dataset.theme;
                if (wp) {
                    this.activeConfig.type = 'wallpaper';
                    this.activeConfig.wallpaper = wp;
                    this.activeConfig.customWallpaperData = null;
                    this.applyThemeConfig(this.activeConfig, false);
                    this.syncActiveUI();
                }
            });
        });

        // Setup Delegated Event Listeners once on document
        if (!this._delegatedListenersBound) {
            this._delegatedListenersBound = true;
            document.addEventListener('click', (e) => {
                const pill = e.target.closest('.preset-opacity-btn, .opacity-presets .preset-btn');
                if (pill) {
                    e.preventDefault();
                    e.stopPropagation();
                    const op = Number(pill.dataset.opacity);
                    this.setOverlayOpacity(op, true);
                    return;
                }

                const colorPreset = e.target.closest('.color-tint-preset, .color-presets .color-preset-btn');
                if (colorPreset) {
                    e.preventDefault();
                    e.stopPropagation();
                    const color = colorPreset.dataset.color;
                    if (color) {
                        this.activeConfig.overlayColor = color;
                        const picker = document.getElementById('overlayColorPicker');
                        const hex = document.getElementById('overlayColorHex');
                        if (picker) picker.value = color;
                        if (hex) hex.textContent = color;
                        this.applyOverlay();
                        this.updateLivePreview();
                    }
                    return;
                }

                const themeTrigger = e.target.closest('#themeBtn');
                if (themeTrigger) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showThemePanel();
                    return;
                }

                const closeBtn = e.target.closest('#closeThemePanelBtn, #closeThemeModal');
                if (closeBtn) {
                    e.preventDefault();
                    this.hideThemePanel();
                    return;
                }

                const saveBtn = e.target.closest('#saveThemeBtn, #saveThemePanelBtn');
                if (saveBtn) {
                    e.preventDefault();
                    this.saveTheme();
                    return;
                }

                const resetBtn = e.target.closest('#resetThemeBtn');
                if (resetBtn) {
                    e.preventDefault();
                    this.resetThemeToDefault();
                    return;
                }
            });

            document.addEventListener('input', (e) => {
                if (e.target && e.target.id === 'overlayOpacitySlider') {
                    const op = Number(e.target.value);
                    this.setOverlayOpacity(op, false);
                } else if (e.target && e.target.id === 'overlayColorPicker') {
                    this.activeConfig.overlayColor = e.target.value;
                    const hex = document.getElementById('overlayColorHex');
                    if (hex) hex.textContent = e.target.value;
                    this.applyOverlay();
                    this.updateLivePreview();
                }
            });

            document.addEventListener('change', (e) => {
                if (e.target && e.target.id === 'overlayEnabled') {
                    this.setOverlayEnabled(e.target.checked);
                }
            });
        }

        // Bubble style selection
        document.querySelectorAll('.bubble-style-card, .bubble-option').forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                const style = card.dataset.bubbleStyle || card.dataset.bubble;
                if (style) {
                    this.activeConfig.bubbleStyle = style;
                    document.querySelectorAll('.bubble-style-card, .bubble-option').forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                    this.applyBubbleStyle(style);
                    this.updateLivePreview();
                }
            });
        });

        // Bubble color pickers
        const sentBubbleColor = document.getElementById('sentBubbleColor');
        const sentBubbleHex = document.getElementById('sentBubbleHex');
        if (sentBubbleColor) {
            sentBubbleColor.addEventListener('input', (e) => {
                this.activeConfig.bubbleSentColor = e.target.value;
                if (sentBubbleHex) sentBubbleHex.textContent = e.target.value;
                this.applyBubbleColors();
                this.updateLivePreview();
            });
        }

        const receivedBubbleColor = document.getElementById('receivedBubbleColor');
        const receivedBubbleHex = document.getElementById('receivedBubbleHex');
        if (receivedBubbleColor) {
            receivedBubbleColor.addEventListener('input', (e) => {
                this.activeConfig.bubbleReceivedColor = e.target.value;
                if (receivedBubbleHex) receivedBubbleHex.textContent = e.target.value;
                this.applyBubbleColors();
                this.updateLivePreview();
            });
        }

        // Custom Wallpaper Upload
        const uploadWallpaperBtn = document.getElementById('uploadWallpaperBtn');
        const wallpaperImageInput = document.getElementById('wallpaperImageInput');
        if (uploadWallpaperBtn && wallpaperImageInput) {
            uploadWallpaperBtn.addEventListener('click', (e) => {
                e.preventDefault();
                wallpaperImageInput.click();
            });
            wallpaperImageInput.addEventListener('change', (e) => {
                this.handleWallpaperUpload(e);
            });
        }

        const removeWallpaperBtn = document.getElementById('removeWallpaperBtn');
        if (removeWallpaperBtn) {
            removeWallpaperBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.activeConfig.customWallpaperData = null;
                this.activeConfig.wallpaper = null;
                this.activeConfig.type = 'preset';
                this.applyThemeConfig(this.activeConfig, false);
                this.syncActiveUI();
                removeWallpaperBtn.classList.add('d-none');
            });
        }
    }

    switchTab(tabKey) {
        // Map tabs
        const tabAliases = {
            'presets': 'presets',
            'wallpapers': 'wallpapers',
            'background': 'wallpapers',
            'overlay': 'overlay',
            'bubbles': 'bubbles'
        };
        const activeTab = tabAliases[tabKey] || 'presets';

        // Update Nav buttons
        document.querySelectorAll('#chatThemeNavPills .nav-link, .theme-tabs .theme-tab').forEach(btn => {
            const bKey = btn.dataset.themeTab || btn.dataset.tab;
            if (tabAliases[bKey] === activeTab) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update Tab Panes
        document.querySelectorAll('.theme-panel-tab-pane, .theme-tab-content').forEach(pane => {
            pane.classList.add('d-none');
            pane.classList.remove('active');
        });

        const targetPane = document.getElementById(`pane-${activeTab}`) || document.getElementById(`${activeTab}-tab`);
        if (targetPane) {
            targetPane.classList.remove('d-none');
            targetPane.classList.add('active');
        }
    }

    showThemePanel() {
        const overlay = document.getElementById('overlay');
        if (overlay) overlay.classList.remove('show');
        document.querySelectorAll('.overlay.show, .theme-modal-backdrop, .modal-backdrop, .dropdown-backdrop').forEach(el => {
            el.classList.remove('show');
            if (el.classList.contains('theme-modal-backdrop') || el.classList.contains('modal-backdrop') || el.classList.contains('dropdown-backdrop')) {
                el.remove();
            }
        });

        const panel = document.getElementById('chatThemePanel');
        if (panel) {
            panel.classList.remove('d-none');
            this.syncActiveUI();
            this.updateLivePreview();
        } else {
            // Legacy modal fallback
            const modal = document.getElementById('themeModal');
            if (modal) {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
    }

    hideThemePanel() {
        const panel = document.getElementById('chatThemePanel');
        if (panel) {
            panel.classList.add('d-none');
        }
        const modal = document.getElementById('themeModal');
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
        // Ensure any backdrop/overlay from theme selection is closed
        const overlay = document.getElementById('overlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
        document.querySelectorAll('.overlay.show, .theme-modal-backdrop, .modal-backdrop, .dropdown-backdrop, .dropdown-menu.show').forEach(el => {
            el.classList.remove('show');
            if (el.classList.contains('theme-modal-backdrop') || el.classList.contains('modal-backdrop') || el.classList.contains('dropdown-backdrop')) {
                el.remove();
            }
        });
    }

    // Alias for legacy calls
    showThemeModal() {
        this.showThemePanel();
    }
    hideThemeModal() {
        this.hideThemePanel();
    }

    syncActiveUI() {
        // Curated presets active check
        document.querySelectorAll('.preset-option').forEach(opt => {
            const p = opt.dataset.preset;
            const currentP = this.activeConfig.preset;
            const isMatch = (p === currentP) ||
                ((p === 'ocean-wave' || p === 'ocean-breeze') && (currentP === 'ocean-wave' || currentP === 'ocean-breeze' || currentP === 'default'));
            if (this.activeConfig.type === 'preset' && isMatch) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });

        // Wallpaper active check
        document.querySelectorAll('.bg-option').forEach(opt => {
            const wp = opt.dataset.wallpaper || opt.dataset.theme;
            if (this.activeConfig.type === 'wallpaper' && wp === this.activeConfig.wallpaper) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });

        // Overlay slider & controls
        const overlayEnabled = document.getElementById('overlayEnabled');
        if (overlayEnabled) overlayEnabled.checked = this.activeConfig.overlayEnabled;

        const overlayOpacitySlider = document.getElementById('overlayOpacitySlider');
        const overlayOpacityValue = document.getElementById('overlayOpacityValue');
        const curOp = (this.activeConfig.overlayOpacity !== undefined && this.activeConfig.overlayOpacity !== null)
            ? Number(this.activeConfig.overlayOpacity)
            : 30;
        if (overlayOpacitySlider) overlayOpacitySlider.value = curOp;
        if (overlayOpacityValue) overlayOpacityValue.textContent = curOp + '%';

        // Sync pills active state
        document.querySelectorAll('.preset-opacity-btn, .opacity-presets .preset-btn').forEach(b => {
            b.classList.toggle('active', Number(b.dataset.opacity) === curOp);
        });

        const overlayColorPicker = document.getElementById('overlayColorPicker');
        const overlayColorHex = document.getElementById('overlayColorHex');
        if (overlayColorPicker) overlayColorPicker.value = this.activeConfig.overlayColor;
        if (overlayColorHex) overlayColorHex.textContent = this.activeConfig.overlayColor;

        // Custom Wallpaper Remove Button visibility
        const removeWallpaperBtn = document.getElementById('removeWallpaperBtn');
        if (removeWallpaperBtn) {
            if (this.activeConfig.customWallpaperData) {
                removeWallpaperBtn.classList.remove('d-none');
            } else {
                removeWallpaperBtn.classList.add('d-none');
            }
        }

        // Bubbles style
        document.querySelectorAll('.bubble-style-card, .bubble-option').forEach(card => {
            const style = card.dataset.bubbleStyle || card.dataset.bubble;
            if (style === (this.activeConfig.bubbleStyle || 'default')) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });

        this.updateLivePreview();
    }

    updateLivePreview() {
        const previewCard = document.getElementById('themeLivePreviewCard');
        if (!previewCard) return;

        const overlayLayer = document.getElementById('themePreviewOverlay');
        const receivedBubble = document.getElementById('previewReceivedBubble');
        const sentBubble = document.getElementById('previewSentBubble');
        const previewComposer = document.getElementById('themePreviewComposer');

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || document.documentElement.getAttribute('data-bs-theme') === 'dark';

        // 1. Wallpaper / Background in preview
        if (this.activeConfig.type === 'wallpaper') {
            if (this.activeConfig.customWallpaperData) {
                previewCard.style.background = `url(${this.activeConfig.customWallpaperData})`;
                previewCard.style.backgroundSize = 'cover';
                previewCard.style.backgroundPosition = 'center';
            } else if (this.activeConfig.wallpaper) {
                const gradientMap = {
                    'light': '#efeae2',
                    'dark': '#0b141a',
                    'wallpaper-1': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'wallpaper-2': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                    'wallpaper-3': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                    'wallpaper-4': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                    'wallpaper-5': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                    'wallpaper-6': 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
                };
                previewCard.style.background = gradientMap[this.activeConfig.wallpaper] || '#efeae2';
            }
        } else {
            // Curated preset background
            const presetBgMap = {
                'default': isDark ? '#0c233c' : '#e0f2fe',
                'ocean-wave': isDark ? '#0c233c' : '#e0f2fe',
                'ocean-breeze': isDark ? '#0c233c' : '#e0f2fe',
                'classic': isDark ? '#0b141a' : '#efeae2',
                'sand-gradient': isDark ? '#26180e' : '#fef3c7',
                'swahili-wave': isDark ? '#0b2b26' : '#ccfbf1',
                'midnight-coast': isDark ? '#111a38' : '#e0e7ff',
                'forest-glow': isDark ? '#0d281a' : '#dcfce7',
                'pwani-neon': isDark ? '#1d1130' : '#f5f3ff'
            };
            previewCard.style.background = presetBgMap[this.activeConfig.preset || 'ocean-wave'] || '#e0f2fe';
        }

        // 2. Overlay in preview
        if (overlayLayer) {
            const isEnabled = this.activeConfig.overlayEnabled !== false;
            const rawOp = (this.activeConfig.overlayOpacity !== undefined && this.activeConfig.overlayOpacity !== null)
                ? Number(this.activeConfig.overlayOpacity)
                : 30;
            const opacity = isEnabled ? (rawOp / 100) : 0;
            overlayLayer.style.backgroundColor = this.activeConfig.overlayColor || '#ffffff';
            overlayLayer.style.opacity = opacity;
        }

        // 3. Bubbles & Corner Radius in preview
        let bubbleRadius = '';
        if (this.activeConfig.bubbleStyle === 'rounded') {
            bubbleRadius = '20px';
        } else if (this.activeConfig.bubbleStyle === 'square') {
            bubbleRadius = '4px';
        }

        if (sentBubble) {
            sentBubble.style.borderRadius = bubbleRadius;
            if (this.activeConfig.bubbleSentColor) {
                sentBubble.style.backgroundColor = this.activeConfig.bubbleSentColor;
                sentBubble.style.color = this.getContrastColor(this.activeConfig.bubbleSentColor);
            } else {
                sentBubble.style.backgroundColor = '';
                sentBubble.style.color = '';
            }
        }
        if (receivedBubble) {
            receivedBubble.style.borderRadius = bubbleRadius;
            if (this.activeConfig.bubbleReceivedColor) {
                receivedBubble.style.backgroundColor = this.activeConfig.bubbleReceivedColor;
                receivedBubble.style.color = this.getContrastColor(this.activeConfig.bubbleReceivedColor);
            } else {
                receivedBubble.style.backgroundColor = '';
                receivedBubble.style.color = '';
            }
        }

        // 4. Composer mock contrast in preview
        if (previewComposer) {
            const composerBg = isDark ? '#202c33' : '#ffffff';
            previewComposer.style.backgroundColor = composerBg;
            previewComposer.style.color = isDark ? '#f8fafc' : '#0f172a';
        }
    }

    setOverlayOpacity(op, updateSlider = true) {
        const numOp = Math.max(0, Math.min(80, Number(op)));
        this.activeConfig.overlayOpacity = numOp;
        this.activeConfig.overlayEnabled = numOp > 0;

        const slider = document.getElementById('overlayOpacitySlider');
        const valBadge = document.getElementById('overlayOpacityValue');
        const sw = document.getElementById('overlayEnabled');

        if (slider && updateSlider) slider.value = numOp;
        if (valBadge) valBadge.textContent = numOp + '%';
        if (sw) sw.checked = (numOp > 0);

        document.querySelectorAll('.preset-opacity-btn, .opacity-presets .preset-btn').forEach(b => {
            b.classList.toggle('active', Number(b.dataset.opacity) === numOp);
        });

        this.applyOverlay();
        this.updateLivePreview();
    }

    setOverlayEnabled(enabled) {
        this.activeConfig.overlayEnabled = Boolean(enabled);
        const sw = document.getElementById('overlayEnabled');
        if (sw) sw.checked = this.activeConfig.overlayEnabled;

        const currentOp = this.activeConfig.overlayEnabled
            ? (Number(this.activeConfig.overlayOpacity) || 30)
            : 0;

        const slider = document.getElementById('overlayOpacitySlider');
        const valBadge = document.getElementById('overlayOpacityValue');
        if (slider) slider.value = currentOp;
        if (valBadge) valBadge.textContent = currentOp + '%';

        document.querySelectorAll('.preset-opacity-btn, .opacity-presets .preset-btn').forEach(b => {
            b.classList.toggle('active', Number(b.dataset.opacity) === currentOp);
        });

        this.applyOverlay();
        this.updateLivePreview();
    }

    applyOverlay() {
        const chatTarget = this.getChatTarget();
        const whatsappLayout = document.getElementById('whatsappLayout');
        const isPreset = this.activeConfig.type === 'preset' && !this.activeConfig.customOverlayActive;
        const isEnabled = !isPreset && this.activeConfig.overlayEnabled !== false;
        const rawOp = (isEnabled && this.activeConfig.overlayOpacity !== undefined && this.activeConfig.overlayOpacity !== null)
            ? Number(this.activeConfig.overlayOpacity)
            : 0;
        const opacity = isEnabled ? (rawOp / 100) : 0;
        const color = this.activeConfig.overlayColor || '#ffffff';

        if (chatTarget) {
            chatTarget.style.setProperty('--chat-overlay-color', color);
            chatTarget.style.setProperty('--chat-overlay-opacity', opacity);
        }
        if (whatsappLayout) {
            whatsappLayout.style.setProperty('--chat-overlay-color', color);
            whatsappLayout.style.setProperty('--chat-overlay-opacity', opacity);
        }
        document.documentElement.style.setProperty('--chat-overlay-color', color);
        document.documentElement.style.setProperty('--chat-overlay-opacity', opacity);
        if (document.body) {
            document.body.style.setProperty('--chat-overlay-color', color);
            document.body.style.setProperty('--chat-overlay-opacity', opacity);
        }

        const overlayLayer = document.getElementById('themePreviewOverlay');
        if (overlayLayer) {
            overlayLayer.style.backgroundColor = color;
            overlayLayer.style.opacity = opacity;
        }
    }

    applyBubbleStyle(style) {
        const messagesArea = document.getElementById('messagesContainer');
        if (!messagesArea) return;

        messagesArea.classList.remove('bubble-style-rounded', 'bubble-style-square');
        if (style === 'rounded') {
            messagesArea.classList.add('bubble-style-rounded');
            document.querySelectorAll('.message-bubble').forEach(b => b.style.borderRadius = '24px');
        } else if (style === 'square') {
            messagesArea.classList.add('bubble-style-square');
            document.querySelectorAll('.message-bubble').forEach(b => b.style.borderRadius = '4px');
        } else {
            document.querySelectorAll('.message-bubble').forEach(b => b.style.borderRadius = '');
        }
    }

    applyBubbleColors() {
        const chatTarget = this.getChatTarget();
        if (!chatTarget) return;

        if (this.activeConfig.bubbleSentColor) {
            chatTarget.style.setProperty('--chat-bg-sent', this.activeConfig.bubbleSentColor);
            chatTarget.style.setProperty('--chat-text-sent', this.getContrastColor(this.activeConfig.bubbleSentColor));
        } else {
            chatTarget.style.removeProperty('--chat-bg-sent');
            chatTarget.style.removeProperty('--chat-text-sent');
        }

        if (this.activeConfig.bubbleReceivedColor) {
            chatTarget.style.setProperty('--chat-bg-received', this.activeConfig.bubbleReceivedColor);
            chatTarget.style.setProperty('--chat-text-received', this.getContrastColor(this.activeConfig.bubbleReceivedColor));
        } else {
            chatTarget.style.removeProperty('--chat-bg-received');
            chatTarget.style.removeProperty('--chat-text-received');
        }
    }

    handleWallpaperUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select an image file', 'error');
            return;
        }

        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showNotification('File size must be less than 5MB', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.activeConfig.type = 'wallpaper';
            this.activeConfig.customWallpaperData = e.target.result;
            this.activeConfig.wallpaper = 'custom';
            this.applyThemeConfig(this.activeConfig, false);
            this.syncActiveUI();
            this.showNotification('Custom wallpaper loaded!');
        };
        reader.onerror = () => {
            this.showNotification('Failed to read image file', 'error');
        };
        reader.readAsDataURL(file);
    }

    applyThemeConfig(config, notify = false) {
        if (!config) return;
        this.activeConfig = { ...this.activeConfig, ...config };

        const chatTarget = this.getChatTarget();
        const messagesArea = document.getElementById('messagesContainer');
        const whatsappLayout = document.getElementById('whatsappLayout');

        // Always ensure messagesArea background is transparent so chatMainArea wallpaper/color shines cleanly
        if (messagesArea) {
            messagesArea.style.background = 'transparent';
            messagesArea.style.backgroundColor = 'transparent';
            messagesArea.style.backgroundImage = 'none';
        }

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || document.documentElement.getAttribute('data-bs-theme') === 'dark';

        if (config.type === 'wallpaper') {
            // Apply custom gradient or image wallpaper via --chat-wallpaper so CSS !important respects it
            let wallpaperCss = '';
            if (config.customWallpaperData) {
                wallpaperCss = `url(${config.customWallpaperData})`;
            } else if (config.wallpaper) {
                const gradientMap = {
                    'light': '#efeae2',
                    'dark': '#0b141a',
                    'wallpaper-1': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'wallpaper-2': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                    'wallpaper-3': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                    'wallpaper-4': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                    'wallpaper-5': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                    'wallpaper-6': 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
                };
                wallpaperCss = gradientMap[config.wallpaper] || '#efeae2';
            }

            if (chatTarget) {
                chatTarget.style.setProperty('--chat-wallpaper', wallpaperCss);
            }
            if (whatsappLayout) {
                whatsappLayout.style.setProperty('--chat-wallpaper', wallpaperCss);
            }

            // Guaranteed Solid Composer & Contrast
            this.ensureComposerContrast(isDark ? '#202c33' : '#ffffff');
        } else {
            // Curated Atmosphere Preset
            const preset = config.preset || 'default';
            if (!config.customOverlayActive) {
                this.activeConfig.overlayOpacity = 0;
                this.activeConfig.overlayEnabled = false;
            }
            if (chatTarget) {
                chatTarget.style.removeProperty('--chat-wallpaper');
                chatTarget.setAttribute('data-chat-theme', preset);
            }
            if (whatsappLayout) {
                whatsappLayout.style.removeProperty('--chat-wallpaper');
                whatsappLayout.setAttribute('data-chat-theme', preset);
            }
            document.documentElement.setAttribute('data-chat-theme', preset);

            // Compute contrast for the preset's composer
            const composerBg = isDark ? '#202c33' : '#ffffff';
            this.ensureComposerContrast(composerBg);
        }

        // Apply Overlay
        this.applyOverlay();

        // Apply Bubble Style & Colors
        if (config.bubbleStyle) this.applyBubbleStyle(config.bubbleStyle);
        this.applyBubbleColors();

        if (notify) {
            const displayName = config.type === 'wallpaper' ? 'Wallpaper' : this.getPresetDisplayName(config.preset);
            this.showNotification(`Theme set to ${displayName}!`);
        }
    }

    // Alias for applying curated preset directly
    applyChatPreset(preset, notify = true) {
        this.activeConfig.type = 'preset';
        this.activeConfig.preset = preset;
        this.activeConfig.wallpaper = null;
        this.activeConfig.customWallpaperData = null;
        this.applyThemeConfig(this.activeConfig, notify);
        this.syncActiveUI();
    }

    ensureComposerContrast(composerBgHex) {
        const chatTarget = this.getChatTarget();
        if (!chatTarget) return;

        const textColor = this.getContrastColor(composerBgHex);
        const placeholderColor = textColor === '#0f172a' ? '#64748b' : '#94a3b8';

        chatTarget.style.setProperty('--chat-composer-bg', composerBgHex);
        chatTarget.style.setProperty('--chat-composer-text', textColor);
        chatTarget.style.setProperty('--chat-composer-placeholder', placeholderColor);
        chatTarget.style.setProperty('--chat-composer-btn-color', placeholderColor);

        // Also set on root element so floating composer inherits seamlessly
        document.documentElement.style.setProperty('--chat-composer-text', textColor);
        document.documentElement.style.setProperty('--chat-composer-placeholder', placeholderColor);
    }

    getContrastColor(hexOrRgb) {
        if (!hexOrRgb) return '#0f172a';
        let r = 255, g = 255, b = 255;
        if (hexOrRgb.startsWith('#')) {
            const hex = hexOrRgb.replace('#', '');
            if (hex.length === 3) {
                r = parseInt(hex[0] + hex[0], 16);
                g = parseInt(hex[1] + hex[1], 16);
                b = parseInt(hex[2] + hex[2], 16);
            } else if (hex.length >= 6) {
                r = parseInt(hex.substring(0, 2), 16);
                g = parseInt(hex.substring(2, 4), 16);
                b = parseInt(hex.substring(4, 6), 16);
            }
        } else if (hexOrRgb.startsWith('rgb')) {
            const parts = hexOrRgb.match(/\d+/g);
            if (parts && parts.length >= 3) {
                r = parseInt(parts[0], 10);
                g = parseInt(parts[1], 10);
                b = parseInt(parts[2], 10);
            }
        }
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.55 ? '#0f172a' : '#f8fafc';
    }

    getPresetDisplayName(preset) {
        const names = {
            'default': 'Ocean Wave',
            'ocean-wave': 'Ocean Wave',
            'ocean-breeze': 'Ocean Wave',
            'classic': 'Classic',
            'sand-gradient': 'Sand Gradient',
            'swahili-wave': 'Swahili Wave',
            'midnight-coast': 'Midnight Coast',
            'forest-glow': 'Forest Glow',
            'pwani-neon': 'Pwani Neon'
        };
        return names[preset] || preset;
    }

    loadCurrentTheme() {
        const conversationId = this.getConversationId();
        const defaultTheme = this.getDefaultTheme();

        let targetConfig = {
            type: 'preset',
            preset: defaultTheme,
            overlayEnabled: false,
            overlayOpacity: 0,
            overlayColor: '#ffffff',
            customOverlayActive: false
        };

        // Check if there is a chat-specific theme for this conversation
        if (conversationId) {
            const savedChatTheme = localStorage.getItem(`chat_theme_${conversationId}`);
            if (savedChatTheme) {
                try {
                    const parsed = JSON.parse(savedChatTheme);
                    targetConfig = { ...targetConfig, ...parsed };
                } catch (e) {
                    console.error('Failed to parse saved chat theme:', e);
                }
            }
        }

        this.applyThemeConfig(targetConfig, false);
        this.syncActiveUI();
    }

    saveTheme() {
        const conversationId = this.getConversationId();
        const applyToAll = document.getElementById('themeApplyToAllChats')?.checked || false;

        const themeDataToSave = {
            type: this.activeConfig.type,
            preset: this.activeConfig.preset,
            wallpaper: this.activeConfig.wallpaper,
            customWallpaperData: this.activeConfig.customWallpaperData,
            overlayEnabled: this.activeConfig.overlayEnabled,
            overlayOpacity: this.activeConfig.overlayOpacity,
            overlayColor: this.activeConfig.overlayColor,
            customOverlayActive: this.activeConfig.customOverlayActive,
            bubbleStyle: this.activeConfig.bubbleStyle,
            bubbleSentColor: this.activeConfig.bubbleSentColor,
            bubbleReceivedColor: this.activeConfig.bubbleReceivedColor
        };

        if (applyToAll) {
            const defaultThemeName = this.activeConfig.type === 'preset' ? this.activeConfig.preset : 'default';
            localStorage.setItem('default_chat_theme', defaultThemeName);
            localStorage.setItem('chat_theme', defaultThemeName);

            // 2. Persist to backend user preference
            this.saveChatThemePreference(defaultThemeName);

            // 3. Clear conversation-specific override so this chat inherits the new global default
            if (conversationId) {
                localStorage.removeItem(`chat_theme_${conversationId}`);
            }

            this.showNotification('Default theme applied to all chats!');
        } else {
            // Per-chat persistence: sticks strictly to this conversation!
            if (conversationId) {
                localStorage.setItem(`chat_theme_${conversationId}`, JSON.stringify(themeDataToSave));
                this.showNotification('Theme saved for this chat!');
            } else {
                this.showNotification('Theme applied!');
            }
        }

        this.hideThemePanel();
    }

    resetThemeToDefault() {
        const conversationId = this.getConversationId();
        const defaultTheme = this.getDefaultTheme();

        if (conversationId) {
            localStorage.removeItem(`chat_theme_${conversationId}`);
        }

        this.activeConfig = {
            type: 'preset',
            preset: defaultTheme,
            wallpaper: null,
            customWallpaperData: null,
            overlayEnabled: false,
            overlayOpacity: 0,
            overlayColor: '#ffffff',
            customOverlayActive: false,
            bubbleStyle: 'default',
            bubbleSentColor: '',
            bubbleReceivedColor: ''
        };

        this.applyThemeConfig(this.activeConfig, false);
        this.syncActiveUI();
        this.showNotification('Reset to default theme for this chat!');
        this.hideThemePanel();
    }

    saveChatThemePreference(preset) {
        const getCSRFToken = () => {
            const tokenInput = document.querySelector('[name="csrfmiddlewaretoken"]');
            if (tokenInput && tokenInput.value) return tokenInput.value;
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag && metaTag.content) return metaTag.content;
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, val] = cookie.trim().split('=');
                if (name === 'csrftoken') return decodeURIComponent(val);
            }
            return '';
        };

        fetch('/users/api/users/update_preferences/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ chat_theme_preference: preset })
        }).catch(err => console.error('Error saving chat theme preference:', err));
    }

    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 24px;
            right: 24px;
            padding: 12px 22px;
            background: ${type === 'error' ? '#ef4444' : 'var(--brand, #008489)'};
            color: #ffffff;
            border-radius: 24px;
            z-index: 10001;
            font-weight: 600;
            font-size: 0.9rem;
            box-shadow: 0 6px 18px rgba(0,0,0,0.22);
            animation: themeSlideIn 0.25s ease;
            pointer-events: none;
        `;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.style.animation = 'themeSlideOut 0.25s ease forwards';
            setTimeout(() => notification.remove(), 250);
        }, 2200);
    }
}

// Global initialization
function initChatThemeHandler() {
    if (!window.chatThemeHandler) {
        window.chatThemeHandler = new ChatThemeHandler();
    } else {
        window.chatThemeHandler.reinit();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatThemeHandler);
} else {
    initChatThemeHandler();
}

document.addEventListener('htmx:afterSwap', () => {
    if (window.chatThemeHandler) {
        window.chatThemeHandler.reinit();
    }
});

// Animation Keyframes
const themeStyleTag = document.createElement('style');
themeStyleTag.textContent = `
    @keyframes themeSlideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes themeSlideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(themeStyleTag);
