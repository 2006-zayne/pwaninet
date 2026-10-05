/**
 * Universal Media Picker (Emoji, GIFs, Stickers)
 * Supports Mobile Bottom Sheet & Desktop/Tablet Floating Anchored Model
 * Integrates with KLIPY for GIFs & Stickers + Built-in offline packs
 */

(function(window, document) {
  'use strict';

  const BUILTIN_STICKERS = [
    { name: 'Fire', file: 'fire.svg' },
    { name: 'Heart Eyes', file: 'heart_eyes.svg' },
    { name: 'Party', file: 'party.svg' },
    { name: 'Laughing', file: 'laughing.svg' },
    { name: 'Thumbs Up', file: 'thumbs_up.svg' },
    { name: 'Rocket', file: 'rocket.svg' },
    { name: '100', file: '100.svg' },
    { name: 'Cool', file: 'cool.svg' },
    { name: 'Clap', file: 'clap.svg' },
    { name: 'Mind Blown', file: 'mind_blown.svg' },
    { name: 'Crying', file: 'crying.svg' },
    { name: 'Wow', file: 'wow.svg' },
    { name: 'Hug', file: 'hug.svg' },
    { name: 'Peace', file: 'peace.svg' },
    { name: 'Dance', file: 'dance.svg' },
    { name: 'Thinking', file: 'thinking.svg' }
  ];

  const QUICK_EMOJIS = ['😂', '❤️', '🔥', '👏', '😢', '😮', '🙏', '💯', '😍', '🎉'];

  const MediaPicker = {
    isOpen: false,
    activeTab: 'emojis',
    activeStickerSubtab: 'klipy',
    currentTargetInput: null,
    currentForm: null,
    currentTrigger: null,
    gifSearchTimeout: null,
    stickerSearchTimeout: null,
    gifPage: 1,
    stickerPage: 1,
    hasMoreGifs: true,
    hasMoreStickers: true,
    isLoadingGifs: false,
    isLoadingStickers: false,
    gifQuery: '',
    stickerQuery: '',
    gifRequestId: 0,
    stickerRequestId: 0,
    _myStickersCache: null,

    escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = String(text);
      return div.innerHTML;
    },

    init() {
      if (this._initialized) return;
      this._initialized = true;

      this.buildDOM();
      this.bindGlobalEvents();
      this.initEmojiPickerElement();
    },

    buildDOM() {
      if (document.getElementById('mediaPickerModal')) return;

      // Backdrop
      const backdrop = document.createElement('div');
      backdrop.id = 'mediaPickerBackdrop';
      backdrop.className = 'media-picker-backdrop';

      // Main Modal Container
      const modal = document.createElement('div');
      modal.id = 'mediaPickerModal';
      modal.className = 'media-picker-modal';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.setAttribute('aria-label', 'Emoji, GIF and Sticker Picker');

      modal.innerHTML = `
        <div class="media-picker-drag-handle" aria-hidden="true"></div>
        <div class="media-picker-header">
          <div class="media-picker-tabs" role="tablist">
            <button type="button" class="media-picker-tab-btn active" data-tab="emojis" role="tab" aria-selected="true">
              <i class="bi bi-emoji-smile"></i> Emoji
            </button>
            <button type="button" class="media-picker-tab-btn" data-tab="gifs" role="tab" aria-selected="false">
              <i class="bi bi-camera-video"></i> GIFs
            </button>
            <button type="button" class="media-picker-tab-btn" data-tab="stickers" role="tab" aria-selected="false">
              <i class="bi bi-stickies"></i> Stickers
            </button>
          </div>
          <button type="button" class="media-picker-close-btn" id="mediaPickerCloseBtn" aria-label="Close picker">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <!-- Quick Reactions Bar -->
        <div class="media-picker-quick-bar" id="mediaPickerQuickBar">
          ${QUICK_EMOJIS.map(em => `<button type="button" class="media-picker-quick-emoji" data-emoji="${em}" title="${em}">${em}</button>`).join('')}
        </div>

        <div class="media-picker-body">
          <!-- EMOJI PANEL -->
          <div class="media-picker-panel active" id="mediaPickerEmojiPanel" data-panel="emojis">
            <div class="media-picker-emoji-container" id="mediaPickerEmojiContainer">
              <!-- <emoji-picker> element injected here -->
            </div>
          </div>

          <!-- GIFS PANEL -->
          <div class="media-picker-panel" id="mediaPickerGifPanel" data-panel="gifs">
            <div class="media-picker-search-wrap">
              <i class="bi bi-search text-muted position-absolute" style="left: 24px;"></i>
              <input type="text" class="media-picker-search-input" id="mediaPickerGifSearch" placeholder="Search GIFs with KLIPY..." autocomplete="off">
              <button type="button" class="media-picker-search-clear" id="mediaPickerGifClear" title="Clear search"><i class="bi bi-x-circle-fill"></i></button>
            </div>
            <div class="media-picker-categories" id="mediaPickerGifCategories">
              <button type="button" class="media-picker-chip active" data-query="">🔥 Trending</button>
              <button type="button" class="media-picker-chip" data-query="lol">😂 LOL</button>
              <button type="button" class="media-picker-chip" data-query="love">❤️ Love</button>
              <button type="button" class="media-picker-chip" data-query="party">🎉 Party</button>
              <button type="button" class="media-picker-chip" data-query="clap">👏 Clap</button>
              <button type="button" class="media-picker-chip" data-query="cats">🐱 Cats</button>
              <button type="button" class="media-picker-chip" data-query="dance">💃 Dance</button>
              <button type="button" class="media-picker-chip" data-query="sad">😢 Sad</button>
              <button type="button" class="media-picker-chip" data-query="yes">👍 Yes</button>
              <button type="button" class="media-picker-chip" data-query="no">🤦 No</button>
              <button type="button" class="media-picker-chip" data-query="wow">😮 Wow</button>
            </div>
            <div class="media-picker-grid" id="mediaPickerGifGrid">
              <div class="media-picker-loading"><div class="spinner-border spinner-border-sm text-primary"></div><span>Loading GIFs...</span></div>
            </div>
            <div class="media-picker-footer">
              <span class="text-muted small">Powered by</span>
              <a href="https://klipy.com" target="_blank" rel="noopener" class="media-picker-klipy-brand">
                <img src="/static/images/klipy-logo.png" alt="KLIPY">
              </a>
            </div>
          </div>

          <!-- STICKERS PANEL -->
          <div class="media-picker-panel" id="mediaPickerStickerPanel" data-panel="stickers">
            <div class="media-picker-subtabs">
              <button type="button" class="media-picker-pill active" data-subtab="klipy">KLIPY Stickers</button>
              <button type="button" class="media-picker-pill" data-subtab="builtin">Built-in Pack</button>
              <button type="button" class="media-picker-pill" data-subtab="mine">My Stickers</button>
            </div>
            <div class="media-picker-search-wrap" id="mediaPickerStickerSearchWrap">
              <i class="bi bi-search text-muted position-absolute" style="left: 24px;"></i>
              <input type="text" class="media-picker-search-input" id="mediaPickerStickerSearch" placeholder="Search stickers with KLIPY..." autocomplete="off">
              <button type="button" class="media-picker-search-clear" id="mediaPickerStickerClear" title="Clear search"><i class="bi bi-x-circle-fill"></i></button>
            </div>
            <div class="media-picker-categories" id="mediaPickerStickerCategories">
              <button type="button" class="media-picker-chip active" data-query="">🔥 Trending</button>
              <button type="button" class="media-picker-chip" data-query="love">❤️ Love</button>
              <button type="button" class="media-picker-chip" data-query="cute">✨ Cute</button>
              <button type="button" class="media-picker-chip" data-query="funny">😂 Funny</button>
              <button type="button" class="media-picker-chip" data-query="party">🎉 Party</button>
              <button type="button" class="media-picker-chip" data-query="animals">🐱 Animals</button>
              <button type="button" class="media-picker-chip" data-query="anime">💥 Anime</button>
              <button type="button" class="media-picker-chip" data-query="cool">😎 Cool</button>
              <button type="button" class="media-picker-chip" data-query="mood">💬 Mood</button>
            </div>
            <div class="media-picker-grid stickers-grid" id="mediaPickerStickerGrid">
              <div class="media-picker-loading"><div class="spinner-border spinner-border-sm text-primary"></div><span>Loading stickers...</span></div>
            </div>
            <div class="media-picker-footer" id="mediaPickerStickerFooter">
              <span class="text-muted small">Powered by</span>
              <a href="https://klipy.com" target="_blank" rel="noopener" class="media-picker-klipy-brand">
                <img src="/static/images/klipy-logo.png" alt="KLIPY">
              </a>
            </div>
          </div>
        </div>

        <input type="file" id="mediaPickerCustomStickerInput" accept="image/*" style="display: none;">
      `;

      // Stop clicks inside picker modal from bubbling and dismissing parent modals
      modal.addEventListener('click', (e) => {
        e.stopPropagation();
      });

      document.body.appendChild(backdrop);
      document.body.appendChild(modal);

      this.backdropEl = backdrop;
      this.modalEl = modal;
    },

    initEmojiPickerElement() {
      const container = document.getElementById('mediaPickerEmojiContainer');
      if (!container) return;

      // Lazy load emoji-picker custom element module
      if (!window.customElements.get('emoji-picker')) {
        import('/static/vendor/emoji-picker/index.js')
          .then(() => {
            this.mountEmojiPickerTag(container);
          })
          .catch(err => {
            console.warn('[MediaPicker] Could not import local emoji-picker module, trying fallback:', err);
            // Fallback: create dynamic script
            const s = document.createElement('script');
            s.type = 'module';
            s.src = '/static/vendor/emoji-picker/index.js';
            s.onload = () => this.mountEmojiPickerTag(container);
            document.head.appendChild(s);
          });
      } else {
        this.mountEmojiPickerTag(container);
      }
    },

    mountEmojiPickerTag(container) {
      if (container.querySelector('emoji-picker')) return;

      const picker = document.createElement('emoji-picker');
      picker.setAttribute('data-source', '/static/vendor/emoji-picker/data/emojibase-en.json');
      
      // Inherit dark mode if active and observe theme changes
      const syncTheme = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        picker.classList.toggle('dark', isDark);
      };
      syncTheme();
      try {
        const observer = new MutationObserver(syncTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      } catch (_) {}

      picker.addEventListener('emoji-click', (e) => {
        if (e.stopPropagation) e.stopPropagation();
        const unicode = e.detail?.unicode || e.detail?.emoji?.unicode;
        if (unicode) {
          this.insertEmoji(unicode);
        }
      });

      picker.addEventListener('skin-tone-change', (e) => {
        // persists natively in indexdb
      });

      container.appendChild(picker);
    },

    bindGlobalEvents() {
      // 1. Delegated click for all emoji / media triggers across the page
      document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-media-picker], [data-action="emoji"], .composer-media-trigger, .comment-emoji-btn');
        if (trigger) {
          e.preventDefault();
          e.stopPropagation();
          this.toggle(trigger);
          return;
        }

        // Close when clicking outside of modal & not on trigger
        if (this.isOpen && this.modalEl && !this.modalEl.contains(e.target) && !e.target.closest('[data-media-picker], [data-action="emoji"], .composer-media-trigger')) {
          this.close();
        }
      });

      // 2. Backdrop click
      if (this.backdropEl) {
        this.backdropEl.addEventListener('click', () => this.close());
      }

      // 3. Close button
      const closeBtn = document.getElementById('mediaPickerCloseBtn');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.close());
      }

      // 4. Quick reactions
      const quickBar = document.getElementById('mediaPickerQuickBar');
      if (quickBar) {
        quickBar.addEventListener('click', (e) => {
          e.stopPropagation();
          const btn = e.target.closest('.media-picker-quick-emoji');
          if (btn && btn.dataset.emoji) {
            this.insertEmoji(btn.dataset.emoji);
          }
        });
      }

      // 5. Tabs
      const tabs = document.querySelectorAll('.media-picker-tab-btn');
      tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
          e.preventDefault();
          this.switchTab(tab.dataset.tab);
        });
      });

      // 6. Sticker Subtabs
      const subtabs = document.querySelectorAll('.media-picker-pill');
      subtabs.forEach(st => {
        st.addEventListener('click', (e) => {
          e.preventDefault();
          this.switchStickerSubtab(st.dataset.subtab);
        });
      });

      // 7. GIF Search with debounce & category chips
      const gifSearch = document.getElementById('mediaPickerGifSearch');
      const gifClear = document.getElementById('mediaPickerGifClear');
      const gifCategories = document.getElementById('mediaPickerGifCategories');

      const syncGifCategoryPills = (query) => {
        if (!gifCategories) return;
        const qNorm = (query || '').toLowerCase().trim();
        gifCategories.querySelectorAll('.media-picker-chip').forEach(chip => {
          const chipQ = (chip.dataset.query || '').toLowerCase().trim();
          chip.classList.toggle('active', chipQ === qNorm);
        });
      };

      if (gifCategories) {
        gifCategories.addEventListener('click', (e) => {
          const chip = e.target.closest('.media-picker-chip');
          if (!chip) return;
          e.preventDefault();
          const q = chip.dataset.query || '';
          if (gifSearch) gifSearch.value = q;
          if (gifClear) gifClear.classList.toggle('show', q.length > 0);
          syncGifCategoryPills(q);
          clearTimeout(this.gifSearchTimeout);
          this.gifQuery = q;
          this.gifPage = 1;
          this.loadGifs(true);
        });
      }

      if (gifSearch) {
        gifSearch.addEventListener('input', (e) => {
          const val = e.target.value.trim();
          gifClear.classList.toggle('show', val.length > 0);
          syncGifCategoryPills(val);
          clearTimeout(this.gifSearchTimeout);
          this.gifSearchTimeout = setTimeout(() => {
            this.gifQuery = val;
            this.gifPage = 1;
            this.loadGifs(true);
          }, 280);
        });

        gifSearch.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(this.gifSearchTimeout);
            const val = gifSearch.value.trim();
            this.gifQuery = val;
            this.gifPage = 1;
            this.loadGifs(true);
          }
        });
      }

      if (gifClear) {
        gifClear.addEventListener('click', () => {
          if (gifSearch) gifSearch.value = '';
          gifClear.classList.remove('show');
          syncGifCategoryPills('');
          clearTimeout(this.gifSearchTimeout);
          this.gifQuery = '';
          this.gifPage = 1;
          this.loadGifs(true);
        });
      }

      // 8. Sticker Search with debounce & category chips
      const stickerSearch = document.getElementById('mediaPickerStickerSearch');
      const stickerClear = document.getElementById('mediaPickerStickerClear');
      const stickerCategories = document.getElementById('mediaPickerStickerCategories');

      const syncStickerCategoryPills = (query) => {
        if (!stickerCategories) return;
        const qNorm = (query || '').toLowerCase().trim();
        stickerCategories.querySelectorAll('.media-picker-chip').forEach(chip => {
          const chipQ = (chip.dataset.query || '').toLowerCase().trim();
          chip.classList.toggle('active', chipQ === qNorm);
        });
      };

      if (stickerCategories) {
        stickerCategories.addEventListener('click', (e) => {
          const chip = e.target.closest('.media-picker-chip');
          if (!chip) return;
          e.preventDefault();
          if (this.activeStickerSubtab !== 'klipy') {
            this.switchStickerSubtab('klipy');
          }
          const q = chip.dataset.query || '';
          if (stickerSearch) stickerSearch.value = q;
          if (stickerClear) stickerClear.classList.toggle('show', q.length > 0);
          syncStickerCategoryPills(q);
          clearTimeout(this.stickerSearchTimeout);
          this.stickerQuery = q;
          this.stickerPage = 1;
          this.loadStickers(true);
        });
      }

      if (stickerSearch) {
        stickerSearch.addEventListener('input', (e) => {
          const val = e.target.value.trim();
          stickerClear.classList.toggle('show', val.length > 0);
          syncStickerCategoryPills(val);
          clearTimeout(this.stickerSearchTimeout);

          if (this.activeStickerSubtab === 'builtin') {
            this.renderBuiltinStickers(val);
          } else if (this.activeStickerSubtab === 'mine') {
            this.loadMyStickers(val);
          } else {
            this.stickerSearchTimeout = setTimeout(() => {
              this.stickerQuery = val;
              this.stickerPage = 1;
              this.loadStickers(true);
            }, 280);
          }
        });

        stickerSearch.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(this.stickerSearchTimeout);
            const val = stickerSearch.value.trim();
            this.stickerQuery = val;
            this.stickerPage = 1;
            this.loadStickers(true);
          }
        });
      }

      if (stickerClear) {
        stickerClear.addEventListener('click', () => {
          if (stickerSearch) stickerSearch.value = '';
          stickerClear.classList.remove('show');
          syncStickerCategoryPills('');
          clearTimeout(this.stickerSearchTimeout);
          this.stickerQuery = '';
          this.stickerPage = 1;
          this.loadStickers(true);
        });
      }

      // 9. Infinite Scroll on Grids
      const gifGrid = document.getElementById('mediaPickerGifGrid');
      if (gifGrid) {
        gifGrid.addEventListener('scroll', () => {
          if (this.isLoadingGifs || !this.hasMoreGifs) return;
          if (gifGrid.scrollTop + gifGrid.clientHeight >= gifGrid.scrollHeight - 140) {
            this.gifPage++;
            this.loadGifs(false);
          }
        }, { passive: true });
      }

      const stickerGrid = document.getElementById('mediaPickerStickerGrid');
      if (stickerGrid) {
        stickerGrid.addEventListener('scroll', () => {
          if (this.activeStickerSubtab !== 'klipy') return;
          if (this.isLoadingStickers || !this.hasMoreStickers) return;
          if (stickerGrid.scrollTop + stickerGrid.clientHeight >= stickerGrid.scrollHeight - 140) {
            this.stickerPage++;
            this.loadStickers(false);
          }
        }, { passive: true });
      }

      // 10. Action buttons in empty states & errors
      if (this.modalEl) {
        this.modalEl.addEventListener('click', (e) => {
          const clearGif = e.target.closest('[data-action="clear-gif-search"]');
          if (clearGif && gifClear) {
            e.preventDefault();
            gifClear.click();
            return;
          }

          const clearSticker = e.target.closest('[data-action="clear-sticker-search"]');
          if (clearSticker && stickerClear) {
            e.preventDefault();
            stickerClear.click();
            return;
          }

          const switchKlipy = e.target.closest('[data-action="switch-to-klipy-stickers"]');
          if (switchKlipy) {
            e.preventDefault();
            this.switchStickerSubtab('klipy');
            return;
          }

          const retryGif = e.target.closest('[data-action="retry-gif-search"]');
          if (retryGif) {
            e.preventDefault();
            this.loadGifs(true);
            return;
          }

          const retrySticker = e.target.closest('[data-action="retry-sticker-search"]');
          if (retrySticker) {
            e.preventDefault();
            this.loadStickers(true);
            return;
          }
        });
      }

      // 11. ESC key to close
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      // 12. Window resize / scroll position update
      window.addEventListener('resize', () => {
        if (this.isOpen && window.innerWidth >= 768 && this.currentTrigger) {
          this.positionModal(this.currentTrigger);
        }
      });

      // 13. Custom sticker file input
      const customStickerInput = document.getElementById('mediaPickerCustomStickerInput');
      if (customStickerInput) {
        customStickerInput.addEventListener('change', (e) => {
          const file = e.target.files && e.target.files[0];
          if (file) {
            this.uploadCustomSticker(file);
          }
        });
      }

      // 14. Delegate image / camera attachment buttons: [data-action="image-comment"]
      document.addEventListener('change', (e) => {
        if (e.target.matches('input[type="file"].comment-photo-input')) {
          const file = e.target.files && e.target.files[0];
          if (file) {
            const form = e.target.closest('form') || e.target.closest('.comment-composer');
            this.attachLocalImage(file, form);
          }
        }
      });

      // 15. Delegate remove attachment chip button
      document.addEventListener('click', (e) => {
        const removeBtn = e.target.closest('.comment-attachment-remove-btn');
        if (removeBtn) {
          e.preventDefault();
          const form = removeBtn.closest('form') || removeBtn.closest('.comment-composer') || document;
          this.clearAttachment(form);
        }
      });
    },

    toggle(triggerEl) {
      if (this.isOpen && this.currentTrigger === triggerEl) {
        this.close();
      } else {
        this.open(triggerEl);
      }
    },

    open(triggerEl) {
      this.init();
      this.currentTrigger = triggerEl;

      // Locate target input & form
      const targetSelector = triggerEl.dataset.input;
      let targetInput = targetSelector ? document.querySelector(targetSelector) : null;
      let form = triggerEl.closest('form') || triggerEl.closest('.comment-composer');

      if (!targetInput && form) {
        targetInput = form.querySelector('input[type="text"], textarea');
      } else if (!targetInput) {
        const container = triggerEl.closest('.comment-composer, .main-composer-input-wrapper, .modal-footer, .comment-row');
        if (container) {
          targetInput = container.querySelector('input[type="text"], textarea');
          form = container.querySelector('form') || container.closest('.comment-composer') || form;
        }
      }

      this.currentTargetInput = targetInput;
      this.currentForm = form;

      // Position modal
      this.positionModal(triggerEl);

      // Show modal
      this.backdropEl.classList.add('show');
      this.modalEl.classList.add('show');
      this.isOpen = true;

      // Sync dark mode class on emoji picker
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      const picker = this.modalEl.querySelector('emoji-picker');
      if (picker) {
        picker.classList.toggle('dark', isDark);
      }

      // Default load GIFs / Stickers if needed
      if (this.activeTab === 'gifs' && !this._gifsLoaded) {
        this.loadGifs();
      } else if (this.activeTab === 'stickers' && !this._stickersLoaded) {
        this.loadStickers();
      }
    },

    positionModal(triggerEl) {
      if (window.innerWidth < 768) {
        // Mobile bottom sheet: clear inline coordinates
        this.modalEl.style.left = '';
        this.modalEl.style.right = '';
        this.modalEl.style.top = '';
        this.modalEl.style.bottom = '';
        return;
      }

      // Desktop / Tablet floating anchored popover
      const rect = triggerEl.getBoundingClientRect();
      const modalWidth = 370;
      const modalHeight = 460;
      const padding = 12;

      // Horizontal: align with trigger, but keep inside viewport
      let left = rect.left + (rect.width / 2) - (modalWidth / 2);
      if (left < padding) left = padding;
      if (left + modalWidth > window.innerWidth - padding) {
        left = window.innerWidth - modalWidth - padding;
      }

      // Vertical: prefer above the trigger, flip below if not enough space
      let top;
      if (rect.top - modalHeight - 8 >= padding) {
        top = rect.top - modalHeight - 8;
      } else if (rect.bottom + modalHeight + 8 <= window.innerHeight - padding) {
        top = rect.bottom + 8;
      } else {
        // Center vertically if neither fits
        top = Math.max(padding, (window.innerHeight - modalHeight) / 2);
      }

      this.modalEl.style.left = `${Math.round(left)}px`;
      this.modalEl.style.top = `${Math.round(top)}px`;
      this.modalEl.style.bottom = 'auto';
      this.modalEl.style.right = 'auto';
    },

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;
      this.currentTrigger = null;

      if (this.modalEl) this.modalEl.classList.remove('show');
      if (this.backdropEl) this.backdropEl.classList.remove('show');
    },

    switchTab(tabName) {
      this.activeTab = tabName;

      document.querySelectorAll('.media-picker-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
        btn.setAttribute('aria-selected', btn.dataset.tab === tabName ? 'true' : 'false');
      });

      document.querySelectorAll('.media-picker-panel').forEach(panel => {
        panel.classList.toggle('active', panel.dataset.panel === tabName);
      });

      // Quick bar is only visible for Emoji tab
      const quickBar = document.getElementById('mediaPickerQuickBar');
      if (quickBar) {
        quickBar.style.display = tabName === 'emojis' ? 'flex' : 'none';
      }

      if (tabName === 'gifs' && !this._gifsLoaded) {
        this.loadGifs(true);
      } else if (tabName === 'stickers' && !this._stickersLoaded) {
        this.loadStickers(true);
      }
    },

    switchStickerSubtab(subtabName) {
      this.activeStickerSubtab = subtabName;

      document.querySelectorAll('.media-picker-pill').forEach(pill => {
        pill.classList.toggle('active', pill.dataset.subtab === subtabName);
      });

      const searchInput = document.getElementById('mediaPickerStickerSearch');
      const searchWrap = document.getElementById('mediaPickerStickerSearchWrap');
      const catBar = document.getElementById('mediaPickerStickerCategories');
      const footer = document.getElementById('mediaPickerStickerFooter');

      if (subtabName === 'builtin') {
        if (searchWrap) searchWrap.style.display = 'flex';
        if (searchInput) searchInput.placeholder = 'Filter built-in stickers...';
        if (catBar) catBar.style.display = 'none';
        if (footer) footer.style.display = 'none';
        this.renderBuiltinStickers(searchInput ? searchInput.value.trim() : '');
      } else if (subtabName === 'mine') {
        if (searchWrap) searchWrap.style.display = 'flex';
        if (searchInput) searchInput.placeholder = 'Filter your stickers...';
        if (catBar) catBar.style.display = 'none';
        if (footer) footer.style.display = 'none';
        this.loadMyStickers(searchInput ? searchInput.value.trim() : '');
      } else {
        if (searchWrap) searchWrap.style.display = 'flex';
        if (searchInput) searchInput.placeholder = 'Search stickers with KLIPY...';
        if (catBar) catBar.style.display = 'flex';
        if (footer) footer.style.display = 'flex';
        this.loadStickers(true);
      }
    },

    insertEmoji(emoji) {
      const input = this.currentTargetInput;
      if (!input) return;

      const start = input.selectionStart || 0;
      const end = input.selectionEnd || 0;
      const val = input.value || '';

      input.value = val.substring(0, start) + emoji + val.substring(end);
      const newPos = start + emoji.length;
      input.selectionStart = newPos;
      input.selectionEnd = newPos;

      // Trigger input & change events for validation & autosize
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));

      // Keep focus on input so user can seamlessly keep typing or sending
      input.focus();
    },

    attachMedia({ type, url, previewUrl, meta = {} }) {
      const form = this.currentForm || (this.currentTargetInput ? (this.currentTargetInput.closest('form') || this.currentTargetInput.closest('.comment-composer')) : null);
      if (!form) {
        console.warn('[MediaPicker] No active comment form found for attachment');
        this.close();
        return;
      }

      // Check or create attachment hidden inputs on the form
      this.setHiddenInput(form, 'attachment_type', type);
      this.setHiddenInput(form, 'attachment_url', url);
      this.setHiddenInput(form, 'attachment_meta', JSON.stringify(meta));

      // Remove existing attachment image file input value if any
      const fileInput = form.querySelector('input[type="file"].comment-photo-input');
      if (fileInput) fileInput.value = '';

      // Render preview chip above comment input
      this.renderAttachmentPreviewChip(form, {
        type,
        thumbUrl: previewUrl || url,
        title: meta.title || type.toUpperCase()
      });

      this.close();

      // Enable send button if disabled
      const sendBtn = form.querySelector('button[type="submit"], [data-action="send-reply"]');
      if (sendBtn) sendBtn.disabled = false;

      // Focus input so user can type text or hit Enter
      const textInput = form.querySelector('input[type="text"], textarea');
      if (textInput) textInput.focus();
    },

    attachLocalImage(file, form) {
      if (!file || !form) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target.result;

        this.setHiddenInput(form, 'attachment_type', 'image');
        this.setHiddenInput(form, 'attachment_url', '');
        this.setHiddenInput(form, 'attachment_meta', JSON.stringify({
          name: file.name,
          size: file.size,
          type: file.type
        }));

        this.renderAttachmentPreviewChip(form, {
          type: 'image',
          thumbUrl: dataUrl,
          title: 'Photo Sticker'
        });

        const sendBtn = form.querySelector('button[type="submit"], [data-action="send-reply"]');
        if (sendBtn) sendBtn.disabled = false;
      };
      reader.readAsDataURL(file);
    },

    renderAttachmentPreviewChip(form, { type, thumbUrl, title }) {
      let previewContainer = form.querySelector('.comment-attachment-preview-container');
      if (!previewContainer) {
        previewContainer = document.createElement('div');
        previewContainer.className = 'comment-attachment-preview-container';
        const inputWrap = form.querySelector('.flex-grow-1, .main-composer-input-wrapper, .composer-input, input, textarea');
        if (inputWrap) {
          inputWrap.parentElement.insertBefore(previewContainer, inputWrap);
        } else {
          form.insertBefore(previewContainer, form.firstChild);
        }
      }

      const isSticker = type === 'sticker';
      const badgeText = type === 'gif' ? 'GIF' : (type === 'sticker' ? 'STICKER' : 'PHOTO');

      previewContainer.innerHTML = `
        <div class="comment-attachment-preview-chip">
          <img src="${thumbUrl}" class="comment-attachment-preview-thumb ${isSticker ? 'is-sticker' : ''}" alt="Attachment">
          <div class="comment-attachment-preview-info">
            <span class="comment-attachment-preview-badge">${badgeText}</span>
            <span class="comment-attachment-preview-text">${title || 'Attachment'}</span>
          </div>
          <button type="button" class="comment-attachment-remove-btn" title="Remove attachment" aria-label="Remove attachment">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      `;
    },

    clearAttachment(form) {
      if (!form) return;
      this.setHiddenInput(form, 'attachment_type', 'none');
      this.setHiddenInput(form, 'attachment_url', '');
      this.setHiddenInput(form, 'attachment_meta', '{}');

      const fileInput = form.querySelector('input[type="file"].comment-photo-input');
      if (fileInput) fileInput.value = '';

      const previewContainer = form.querySelector('.comment-attachment-preview-container');
      if (previewContainer) {
        previewContainer.innerHTML = '';
      }

      // Check if text input is empty, disable send button if empty
      const textInput = form.querySelector('input[type="text"], textarea');
      const sendBtn = form.querySelector('button[type="submit"], [data-action="send-reply"]');
      if (sendBtn && textInput && !textInput.value.trim()) {
        sendBtn.disabled = true;
      }
    },

    setHiddenInput(form, name, value) {
      let input = form.querySelector(`input[name="${name}"]`);
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        form.appendChild(input);
      }
      input.value = value;
    },

    // =========================================================================
    // KLIPY GIFs Loading & Rendering
    // =========================================================================
    async loadGifs(reset = false) {
      if (this.isLoadingGifs) return;
      if (!reset && !this.hasMoreGifs) return;

      this.isLoadingGifs = true;
      const currentReqId = ++this.gifRequestId;

      const grid = document.getElementById('mediaPickerGifGrid');
      if (!grid) {
        this.isLoadingGifs = false;
        return;
      }

      if (reset) {
        this.gifPage = 1;
        this.hasMoreGifs = true;
        const msg = this.gifQuery ? `Searching "${this.escapeHtml(this.gifQuery)}"...` : 'Loading GIFs...';
        grid.innerHTML = `<div class="media-picker-loading"><div class="spinner-border spinner-border-sm text-primary"></div><span>${msg}</span></div>`;
        grid.scrollTop = 0;
      } else {
        const existingLoader = grid.querySelector('.media-picker-pagination-loader');
        if (!existingLoader) {
          const loader = document.createElement('div');
          loader.className = 'media-picker-pagination-loader';
          loader.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div><span>Loading more GIFs...</span>';
          grid.appendChild(loader);
        }
      }

      try {
        const q = encodeURIComponent(this.gifQuery || '');
        const url = `/api/media/klipy/?type=gifs&q=${q}&page=${this.gifPage}&per_page=24`;
        const res = await fetch(url);
        const json = await res.json();

        // Stale query response protection
        if (currentReqId !== this.gifRequestId) {
          return;
        }

        this._gifsLoaded = true;
        const items = json?.data?.data || [];

        // Remove loaders
        const bottomLoader = grid.querySelector('.media-picker-pagination-loader');
        if (bottomLoader) bottomLoader.remove();
        const mainLoader = grid.querySelector('.media-picker-loading');
        if (mainLoader) mainLoader.remove();

        if (reset) {
          grid.innerHTML = '';
        }

        if (!items || items.length === 0) {
          if (reset && grid.children.length === 0) {
            const emptyMsg = this.gifQuery
              ? `No GIFs found for "${this.escapeHtml(this.gifQuery)}"`
              : 'No GIFs available at the moment';
            grid.innerHTML = `
              <div class="media-picker-empty">
                <i class="bi bi-camera-video text-muted"></i>
                <span class="fw-semibold">${emptyMsg}</span>
                ${this.gifQuery ? '<button type="button" class="media-picker-empty-action" data-action="clear-gif-search"><i class="bi bi-arrow-clockwise me-1"></i>Browse Trending GIFs</button>' : ''}
              </div>
            `;
          }
          this.hasMoreGifs = false;
          return;
        }

        if (items.length < 24) {
          this.hasMoreGifs = false;
        }

        items.forEach(item => {
          const files = item.file || {};
          // Direct media loading per KLIPY requirements
          const gifUrl = files.md?.gif?.url || files.hd?.gif?.url || files.sm?.gif?.url || '';
          const previewUrl = files.sm?.webp?.url || files.sm?.gif?.url || files.xs?.gif?.url || gifUrl;
          if (!gifUrl) return;

          const card = document.createElement('div');
          card.className = 'media-picker-item';
          card.setAttribute('title', item.title || 'GIF');
          card.innerHTML = `<img src="${previewUrl}" alt="${this.escapeHtml(item.title || 'GIF')}" loading="lazy">`;

          card.addEventListener('click', () => {
            this.attachMedia({
              type: 'gif',
              url: gifUrl,
              previewUrl: previewUrl,
              meta: {
                id: item.id,
                slug: item.slug,
                title: item.title,
                width: files.md?.gif?.width || 320,
                height: files.md?.gif?.height || 240
              }
            });
          });

          grid.appendChild(card);
        });

      } catch (err) {
        if (currentReqId !== this.gifRequestId) return;
        console.error('[MediaPicker] Error loading GIFs:', err);
        const bottomLoader = grid.querySelector('.media-picker-pagination-loader');
        if (bottomLoader) bottomLoader.remove();
        if (reset) {
          grid.innerHTML = `
            <div class="media-picker-empty text-danger">
              <i class="bi bi-exclamation-circle"></i>
              <span>Failed to load GIFs. Check connection.</span>
              <button type="button" class="media-picker-empty-action" data-action="retry-gif-search">Try Again</button>
            </div>
          `;
        }
      } finally {
        if (currentReqId === this.gifRequestId) {
          this.isLoadingGifs = false;
        }
      }
    },

    // =========================================================================
    // Stickers Loading & Rendering
    // =========================================================================
    async loadStickers(reset = false) {
      if (this.activeStickerSubtab === 'builtin') {
        const searchInput = document.getElementById('mediaPickerStickerSearch');
        this.renderBuiltinStickers(searchInput ? searchInput.value.trim() : '');
        return;
      } else if (this.activeStickerSubtab === 'mine') {
        const searchInput = document.getElementById('mediaPickerStickerSearch');
        this.loadMyStickers(searchInput ? searchInput.value.trim() : '');
        return;
      }

      // KLIPY Stickers
      if (this.isLoadingStickers) return;
      if (!reset && !this.hasMoreStickers) return;

      this.isLoadingStickers = true;
      const currentReqId = ++this.stickerRequestId;

      const grid = document.getElementById('mediaPickerStickerGrid');
      if (!grid) {
        this.isLoadingStickers = false;
        return;
      }

      if (reset) {
        this.stickerPage = 1;
        this.hasMoreStickers = true;
        const msg = this.stickerQuery ? `Searching "${this.escapeHtml(this.stickerQuery)}"...` : 'Loading stickers...';
        grid.innerHTML = `<div class="media-picker-loading"><div class="spinner-border spinner-border-sm text-primary"></div><span>${msg}</span></div>`;
        grid.scrollTop = 0;
      } else {
        const existingLoader = grid.querySelector('.media-picker-pagination-loader');
        if (!existingLoader) {
          const loader = document.createElement('div');
          loader.className = 'media-picker-pagination-loader';
          loader.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div><span>Loading more stickers...</span>';
          grid.appendChild(loader);
        }
      }

      try {
        const q = encodeURIComponent(this.stickerQuery || '');
        const url = `/api/media/klipy/?type=stickers&q=${q}&page=${this.stickerPage}&per_page=24`;
        const res = await fetch(url);
        const json = await res.json();

        // Stale query response protection
        if (currentReqId !== this.stickerRequestId) return;

        this._stickersLoaded = true;
        const items = json?.data?.data || [];

        const bottomLoader = grid.querySelector('.media-picker-pagination-loader');
        if (bottomLoader) bottomLoader.remove();
        const mainLoader = grid.querySelector('.media-picker-loading');
        if (mainLoader) mainLoader.remove();

        if (reset) {
          grid.innerHTML = '';
          // Show matching built-in SVG stickers first if search term matches
          if (this.stickerQuery) {
            const queryNorm = this.stickerQuery.toLowerCase().trim();
            const matchingBuiltin = BUILTIN_STICKERS.filter(st => st.name.toLowerCase().includes(queryNorm));
            matchingBuiltin.forEach(st => {
              const card = document.createElement('div');
              card.className = 'media-picker-item';
              card.setAttribute('title', `${st.name} (Built-in)`);
              const stUrl = `/static/images/stickers/${st.file}`;
              card.innerHTML = `<img src="${stUrl}" alt="${this.escapeHtml(st.name)}" loading="lazy">`;
              card.addEventListener('click', () => {
                this.attachMedia({
                  type: 'sticker',
                  url: stUrl,
                  previewUrl: stUrl,
                  meta: { title: st.name, source: 'builtin' }
                });
              });
              grid.appendChild(card);
            });
          }
        }

        if (!items || items.length === 0) {
          if (reset && grid.children.length === 0) {
            const emptyMsg = this.stickerQuery
              ? `No stickers found for "${this.escapeHtml(this.stickerQuery)}"`
              : 'No stickers available';
            grid.innerHTML = `
              <div class="media-picker-empty">
                <i class="bi bi-stickies text-muted"></i>
                <span class="fw-semibold">${emptyMsg}</span>
                ${this.stickerQuery ? '<button type="button" class="media-picker-empty-action" data-action="clear-sticker-search"><i class="bi bi-arrow-clockwise me-1"></i>Browse Trending Stickers</button>' : ''}
              </div>
            `;
          }
          this.hasMoreStickers = false;
          return;
        }

        if (items.length < 24) {
          this.hasMoreStickers = false;
        }

        items.forEach(item => {
          const files = item.file || {};
          const stickerUrl = files.md?.webp?.url || files.md?.png?.url || files.hd?.webp?.url || files.hd?.gif?.url || '';
          const previewUrl = files.sm?.webp?.url || files.sm?.png?.url || stickerUrl;
          if (!stickerUrl) return;

          const card = document.createElement('div');
          card.className = 'media-picker-item';
          card.setAttribute('title', item.title || 'Sticker');
          card.innerHTML = `<img src="${previewUrl}" alt="${this.escapeHtml(item.title || 'Sticker')}" loading="lazy">`;

          card.addEventListener('click', () => {
            this.attachMedia({
              type: 'sticker',
              url: stickerUrl,
              previewUrl: previewUrl,
              meta: {
                id: item.id,
                slug: item.slug,
                title: item.title,
                source: 'klipy'
              }
            });
          });

          grid.appendChild(card);
        });

      } catch (err) {
        if (currentReqId !== this.stickerRequestId) return;
        console.error('[MediaPicker] Error loading stickers:', err);
        const bottomLoader = grid.querySelector('.media-picker-pagination-loader');
        if (bottomLoader) bottomLoader.remove();
        if (reset && grid.children.length === 0) {
          grid.innerHTML = `
            <div class="media-picker-empty text-danger">
              <i class="bi bi-exclamation-circle"></i>
              <span>Failed to load stickers.</span>
              <button type="button" class="media-picker-empty-action" data-action="retry-sticker-search">Try Again</button>
            </div>
          `;
        }
      } finally {
        if (currentReqId === this.stickerRequestId) {
          this.isLoadingStickers = false;
        }
      }
    },

    renderBuiltinStickers(filterQuery = '') {
      const grid = document.getElementById('mediaPickerStickerGrid');
      if (!grid) return;

      const q = (filterQuery || this.stickerQuery || '').toLowerCase().trim();
      const filtered = q
        ? BUILTIN_STICKERS.filter(st => st.name.toLowerCase().includes(q))
        : BUILTIN_STICKERS;

      grid.innerHTML = '';

      if (filtered.length === 0) {
        grid.innerHTML = `
          <div class="media-picker-empty">
            <i class="bi bi-stickies text-muted"></i>
            <span class="fw-semibold">No built-in stickers found for "${this.escapeHtml(q)}"</span>
            <button type="button" class="media-picker-empty-action" data-action="switch-to-klipy-stickers"><i class="bi bi-search me-1"></i>Search in KLIPY Stickers</button>
          </div>
        `;
        return;
      }

      filtered.forEach(st => {
        const card = document.createElement('div');
        card.className = 'media-picker-item';
        card.setAttribute('title', st.name);
        const stUrl = `/static/images/stickers/${st.file}`;
        card.innerHTML = `<img src="${stUrl}" alt="${this.escapeHtml(st.name)}" loading="lazy">`;

        card.addEventListener('click', () => {
          this.attachMedia({
            type: 'sticker',
            url: stUrl,
            previewUrl: stUrl,
            meta: {
              title: st.name,
              source: 'builtin'
            }
          });
        });

        grid.appendChild(card);
      });
    },

    async loadMyStickers(filterQuery = '') {
      const grid = document.getElementById('mediaPickerStickerGrid');
      if (!grid) return;

      const q = (filterQuery || this.stickerQuery || '').toLowerCase().trim();

      if (!this._myStickersCache) {
        grid.innerHTML = '<div class="media-picker-loading"><div class="spinner-border spinner-border-sm text-primary"></div><span>Loading your stickers...</span></div>';

        try {
          const res = await fetch('/api/stickers/mine/');
          if (!res.ok) {
            if (res.status === 401 || res.status === 403) {
              grid.innerHTML = '<div class="media-picker-empty"><i class="bi bi-lock"></i><span>Please log in to save and use custom stickers.</span></div>';
              return;
            }
            throw new Error('Failed to load user stickers');
          }

          this._myStickersCache = await res.json();
        } catch (err) {
          console.error('[MediaPicker] Error loading user stickers:', err);
          grid.innerHTML = '<div class="media-picker-empty text-danger"><i class="bi bi-exclamation-circle"></i><span>Failed to load custom stickers.</span></div>';
          return;
        }
      }

      const stickers = (this._myStickersCache || []).filter(st => {
        if (!q) return true;
        const name = (st.name || '').toLowerCase();
        return name.includes(q);
      });

      grid.innerHTML = '';

      // First item: "+ Add Sticker" button
      const uploadCard = document.createElement('div');
      uploadCard.className = 'media-picker-upload-card';
      uploadCard.innerHTML = `<i class="bi bi-plus-circle"></i><span>Upload</span>`;
      uploadCard.addEventListener('click', () => {
        const fileInput = document.getElementById('mediaPickerCustomStickerInput');
        if (fileInput) fileInput.click();
      });
      grid.appendChild(uploadCard);

      if (stickers.length === 0 && q) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'media-picker-empty';
        emptyDiv.innerHTML = `<span class="text-muted">No custom stickers matching "${this.escapeHtml(q)}"</span>`;
        grid.appendChild(emptyDiv);
        return;
      }

      stickers.forEach(st => {
        const card = document.createElement('div');
        card.className = 'media-picker-item';
        card.setAttribute('title', st.name || 'My Sticker');
        card.innerHTML = `<img src="${st.image}" alt="${this.escapeHtml(st.name || 'Sticker')}" loading="lazy">`;

        card.addEventListener('click', () => {
          this.attachMedia({
            type: 'sticker',
            url: st.image,
            previewUrl: st.image,
            meta: {
              id: st.id,
              title: st.name || 'Custom Sticker',
              source: 'user'
            }
          });
        });

        grid.appendChild(card);
      });
    },

    async uploadCustomSticker(file) {
      const formData = new FormData();
      formData.append('image', file);
      formData.append('name', file.name.replace(/\.[^/.]+$/, ""));

      const grid = document.getElementById('mediaPickerStickerGrid');
      if (grid) {
        grid.insertAdjacentHTML('afterbegin', '<div class="media-picker-loading uploading-pill"><div class="spinner-border spinner-border-sm text-primary"></div><span>Uploading sticker...</span></div>');
      }

      try {
        const csrfToken = this.getCsrfToken();
        const res = await fetch('/api/stickers/mine/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          },
          body: formData
        });

        if (!res.ok) throw new Error('Sticker upload failed');
        this.loadMyStickers();
      } catch (err) {
        console.error('[MediaPicker] Sticker upload failed:', err);
        alert('Failed to upload sticker. Please ensure image is under 5MB.');
        this.loadMyStickers();
      }
    },

    getCsrfToken() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      if (meta && meta.getAttribute('content')) {
        const val = meta.getAttribute('content').trim();
        if (val && !val.includes('{{')) return val;
      }
      const domInput = (this.activeForm && this.activeForm.querySelector('[name=csrfmiddlewaretoken]')) ||
                       document.querySelector('[name=csrfmiddlewaretoken]');
      if (domInput && domInput.value) return domInput.value;
      try {
        if (document.cookie) {
          const cookies = document.cookie.split(';');
          let localToken = '';
          let defaultToken = '';
          for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'pwaninet_local_csrftoken') {
              localToken = decodeURIComponent(value || '');
            } else if (name === 'csrftoken') {
              defaultToken = decodeURIComponent(value || '');
            }
          }
          if (localToken) return localToken;
          if (defaultToken) return defaultToken;
        }
      } catch (_) {}
      return '';
    }
  };

  // Expose globally
  window.MediaPicker = MediaPicker;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MediaPicker.init());
  } else {
    MediaPicker.init();
  }

})(window, document);
