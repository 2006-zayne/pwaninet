/**
 * ThemeService - Theme management (merged service + UI)
 * Service layer: No DOM manipulation, pure logic
 * UI layer: DOM manipulation for theme selector
 */

import { EVENTS, DEFAULT_THEME } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';
import { store } from '../../core/store.js';
import { getCSRFToken } from '../../shared/utils.js';

export class ThemeService {
  constructor() {
    this.currentConversationId = null;
    this.currentTheme = null;
    this.currentThemeMode = 'light';
    this.modal = null;
  }

  /**
   * Initialize theme service
   */
  init() {
    this.modal = document.getElementById('themeSelectorModal');
    this.setupEventListeners();
    this.setupDOMListeners();
    this.detectThemeMode();
    this.loadThemeForCurrentConversation();
  }

  /**
   * Setup event listeners (service layer)
   */
  setupEventListeners() {
    // Listen for theme toggle
    eventBus.on(EVENTS.THEME_TOGGLE, () => {
      this.showSelector();
    });

    // Listen for theme mode changes
    const observer = new MutationObserver(() => {
      this.detectThemeMode();
      this.applyTheme();
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });

    // Listen for theme save request
    eventBus.on(EVENTS.THEME_SAVE, (themeData) => {
      this.saveTheme(themeData);
    });

    // Listen for theme reset request
    eventBus.on(EVENTS.THEME_RESET, () => {
      this.resetTheme();
    });

    // Listen for theme tab switch
    eventBus.on(EVENTS.THEME_TAB_SWITCH, (tab) => {
      this.switchTab(tab);
    });
  }

  /**
   * Setup DOM event listeners (UI layer)
   */
  setupDOMListeners() {
    // Close button
    document.getElementById('themeSelectorClose')?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.THEME_RESET);
    });

    // Cancel button
    document.getElementById('themeCancelBtn')?.addEventListener('click', () => {
      this.hideSelector();
    });

    // Save button
    document.getElementById('themeSaveBtn')?.addEventListener('click', () => {
      this.collectAndSave();
    });

    // Reset button
    document.getElementById('themeResetBtn')?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.THEME_RESET);
    });

    // Theme tabs
    document.querySelectorAll('.theme-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        this.eventBus.emit(EVENTS.THEME_TAB_SWITCH, e.target.dataset.themeType);
      });
    });

    // Color inputs
    this.setupColorInputs();

    // Sliders
    this.setupSliders();

    // Image uploads
    this.setupImageUploads();
  }

  /**
   * Setup color inputs
   */
  setupColorInputs() {
    const colorPairs = [
      ['lightColor', 'lightColorText'],
      ['darkColor', 'darkColorText'],
      ['lightGradientStart', 'lightGradientStartText'],
      ['lightGradientEnd', 'lightGradientEndText'],
      ['darkGradientStart', 'darkGradientStartText'],
      ['darkGradientEnd', 'darkGradientEndText'],
      ['lightOverlayColor', 'lightOverlayColorText'],
      ['darkOverlayColor', 'darkOverlayColorText']
    ];

    colorPairs.forEach(([colorId, textId]) => {
      this.linkColorInputs(colorId, textId);
    });
  }

  /**
   * Link color inputs
   * @param {string} colorInputId - Color input ID
   * @param {string} textInputId - Text input ID
   */
  linkColorInputs(colorInputId, textInputId) {
    const colorInput = document.getElementById(colorInputId);
    const textInput = document.getElementById(textInputId);

    if (colorInput && textInput) {
      colorInput.addEventListener('input', (e) => {
        textInput.value = e.target.value;
      });

      textInput.addEventListener('input', (e) => {
        if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
          colorInput.value = e.target.value;
        }
      });
    }
  }

  /**
   * Setup sliders
   */
  setupSliders() {
    const angleSlider = document.getElementById('gradientAngle');
    if (angleSlider) {
      angleSlider.addEventListener('input', (e) => {
        document.getElementById('angleValue').textContent = e.target.value;
      });
    }

    const opacitySlider = document.getElementById('overlayOpacity');
    if (opacitySlider) {
      opacitySlider.addEventListener('input', (e) => {
        document.getElementById('opacityValue').textContent = e.target.value;
      });
    }
  }

  /**
   * Setup image uploads
   */
  setupImageUploads() {
    const lightUpload = document.getElementById('lightImageUpload');
    const darkUpload = document.getElementById('darkImageUpload');

    if (lightUpload) {
      lightUpload.addEventListener('click', () => {
        document.getElementById('lightImageInput').click();
      });

      document.getElementById('lightImageInput').addEventListener('change', (e) => {
        this.handleImageUpload(e, 'light');
      });
    }

    if (darkUpload) {
      darkUpload.addEventListener('click', () => {
        document.getElementById('darkImageInput').click();
      });

      document.getElementById('darkImageInput').addEventListener('change', (e) => {
        this.handleImageUpload(e, 'dark');
      });
    }
  }

  /**
   * Handle image upload
   * @param {Event} event - File input event
   * @param {string} mode - Light or dark mode
   */
  handleImageUpload(event, mode) {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const previewId = mode === 'light' ? 'lightImagePreview' : 'darkImagePreview';
        const preview = document.getElementById(previewId);
        if (preview) {
          preview.style.backgroundImage = `url(${e.target.result})`;
          preview.parentElement.querySelector('.upload-placeholder').style.display = 'none';
        }
      };
      reader.readAsDataURL(file);
    }
  }

  /**
   * Detect theme mode
   */
  detectThemeMode() {
    this.currentThemeMode = document.documentElement.getAttribute('data-theme') || 'light';
    store.setThemeMode(this.currentThemeMode);
  }

  /**
   * Get current conversation ID
   * @returns {number|null} Conversation ID
   */
  getCurrentConversationId() {
    const pathMatch = window.location.pathname.match(/\/conversation\/(\d+)\//);
    if (pathMatch) return parseInt(pathMatch[1]);

    const chatContainer = document.querySelector('.chat-header');
    if (chatContainer) {
      return parseInt(chatContainer.dataset.conversationId);
    }

    return null;
  }

  /**
   * Load theme for current conversation
   */
  async loadThemeForCurrentConversation() {
    this.currentConversationId = this.getCurrentConversationId();
    if (!this.currentConversationId) return;

    try {
      const response = await fetch(
        `/messaging/v1/themes/by_conversation/?conversation_id=${this.currentConversationId}`,
        {
          headers: {
            'X-CSRFToken': getCSRFToken()
          }
        }
      );

      if (response.ok) {
        this.currentTheme = await response.json();
        this.applyTheme();
        this.populateForm(this.currentTheme);
      }
    } catch (error) {
      console.error('Failed to load theme:', error);
    }
  }

  /**
   * Apply theme to CSS variables
   */
  applyTheme() {
    if (!this.currentTheme) {
      this.applyDefaultTheme();
      return;
    }

    const cssVars = this.currentThemeMode === 'light' 
      ? this.currentTheme.css_variables_light 
      : this.currentTheme.css_variables_dark;

    const overlayVars = this.currentThemeMode === 'light' 
      ? this.currentTheme.overlay_light 
      : this.currentTheme.overlay_dark;

    if (cssVars) {
      Object.entries(cssVars).forEach(([key, value]) => {
        document.documentElement.style.setProperty(key, value);
      });
    }

    if (overlayVars) {
      Object.entries(overlayVars).forEach(([key, value]) => {
        document.documentElement.style.setProperty(key, value);
      });
    }

    eventBus.emit(EVENTS.THEME_APPLY, this.currentTheme);
  }

  /**
   * Apply default theme
   */
  applyDefaultTheme() {
    const defaults = DEFAULT_THEME[this.currentThemeMode];
    Object.entries(defaults).forEach(([key, value]) => {
      document.documentElement.style.setProperty(key, value);
    });

    // Remove custom background from messages area
    const messagesArea = document.querySelector('.messages-area');
    if (messagesArea) {
      messagesArea.style.background = '';
      messagesArea.style.backgroundImage = '';
      const overlay = messagesArea.querySelector('.chat-overlay');
      if (overlay) overlay.remove();
    }

    eventBus.emit(EVENTS.THEME_APPLY, null);
  }

  /**
   * Save theme
   * @param {Object} themeData - Theme data to save
   */
  async saveTheme(themeData) {
    if (!this.currentConversationId) return;

    try {
      let response;
      if (this.currentTheme && this.currentTheme.id) {
        // Update existing theme
        response = await fetch(`/api/messaging/v1/themes/${this.currentTheme.id}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
          },
          body: JSON.stringify(themeData)
        });
      } else {
        // Create new theme
        response = await fetch('/api/messaging/v1/themes/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
          },
          body: JSON.stringify({
            ...themeData,
            conversation: this.currentConversationId
          })
        });
      }

      if (response.ok) {
        this.currentTheme = await response.json();
        this.applyTheme();
        this.hideSelector();
      } else {
        const error = await response.json();
        this.showError(error.detail || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to save theme:', error);
      this.showError('Failed to save theme');
    }
  }

  /**
   * Reset theme
   */
  async resetTheme() {
    if (!this.currentConversationId) return;

    try {
      if (this.currentTheme && this.currentTheme.id) {
        await fetch(`/api/messaging/v1/themes/${this.currentTheme.id}/`, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': getCSRFToken()
          }
        });
      }

      this.currentTheme = null;
      this.applyDefaultTheme();
      this.hideSelector();
    } catch (error) {
      console.error('Failed to reset theme:', error);
      this.showError('Failed to reset theme');
    }
  }

  /**
   * Show theme selector
   */
  showSelector() {
    if (this.modal) {
      this.modal.style.display = 'flex';
      if (this.currentTheme) {
        this.populateForm(this.currentTheme);
      }
    }
  }

  /**
   * Hide theme selector
   */
  hideSelector() {
    if (this.modal) {
      this.modal.style.display = 'none';
    }
  }

  /**
   * Populate form with theme data
   * @param {Object} theme - Theme object
   */
  populateForm(theme) {
    if (!theme) return;

    // Set theme type
    this.switchTab(theme.theme_type || 'solid');

    // Set solid colors
    if (theme.light_color) {
      document.getElementById('lightColor').value = theme.light_color;
      document.getElementById('lightColorText').value = theme.light_color;
    }
    if (theme.dark_color) {
      document.getElementById('darkColor').value = theme.dark_color;
      document.getElementById('darkColorText').value = theme.dark_color;
    }

    // Set gradient colors
    if (theme.light_gradient_start) {
      document.getElementById('lightGradientStart').value = theme.light_gradient_start;
      document.getElementById('lightGradientStartText').value = theme.light_gradient_start;
    }
    if (theme.light_gradient_end) {
      document.getElementById('lightGradientEnd').value = theme.light_gradient_end;
      document.getElementById('lightGradientEndText').value = theme.light_gradient_end;
    }
    if (theme.dark_gradient_start) {
      document.getElementById('darkGradientStart').value = theme.dark_gradient_start;
      document.getElementById('darkGradientStartText').value = theme.dark_gradient_start;
    }
    if (theme.dark_gradient_end) {
      document.getElementById('darkGradientEnd').value = theme.dark_gradient_end;
      document.getElementById('darkGradientEndText').value = theme.dark_gradient_end;
    }

    // Set gradient angle
    if (theme.gradient_angle) {
      document.getElementById('gradientAngle').value = theme.gradient_angle;
      document.getElementById('angleValue').textContent = theme.gradient_angle;
    }

    // Set overlay settings
    if (theme.overlay_opacity !== undefined) {
      document.getElementById('overlayOpacity').value = theme.overlay_opacity * 100;
      document.getElementById('opacityValue').textContent = Math.round(theme.overlay_opacity * 100);
    }
    if (theme.light_overlay_color) {
      document.getElementById('lightOverlayColor').value = theme.light_overlay_color;
      document.getElementById('lightOverlayColorText').value = theme.light_overlay_color;
    }
    if (theme.dark_overlay_color) {
      document.getElementById('darkOverlayColor').value = theme.dark_overlay_color;
      document.getElementById('darkOverlayColorText').value = theme.dark_overlay_color;
    }
  }

  /**
   * Switch tab
   * @param {string} themeType - Theme type
   */
  switchTab(themeType) {
    document.querySelectorAll('.theme-tab').forEach(tab => {
      tab.classList.remove('active');
    });
    document.querySelector(`[data-theme-type="${themeType}"]`)?.classList.add('active');

    document.querySelectorAll('.theme-panel').forEach(panel => {
      panel.classList.remove('active');
    });
    document.getElementById(`${themeType}Panel`)?.classList.add('active');
  }

  /**
   * Collect form data and save
   */
  collectAndSave() {
    const themeType = document.querySelector('.theme-tab.active')?.dataset.themeType || 'solid';
    const formData = {
      theme_type: themeType,
      overlay_opacity: parseFloat(document.getElementById('overlayOpacity').value) / 100,
      light_overlay_color: document.getElementById('lightOverlayColor').value,
      dark_overlay_color: document.getElementById('darkOverlayColor').value
    };

    if (themeType === 'solid') {
      formData.light_color = document.getElementById('lightColor').value;
      formData.dark_color = document.getElementById('darkColor').value;
    } else if (themeType === 'gradient') {
      formData.light_gradient_start = document.getElementById('lightGradientStart').value;
      formData.light_gradient_end = document.getElementById('lightGradientEnd').value;
      formData.dark_gradient_start = document.getElementById('darkGradientStart').value;
      formData.dark_gradient_end = document.getElementById('darkGradientEnd').value;
      formData.gradient_angle = parseInt(document.getElementById('gradientAngle').value);
    } else if (themeType === 'image') {
      formData.image_fit = document.getElementById('imageFit').value;
    }

    eventBus.emit(EVENTS.THEME_SAVE, formData);
  }

  /**
   * Show error
   * @param {string} error - Error message
   */
  showError(error) {
    console.error('Theme error:', error);
    // Could show a toast notification here
  }

  /**
   * Get current theme
   * @returns {Object|null} Current theme
   */
  getCurrentTheme() {
    return this.currentTheme;
  }

  /**
   * Get current theme mode
   * @returns {string} Theme mode
   */
  getThemeMode() {
    return this.currentThemeMode;
  }
}

// Create global instance
export const themeService = new ThemeService();
