/**
 * Pwanimate Chat Controller
 * Vanilla JS controller for Pwanimate assistant interface
 * Supports Web, PWA, and Capacitor Android WebView
 */

(function () {
    'use strict';

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
        return cookieMatch ? cookieMatch[1] : '';
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function isFinePointerDevice() {
        return typeof window !== 'undefined' &&
               window.matchMedia &&
               window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    }

    function isPwanimateCitationLink(element) {
        if (!element) return false;
        const citationControl = (element.matches && element.matches('a, button'))
            ? element
            : (typeof element.closest === 'function' ? element.closest('a, button') : null);
        if (!citationControl) return false;
        if (citationControl.classList && citationControl.classList.contains('pwanimate-citation-badge')) return true;
        if (typeof citationControl.closest === 'function') {
            if (citationControl.closest('.pwanimate-citations') || citationControl.closest('.pwanimate-citation-list')) return true;
        }
        if (typeof citationControl.hasAttribute === 'function') {
            if (citationControl.hasAttribute('data-pwanimate-resource') || citationControl.hasAttribute('data-citation')) return true;
        }
        const ds = citationControl.dataset || {};
        if (ds.resourceType || ds.sourceType || ds.documentShareId || ds.documentId || ds.postId) return true;
        return false;
    }

    /**
     * Returns a human-readable relative time string for a given ISO 8601 timestamp.
     * e.g. "just now", "2 minutes ago", "3 hours ago", "yesterday", "5 days ago"
     */
    function formatRelativeTime(isoString) {
        if (!isoString) return '';
        let date;
        try { date = new Date(isoString); } catch (e) { return ''; }
        if (isNaN(date.getTime())) return '';
        const diffMs = Date.now() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);
        if (diffSec < 60) return 'just now';
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return diffMin === 1 ? '1 minute ago' : diffMin + ' minutes ago';
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return diffHr === 1 ? '1 hour ago' : diffHr + ' hours ago';
        const diffDay = Math.floor(diffHr / 24);
        if (diffDay === 1) return 'yesterday';
        if (diffDay < 7) return diffDay + ' days ago';
        const diffWk = Math.floor(diffDay / 7);
        if (diffWk < 5) return diffWk === 1 ? '1 week ago' : diffWk + ' weeks ago';
        const diffMo = Math.floor(diffDay / 30);
        if (diffMo < 12) return diffMo === 1 ? '1 month ago' : diffMo + ' months ago';
        const diffYr = Math.floor(diffDay / 365);
        return diffYr === 1 ? '1 year ago' : diffYr + ' years ago';
    }

    class PwanimateChat {
        constructor(workspace) {
            this.workspace = workspace;
            this.conversationId = workspace.dataset.conversationId || null;
            this.pendingConversationId = this.conversationId;
            this.transcript = workspace.querySelector('#pwanimate-transcript');
            this.composerForm = workspace.querySelector('#pwanimate-composer-form');
            this.input = workspace.querySelector('#pwanimate-input');
            this.sendBtn = workspace.querySelector('#pwanimate-send-btn');
            this.voiceBtn = workspace.querySelector('#pwanimateVoiceBtn');
            this.voiceCancelBtn = workspace.querySelector('#pwanimateVoiceCancelBtn');
            this.voiceStopBtn = workspace.querySelector('#pwanimateVoiceStopBtn');
            this.voiceSendBtn = workspace.querySelector('#pwanimateVoiceSendBtn');
            this.voiceStatus = workspace.querySelector('#pwanimate-voice-status');
            this.voiceFeedback = workspace.querySelector('#pwanimate-voice-feedback');
            this.voiceCapture = workspace.querySelector('#pwanimate-voice-capture');
            this.voiceWaveform = workspace.querySelector('#pwanimate-voice-waveform');
            this.voiceWaveformBars = this.voiceWaveform ? Array.from(this.voiceWaveform.querySelectorAll('span')) : [];
            this.voiceRecognition = null;
            this.nativeSpeechBridge = null;
            this._onNativeSpeechEvent = null;
            this.voiceListening = false;
            this.voiceStopping = false;
            this.voiceSendAfterTranscription = false;
            this.voiceFinalTranscript = '';
            this.voiceSelection = null;
            this.voiceErrorMessage = '';
            this.voiceCancelled = false;
            this.voiceMediaStream = null;
            this.voiceAudioContext = null;
            this.voiceAnalyser = null;
            this.voiceAnimationFrame = null;
            this.sidebarList = document.getElementById('pwanimate-sidebar-list');
            this.mobileList = document.getElementById('pwanimate-mobile-list');
            this.quotaStatusEl = document.getElementById('pwanimate-quota-status');
            this.isGenerating = false;
            this.abortController = null;
            this.resizeFrame = null;
            this.thinkingTextInterval = null;
            this.thinkingFadeTimeout = null;
            this.lastPreviewTriggerEl = null;
            this._onDocumentClick = null;
            this._onKeyDown = null;
            this._mobileMenuSwipeStart = null;
            this._onMobileMenuTouchStart = null;
            this._onMobileMenuTouchEnd = null;
            this._onMobileMenuTouchCancel = null;

            // Phase 1 Workspace Geometry & State Contract
            this.leftRailCollapsed = localStorage.getItem('pwanimate_left_rail_collapsed') === 'true';
            const parsedPreferred = parseInt(localStorage.getItem('pwanimate_context_rail_width'), 10);
            this.savedPreferredWidth = (!isNaN(parsedPreferred) && parsedPreferred >= 280 && parsedPreferred <= 650) ? parsedPreferred : 360;
            this.currentRenderedWidth = 0;
            this.contextRailOpen = localStorage.getItem('pwanimateContextRailOpen') === 'true';
            this.activeResourceDetails = null;
            this.resizerEl = null;
            this.isResizing = false;
            this._onWindowResize = null;
            this._resizerCleanup = null;

            // Phase 2A Context Workspace & Multi-Resource State
            this.previewResourceState = null;
            this.contextResources = [];
            this.activeWorkspaceTab = 'preview'; // 'preview' | 'context'
            this.activeContextIndex = -1;
            this.previewDocViewer = null;
            this.contextDocViewer = null;

            // Model selection & Quota modal state
            this.selectedProvider = localStorage.getItem('pwanimate_selected_provider') || '';
            this.selectedModel = localStorage.getItem('pwanimate_selected_model') || '';
            this.selectedDisplay = localStorage.getItem('pwanimate_selected_display') || 'Auto';
            this.selectedProviderLabel = localStorage.getItem('pwanimate_selected_provider_label') || '';
            this.selectedModelLabel = workspace.querySelector('#pwanimate-selected-model-label');
            this.dropdownStatusDot = workspace.querySelector('#pwanimate-dropdown-status-dot');
            this.dropdownModelsList = workspace.querySelector('#pwanimate-dropdown-models-list');
            this.modalModelsContainer = document.getElementById('pwanimate-modal-models-container');
            this.refreshQuotaBtn = document.getElementById('pwanimateRefreshQuotaBtn');
            this.quotaModal = document.getElementById('pwanimateQuotaModal');
            this.cachedQuotaStatus = null;

            this.init();
        }

        init() {
            this.initWorkspaceGeometry();
            this.initInitialContextResources();
            this.initMarkdown();
            this.renderExistingMarkdown();
            this.initEmptyStateWelcome();
            this.checkCollapsibleUserBubbles();
            requestAnimationFrame(() => this.checkCollapsibleUserBubbles());
            this.bindEvents();
            this.initVoiceInput();
            this.initMobileMenuSwipeNavigation();
            this.initContextDocumentPicker();
            this.initAttachmentHandlers();
            this.updateQuotaStatus({ models: this.getDefaultModels() });
            this.updateSelectedModelUI();
            this.updateSendButtonState();
            if (this.input && this.input.value) {
                this.resizeTextarea();
            }
            this.scrollToBottom(false);
            this.fetchQuotaStatus();
            this.updateTimestamps(); // apply relative time to any server-rendered timestamps
            this.startTimestampTicker();
        }

        initInitialContextResources() {
            const jsonEl = document.getElementById('pwanimate-initial-context-resources');
            let initialResources = [];
            if (jsonEl) {
                try {
                    initialResources = JSON.parse(jsonEl.textContent || '[]');
                } catch (error) {
                    console.warn('[Pwanimate] Could not read initial context resources.', error);
                }
            }

            this.contextResources = (Array.isArray(initialResources) ? initialResources : []).map(resource =>
                this.normalizeResource(resource.mediaUrl || resource.url, resource.title, resource)
            );
            this.addImageAttachmentsToContext(this.transcript, false);
            if (!this.contextResources.length) return;

            this.activeContextIndex = 0;
            this.updateContextCountBadges();

            // Reveal the desktop rail before creating its viewer so the viewer
            // measures its final width on the first render. switchWorkspaceTab()
            // calls syncContextView(), so avoid an eager sync here: rendering it
            // twice immediately destroys the first viewer while it is loading.
            if (window.innerWidth >= 1200) {
                this.openContextRail();
            }
            this.switchWorkspaceTab('context');

            if (window.innerWidth < 1200) {
                const sheetEl = document.getElementById('pwanimateResourcePreviewSheet');
                if (sheetEl && window.bootstrap) {
                    let offcanvas = bootstrap.Offcanvas.getInstance(sheetEl);
                    if (!offcanvas) offcanvas = new bootstrap.Offcanvas(sheetEl);
                    offcanvas.show();
                }
            }
        }

        addImageAttachmentsToContext(root, openRail = true) {
            if (!root || !root.querySelectorAll) return false;
            let added = false;
            root.querySelectorAll('.pwanimate-message-attachment[data-preview-type="image"]').forEach((link) => {
                const url = link.dataset.mediaUrl || link.getAttribute('href') || '';
                if (!url) return;
                const attachmentId = link.dataset.attachmentId || '';
                const exists = this.contextResources.some(item =>
                    (attachmentId && item.attachmentId === attachmentId) ||
                    item.mediaUrl === url || item.url === url
                );
                if (exists) return;
                const name = link.dataset.fileName || 'Image attachment';
                const resource = this.normalizeResource(url, name, {
                    sourceType: 'attachment',
                    resourceType: 'image',
                    fileType: link.dataset.fileType || '',
                    mediaUrl: url,
                    attachmentId: attachmentId,
                });
                resource.icon = 'bi-image-fill';
                this.contextResources.push(resource);
                added = true;
            });

            if (added) {
                this.activeContextIndex = this.contextResources.length - 1;
                this.updateContextCountBadges();
                this.updateAddToContextButtons();
                this.syncContextView();
                this.switchWorkspaceTab('context');
                if (openRail) {
                    if (window.innerWidth >= 1200) this.openContextRail();
                    else this.openMobileWorkspaceSheet('context');
                }
            }
            return added;
        }

        initContextDocumentPicker() {
            this.contextDocumentModalEl = document.getElementById('pwanimateContextDocumentModal');
            this.contextDocumentSearchInput = document.getElementById('pwanimateContextDocumentSearch');
            this.contextDocumentResultsEl = document.getElementById('pwanimateContextDocumentResults');
            this.contextDocumentSearchResults = [];
            this.contextDocumentSearchTimer = null;
            this.contextDocumentSearchController = null;

            if (!this.contextDocumentSearchInput || !this.contextDocumentResultsEl) return;
            this.contextDocumentSearchInput.addEventListener('input', () => {
                clearTimeout(this.contextDocumentSearchTimer);
                const query = this.contextDocumentSearchInput.value.trim();
                if (this.contextDocumentSearchController) this.contextDocumentSearchController.abort();
                if (query.length < 2) {
                    this.contextDocumentSearchResults = [];
                    this.contextDocumentResultsEl.innerHTML = '<div class="text-center text-muted small py-4">Type at least two characters to search the repository.</div>';
                    return;
                }
                this.contextDocumentResultsEl.innerHTML = '<div class="text-center text-muted small py-4"><span class="spinner-border spinner-border-sm me-2" role="status"></span>Searching books…</div>';
                this.contextDocumentSearchTimer = setTimeout(() => this.searchContextDocuments(query), 250);
            });

            this.contextDocumentResultsEl.addEventListener('click', (event) => {
                const card = event.target.closest('[data-context-document-index]');
                if (!card) return;
                const index = Number.parseInt(card.dataset.contextDocumentIndex, 10);
                const result = this.contextDocumentSearchResults[index];
                if (!result) return;

                const resource = this.normalizeResource(result.media_url, result.title, {
                    sourceType: 'document',
                    resourceType: 'document',
                    documentId: result.document_id,
                    documentShareId: result.document_share_id,
                    documentVersionId: result.document_version_id,
                    fileId: result.file_id,
                    fileType: result.file_type,
                    mediaUrl: result.media_url,
                    thumbnailUrl: result.thumbnail_url,
                    citation: result.category,
                });
                const modal = window.bootstrap && this.contextDocumentModalEl
                    ? window.bootstrap.Modal.getInstance(this.contextDocumentModalEl)
                    : null;
                if (modal) modal.hide();
                this.addResourceToContext(resource);
            });
        }

        async searchContextDocuments(query) {
            if (!this.contextDocumentResultsEl) return;
            const controller = new AbortController();
            this.contextDocumentSearchController = controller;
            try {
                const response = await fetch(`/api/pwanimate/context/documents/?q=${encodeURIComponent(query)}`, {
                    credentials: 'same-origin',
                    headers: { 'Accept': 'application/json' },
                    signal: controller.signal,
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not search the document repository.');
                if (this.contextDocumentSearchInput.value.trim() !== query) return;
                this.contextDocumentSearchResults = Array.isArray(data.results) ? data.results : [];
                if (!this.contextDocumentSearchResults.length) {
                    this.contextDocumentResultsEl.innerHTML = '<div class="text-center text-muted small py-4">No books found. Try another title or topic.</div>';
                    return;
                }
                this.contextDocumentResultsEl.innerHTML = this.contextDocumentSearchResults.map((book, index) => {
                    const title = escapeHtml(book.title || 'Untitled book');
                    const category = escapeHtml(book.category || 'Document');
                    const fileType = escapeHtml((book.file_type || 'file').toUpperCase());
                    const thumbnail = book.thumbnail_url
                        ? `<img src="${escapeHtml(book.thumbnail_url)}" alt="" class="pwanimate-context-book-thumbnail">`
                        : '<span class="pwanimate-context-book-icon"><i class="bi bi-journal-bookmark-fill"></i></span>';
                    return `<button type="button" class="pwanimate-context-book-result" data-context-document-index="${index}">
                        ${thumbnail}
                        <span class="pwanimate-context-book-copy"><strong>${title}</strong><small>${category} · ${fileType}</small></span>
                        <i class="bi bi-arrow-up-right pwanimate-context-book-open"></i>
                    </button>`;
                }).join('');
            } catch (error) {
                if (error.name === 'AbortError') return;
                this.contextDocumentResultsEl.innerHTML = '<div class="text-center text-danger small py-4">Could not search the repository. Try again in a moment.</div>';
            }
        }

        openContextDocumentPicker() {
            if (!this.contextDocumentModalEl || !window.bootstrap) return;
            const modal = window.bootstrap.Modal.getOrCreateInstance(this.contextDocumentModalEl);
            modal.show();
            if (this.contextDocumentSearchInput) {
                this.contextDocumentSearchInput.value = '';
                this.contextDocumentSearchInput.dispatchEvent(new Event('input'));
                window.setTimeout(() => this.contextDocumentSearchInput.focus(), 150);
            }
        }

        initEmptyStateWelcome() {
            const emptyState = this.transcript && this.transcript.querySelector('#pwanimate-empty-state');
            if (!emptyState) return;

            const greetingEl = emptyState.querySelector('#pwanimate-empty-greeting');
            const questionEl = emptyState.querySelector('#pwanimate-empty-question');
            const suggestionsEl = emptyState.querySelector('#pwanimate-empty-suggestions');
            if (!greetingEl || !questionEl || !suggestionsEl) return;

            const name = (emptyState.dataset.nickname || emptyState.dataset.username || emptyState.dataset.displayName || '').trim();
            const tone = (emptyState.dataset.tone || 'neutral').toLowerCase();
            const interests = (emptyState.dataset.interests || '').split(',').map(value => value.trim()).filter(Boolean);
            const friendly = tone === 'friendly';
            const formal = tone === 'professional' || tone === 'academic';

            let welcomeLines;
            if (formal) {
                welcomeLines = [
                    { greeting: `Hello${name ? `, ${name}` : ''}.`, question: 'What would you like to work on today?' },
                    { greeting: `Good to see you${name ? `, ${name}` : ''}.`, question: 'Where should we start?' },
                    { greeting: `I'm ready when you are${name ? `, ${name}` : ''}.`, question: 'How can I support your studies today?' }
                ];
            } else if (friendly) {
                welcomeLines = [
                    { greeting: `Hey${name ? ` ${name}` : ''} 👋 How've you been today?`, question: 'What are we getting into today?' },
                    { greeting: `What's up${name ? `, ${name}` : ''}? I'm here for you.`, question: 'What are we tackling first?' },
                    { greeting: `Good to see you${name ? `, ${name}` : ''}!`, question: 'What are we in the mood to work on?' },
                    { greeting: `Hey${name ? ` ${name}` : ''},`, question: 'What’s on your mind today?' }
                ];
            } else {
                welcomeLines = [
                    { greeting: `Hi${name ? `, ${name}` : ''}.`, question: 'What are we up to today?' },
                    { greeting: `What's on your mind${name ? `, ${name}` : ''}?`, question: 'Want to talk something through or get some studying done?' },
                    { greeting: `I'm here for you${name ? `, ${name}` : ''}.`, question: 'Where should we start?' },
                    { greeting: `Hey${name ? ` ${name}` : ''} — how's today going?`, question: 'What should we tackle first?' }
                ];
            }

            if (interests.length) {
                const interest = interests[Math.floor(Math.random() * interests.length)];
                welcomeLines.push({
                    greeting: `Good to see you${name ? `, ${name}` : ''}.`,
                    question: `Want to use ${interest} for an example today, or start somewhere else?`
                });
            }

            const storageKey = `pwanimate_empty_welcome_${emptyState.dataset.username || 'student'}`;
            let previousIndex = -1;
            try {
                previousIndex = Number.parseInt(sessionStorage.getItem(storageKey), 10);
            } catch (_) {
                // Use the random selection when session storage is unavailable.
            }
            let welcomeIndex = Math.floor(Math.random() * welcomeLines.length);
            if (welcomeLines.length > 1 && welcomeIndex === previousIndex) {
                welcomeIndex = (welcomeIndex + 1 + Math.floor(Math.random() * (welcomeLines.length - 1))) % welcomeLines.length;
            }
            try {
                sessionStorage.setItem(storageKey, String(welcomeIndex));
            } catch (_) {
                // Ignore storage restrictions; the selected copy still displays.
            }

            greetingEl.textContent = welcomeLines[welcomeIndex].greeting;
            questionEl.textContent = welcomeLines[welcomeIndex].question;

            const suggestions = [
                { label: 'Explain a tricky topic', prompt: 'Help me understand a topic I find difficult. Ask me which topic first.' },
                { label: 'Find notes or past papers', prompt: 'Help me find lecture notes or past papers for my programme.' },
                { label: 'Plan a study session', prompt: 'Help me plan a focused study session for today.' },
                { label: 'Explain it with an example', prompt: 'Explain a difficult academic idea using a simple, concrete example.' },
                { label: 'Quiz me', prompt: 'Quiz me on a topic I am studying, one question at a time. First ask me which topic.' },
                { label: 'Brainstorm an assignment', prompt: 'Help me brainstorm ideas for an assignment. Ask what the assignment is about.' }
            ];
            if (interests.length) {
                const interest = interests[Math.floor(Math.random() * interests.length)];
                suggestions.push({
                    label: `Explore ${interest}`,
                    prompt: `Can you help me explore ${interest}? Suggest a useful way to connect it with something I'm studying, if relevant.`
                });
            }

            suggestionsEl.replaceChildren();
            for (let i = suggestions.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [suggestions[i], suggestions[j]] = [suggestions[j], suggestions[i]];
            }
            suggestions.slice(0, 3).forEach(suggestion => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'pwanimate-suggestion-chip';
                button.dataset.prompt = suggestion.prompt;
                button.textContent = suggestion.label;
                suggestionsEl.appendChild(button);
            });
        }

        initMarkdown() {
            if (window.marked && typeof window.marked.use === 'function') {
                window.marked.use({
                    breaks: true,
                    gfm: true
                });
            }
        }

        renderExistingMarkdown() {
            if (!this.transcript) return;
            const parseElements = () => {
                const mdElements = this.transcript.querySelectorAll('.pwanimate-markdown-body[data-raw]');
                mdElements.forEach((el) => {
                    const raw = el.getAttribute('data-raw');
                    if (raw) {
                        try {
                            el.innerHTML = this.renderMarkdownWithMathAndCode(raw);
                            this.postProcessMarkdownDOM(el);
                        } catch (e) {
                            console.warn('[Pwanimate] Markdown parse error:', e);
                        }
                    }
                });
            };

            if (window.marked) {
                parseElements();
            } else {
                let attempts = 0;
                const checkMarked = setInterval(() => {
                    attempts++;
                    if (window.marked) {
                        clearInterval(checkMarked);
                        this.initMarkdown();
                        parseElements();
                    } else if (attempts > 30) {
                        clearInterval(checkMarked);
                    }
                }, 50);
            }
        }

        sanitizeToolCallTokens(text) {
            if (!text || typeof text !== 'string') return '';

            const parseToolBlock = (block) => {
                let cleaned = block.trim();
                if (cleaned.startsWith('[') && cleaned.endsWith(']')) {
                    cleaned = cleaned.slice(1, -1).trim();
                }
                const funcMatch = cleaned.match(/^([a-zA-Z0-9_]+)\s*\(([\s\S]*)\)\s*$/);
                if (!funcMatch) return block;

                const funcName = funcMatch[1];
                const argsStr = funcMatch[2].trim();

                if (funcName === 'write') {
                    const pathMatch = argsStr.match(/path=(['"])(.*?)\1/);
                    const path = pathMatch ? pathMatch[2] : '';
                    const ext = path.includes('.') ? path.split('.').pop().toLowerCase() : 'python';
                    const langMap = {
                        py: 'python',
                        js: 'javascript',
                        ts: 'typescript',
                        sh: 'bash',
                        sql: 'sql',
                        json: 'json',
                        html: 'html',
                        css: 'css'
                    };
                    const lang = langMap[ext] || ext || 'python';

                    let content = '';
                    const contentMatch = argsStr.match(/content=(['"])([\s\S]*)/);
                    if (contentMatch) {
                        const quote = contentMatch[1];
                        content = contentMatch[2];
                        content = content.replace(new RegExp(`${quote}\\s*\\)?\\s*$`), '');
                    } else {
                        content = argsStr;
                    }

                    try {
                        content = content
                            .replace(/\\n/g, '\n')
                            .replace(/\\t/g, '\t')
                            .replace(/\\r/g, '\r')
                            .replace(/\\"/g, '"')
                            .replace(/\\'/g, "'")
                            .replace(/\\\\/g, '\\');
                    } catch (e) {}

                    const fileHeader = path ? `### \`${path}\`\n\n` : '';
                    return `${fileHeader}\`\`\`${lang}\n${content.trim()}\n\`\`\``;
                }
                return block;
            };

            let res = text.replace(/<\|tool_call_start\|>([\s\S]*?)<\|tool_call_end\|>/g, (match, inner) => {
                return '\n\n' + parseToolBlock(inner) + '\n\n';
            });

            res = res.replace(/\[write\(\s*(?:path=['"][^'"]+['"]\s*,\s*)?content=['"][\s\S]*?['"]\s*\)\]/g, (match) => {
                return '\n\n' + parseToolBlock(match) + '\n\n';
            });

            res = res.replace(/<\/?(?:\|tool_call_start\||\|tool_call_end\||tool_call)>/g, '');
            return res.trim();
        }

        renderMarkdownWithMathAndCode(content) {
            if (!content) return '';

            // 0. Transform accidental synthetic tool calls into Markdown
            let processed = content;
            if (processed.includes('tool_call') || processed.includes('[write(') || processed.includes('write(path=')) {
                processed = this.sanitizeToolCallTokens(processed);
            }

            const mathPlaceholders = [];
            const storeMath = (mathCode, displayMode) => {
                const id = `PWANIMATE_MATH_PH_${mathPlaceholders.length}_XYZ`;
                mathPlaceholders.push({ id, code: mathCode, displayMode });
                return id;
            };

            // 1. Block math: $$ ... $$ and \[ ... \]
            processed = processed.replace(/\$\$([\s\S]*?)\$\$/g, (match, code) => {
                return '\n\n' + storeMath(code, true) + '\n\n';
            });
            processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (match, code) => {
                return '\n\n' + storeMath(code, true) + '\n\n';
            });

            // 2. Inline math: \( ... \) and $ ... $ (avoiding escaped \$ and empty/spaced dollars)
            processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (match, code) => {
                return storeMath(code, false);
            });
            processed = processed.replace(/(?<!\\)\$([^\$\n]+?)(?<!\\)\$/g, (match, code) => {
                if (!code.trim()) return match;
                return storeMath(code, false);
            });

            // 3. Marked parse
            let html = '';
            if (window.marked && typeof window.marked.parse === 'function') {
                try {
                    html = window.marked.parse(processed);
                } catch (e) {
                    console.warn('[Pwanimate] Marked parse error:', e);
                    html = escapeHtml(content);
                    return html;
                }
            } else {
                html = escapeHtml(content);
            }

            // 4. Sanitize with DOMPurify
            if (window.DOMPurify && typeof window.DOMPurify.sanitize === 'function') {
                html = window.DOMPurify.sanitize(html, {
                    ADD_TAGS: ['annotation', 'math', 'semantics', 'mrow', 'mi', 'mn', 'mo', 'msup', 'msub', 'mfrac', 'mover', 'munder', 'msqrt', 'mroot', 'mtd', 'mtr', 'mtable', 'mtext', 'mspace'],
                    ADD_ATTR: ['xmlns', 'display', 'displaystyle', 'mathvariant', 'columnalign', 'rowalign', 'linethickness']
                });
            }

            // 5. Replace math placeholders with KaTeX rendered HTML
            if (window.katex && typeof window.katex.renderToString === 'function') {
                mathPlaceholders.forEach(({ id, code, displayMode }) => {
                    try {
                        const decodedCode = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
                        const renderedMath = window.katex.renderToString(decodedCode, {
                            displayMode: displayMode,
                            throwOnError: false,
                            output: 'htmlAndMathml'
                        });
                        html = html.split(id).join(renderedMath);
                    } catch (err) {
                        console.warn('[Pwanimate] KaTeX render error:', err);
                        const fallback = displayMode ? `<pre class="katex-fallback">${escapeHtml(code)}</pre>` : `<code>${escapeHtml(code)}</code>`;
                        html = html.split(id).join(fallback);
                    }
                });
            } else {
                mathPlaceholders.forEach(({ id, code, displayMode }) => {
                    const fallback = displayMode ? `<pre class="katex-fallback">${escapeHtml(code)}</pre>` : `<code>${escapeHtml(code)}</code>`;
                    html = html.split(id).join(fallback);
                });
            }

            return html;
        }

        postProcessMarkdownDOM(container) {
            if (!container) return;

            // 1. Wrap tables in responsive scroll wrapper
            const tables = container.querySelectorAll('table');
            tables.forEach(table => {
                if (!table.parentElement.classList.contains('pwanimate-table-scroll') &&
                    !table.parentElement.classList.contains('pwanimate-table-wrapper')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'pwanimate-table-scroll pwanimate-table-wrapper';
                    table.parentNode.insertBefore(wrapper, table);
                    wrapper.appendChild(table);
                }
            });

            // 2. Enhance code blocks: Prism highlighting + Header with Language badge & Copy button
            const preBlocks = container.querySelectorAll('pre');
            preBlocks.forEach(pre => {
                if (pre.closest('.pwanimate-code-block') || pre.classList.contains('katex-fallback')) return;

                const code = pre.querySelector('code');
                let lang = 'code';
                if (code) {
                    const classMatch = (code.className || '').match(/language-([a-zA-Z0-9_\-#+]+)/);
                    if (classMatch) {
                        lang = classMatch[1];
                    }
                }

                const wrapper = document.createElement('div');
                wrapper.className = 'pwanimate-code-block';

                const header = document.createElement('div');
                header.className = 'pwanimate-code-header';

                const langSpan = document.createElement('span');
                langSpan.className = 'pwanimate-code-lang';
                langSpan.textContent = lang;

                const copyBtn = document.createElement('button');
                copyBtn.type = 'button';
                copyBtn.className = 'pwanimate-code-copy-btn';
                copyBtn.setAttribute('aria-label', 'Copy code');
                copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> <span>Copy</span>';

                header.appendChild(langSpan);
                header.appendChild(copyBtn);

                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(header);
                wrapper.appendChild(pre);

                if (code && window.Prism && typeof window.Prism.highlightElement === 'function') {
                    try {
                        window.Prism.highlightElement(code);
                    } catch (e) {
                        console.warn('[Pwanimate] Prism highlight error:', e);
                    }
                }
            });
        }

        checkCollapsibleUserBubbles(container = this.transcript) {
            if (!container) return;
            const bubbles = container.querySelectorAll('.pwanimate-user-bubble');
            bubbles.forEach(bubble => {
                if (bubble.dataset.collapsibleChecked === 'true') return;

                if (bubble.scrollHeight > 220) {
                    bubble.classList.add('is-collapsible');
                    bubble.dataset.collapsibleChecked = 'true';

                    const wrapper = bubble.closest('.pwanimate-user-bubble-wrapper') || bubble.parentElement;
                    if (wrapper && !wrapper.querySelector('.pwanimate-show-more-btn')) {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'pwanimate-show-more-btn';
                        btn.setAttribute('aria-expanded', 'false');
                        btn.innerHTML = '<i class="bi bi-chevron-down"></i> <span>Show more</span>';
                        wrapper.appendChild(btn);
                    }
                }
            });
        }

        copyToClipboard(text, btnElement = null) {
            if (!text) return Promise.resolve(false);

            const showSuccess = () => {
                if (!btnElement) return;
                const originalHtml = btnElement.innerHTML;
                btnElement.classList.add('copied');
                btnElement.innerHTML = btnElement.classList.contains('pwanimate-code-copy-btn')
                    ? '<i class="bi bi-check2 text-success"></i> <span>Copied!</span>'
                    : '<i class="bi bi-check2 text-success"></i>';
                setTimeout(() => {
                    btnElement.classList.remove('copied');
                    btnElement.innerHTML = originalHtml;
                }, 2000);
            };

            if (navigator.clipboard && window.isSecureContext) {
                return navigator.clipboard.writeText(text).then(() => {
                    showSuccess();
                    return true;
                }).catch(err => {
                    console.warn('[Pwanimate] Clipboard API error, falling back:', err);
                    return this.fallbackCopyText(text, showSuccess);
                });
            } else {
                return Promise.resolve(this.fallbackCopyText(text, showSuccess));
            }
        }

        fallbackCopyText(text, onSuccess) {
            try {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                textarea.style.top = '0';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                const successful = document.execCommand('copy');
                document.body.removeChild(textarea);
                if (successful && onSuccess) onSuccess();
                return successful;
            } catch (e) {
                console.warn('[Pwanimate] Fallback copy failed:', e);
                return false;
            }
        }

        bindEvents() {
            // Form submission
            if (this.composerForm) {
                this.composerForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    if (this.isGenerating) {
                        this.handleAbort();
                    } else {
                        this.handleSend();
                    }
                });
            }

            // Direct Send / Stop button click handling
            if (this.sendBtn) {
                this.sendBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (this.isGenerating) {
                        this.handleAbort();
                    } else {
                        this.handleSend();
                    }
                });
            }

            // Global Escape shortcut to abort generation
            this._onKeyDown = (e) => {
                if (e.key === 'Escape' && this.isGenerating) {
                    e.preventDefault();
                    this.handleAbort();
                }
            };
            document.addEventListener('keydown', this._onKeyDown);

            // Keyboard navigation in textarea
            if (this.input) {
                this.input.addEventListener('keydown', (e) => {
                    if (e.isComposing || e.keyCode === 229) {
                        return;
                    }
                    if (e.key === 'Enter' && !e.shiftKey) {
                        if (isFinePointerDevice()) {
                            e.preventDefault();
                            if (this.isGenerating) {
                                this.handleAbort();
                            } else {
                                this.handleSend();
                            }
                        }
                        // On touch/coarse devices, do not preventDefault: native newline is inserted
                    }
                });

                // Auto-resize textarea with rAF batching and synchronize send button state
                this.input.addEventListener('input', () => {
                    this.scheduleTextareaResize();
                    this.updateSendButtonState();
                });
            }

            // Transcript delegated actions (Suggestion chips, Citations, Copy, Edit, Show more)
            if (this.transcript) {
                this.transcript.addEventListener('click', (e) => {
                    const resourceDownload = e.target.closest('.pwanimate-resource-download');
                    if (resourceDownload) {
                        e.preventDefault();
                        this.downloadGeneratedResource(resourceDownload);
                        return;
                    }

                    const chip = e.target.closest('.pwanimate-suggestion-chip');
                    if (chip && chip.dataset.prompt) {
                        e.preventDefault();
                        if (this.input) {
                            this.input.value = chip.dataset.prompt;
                            this.updateSendButtonState();
                            this.handleSend();
                        }
                        return;
                    }

                    const personPreviewBtn = e.target.closest('.pwanimate-person-preview-btn');
                    if (personPreviewBtn) {
                        e.preventDefault();
                        let person = {};
                        try { person = JSON.parse(personPreviewBtn.dataset.person || '{}'); } catch (error) {}
                        if (!person.username) {
                            person = {
                                username: personPreviewBtn.dataset.username || '',
                                display_name: personPreviewBtn.dataset.displayName || '',
                                profile_url: personPreviewBtn.dataset.profileUrl || '',
                                profile_card_url: personPreviewBtn.dataset.profileCardUrl || '',
                                avatar_url: personPreviewBtn.dataset.avatarUrl || '',
                                headline: personPreviewBtn.dataset.headline || '',
                                academic_level: personPreviewBtn.dataset.academicLevel || '',
                                programme_name: personPreviewBtn.dataset.programmeName || '',
                                bio: personPreviewBtn.dataset.bio || '',
                            };
                        }
                        const profileUrl = personPreviewBtn.dataset.profileUrl || person.profile_url || '';
                        this.previewResource(profileUrl, person.display_name || person.username || 'Student profile', {
                            sourceType: 'user',
                            resourceType: 'profile',
                            username: person.username || '',
                            person: person,
                            profileUrl: profileUrl,
                            profileCardUrl: person.profile_card_url || person.profileCardUrl || '',
                            description: person.headline || person.bio || '',
                        });
                        return;
                    }

                    const messageAttachment = e.target.closest('.pwanimate-message-attachment');
                    if (messageAttachment) {
                        e.preventDefault();
                        const name = messageAttachment.dataset.fileName || 'Attachment';
                        const attachmentUrl = messageAttachment.dataset.mediaUrl || messageAttachment.getAttribute('href') || '';
                        this.previewResource(attachmentUrl, name, {
                            sourceType: 'attachment',
                            resourceType: messageAttachment.dataset.previewType || 'document',
                            fileType: messageAttachment.dataset.fileType || '',
                            mediaUrl: attachmentUrl,
                            attachmentId: messageAttachment.dataset.attachmentId || '',
                        });
                        return;
                    }

                    const badge = e.target.closest('a, button');
                    if (badge && isPwanimateCitationLink(badge)) {
                        e.preventDefault();
                        const url = badge.getAttribute('href') || badge.dataset.url || '';
                        let title = badge.dataset.title || 'Resource Preview';
                        if (title === 'Resource Preview') {
                            const span = badge.querySelector('span');
                            if (span && span.textContent.trim()) {
                                title = span.textContent.trim();
                            } else if (badge.textContent && badge.textContent.trim()) {
                                title = badge.textContent.trim();
                            }
                        }
                        const meta = {
                            sourceType: badge.dataset.sourceType || '',
                            resourceType: badge.dataset.resourceType || '',
                            mediaUrl: badge.dataset.mediaUrl || '',
                            thumbnailUrl: badge.dataset.thumbnailUrl || '',
                            hlsUrl: badge.dataset.hlsUrl || '',
                            author: badge.dataset.author || '',
                            snippet: badge.dataset.snippet || '',
                            citation: badge.dataset.citation || '',
                            pageNumber: badge.dataset.pageNumber || null,
                            documentId: badge.dataset.documentId || '',
                            documentShareId: badge.dataset.documentShareId || '',
                            fileType: badge.dataset.fileType || '',
                            postId: badge.dataset.postId || '',
                            username: badge.dataset.username || '',
                            profileUrl: badge.dataset.profileUrl || '',
                            profileCardUrl: badge.dataset.profileCardUrl || '',
                            person: {
                                username: badge.dataset.username || '',
                                profile_url: badge.dataset.profileUrl || '',
                                profile_card_url: badge.dataset.profileCardUrl || '',
                                avatar_url: badge.dataset.avatarUrl || '',
                                headline: badge.dataset.headline || '',
                                academic_level: badge.dataset.academicLevel || '',
                                programme_name: badge.dataset.programmeName || '',
                                bio: badge.dataset.bio || '',
                            },
                            triggerEl: badge
                        };
                        this.previewResource(url, title, meta);
                        return;
                    }

                    // Show more / Show less toggle on collapsible user bubble
                    const showMoreBtn = e.target.closest('.pwanimate-show-more-btn');
                    if (showMoreBtn) {
                        e.preventDefault();
                        const wrapper = showMoreBtn.closest('.pwanimate-user-bubble-wrapper') || showMoreBtn.parentElement;
                        const bubble = wrapper ? wrapper.querySelector('.pwanimate-user-bubble') : showMoreBtn.previousElementSibling;
                        if (bubble) {
                            const isExpanded = bubble.classList.toggle('is-expanded');
                            showMoreBtn.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
                            showMoreBtn.innerHTML = isExpanded
                                ? '<i class="bi bi-chevron-up"></i> <span>Show less</span>'
                                : '<i class="bi bi-chevron-down"></i> <span>Show more</span>';
                        }
                        return;
                    }

                    // Copy action on code block
                    const codeCopyBtn = e.target.closest('.pwanimate-code-copy-btn');
                    if (codeCopyBtn) {
                        e.preventDefault();
                        const codeBlock = codeCopyBtn.closest('.pwanimate-code-block');
                        const code = codeBlock ? codeBlock.querySelector('code') : null;
                        if (code) {
                            this.copyToClipboard(code.textContent, codeCopyBtn);
                        }
                        return;
                    }

                    // Copy action on user or assistant message
                    const copyBtn = e.target.closest('.pwanimate-action-btn.copy-btn');
                    if (copyBtn) {
                        e.preventDefault();
                        const row = copyBtn.closest('.pwanimate-message-row');
                        if (row) {
                            if (row.classList.contains('user')) {
                                const bubble = row.querySelector('.pwanimate-user-bubble');
                                const text = bubble ? (bubble.getAttribute('data-raw') || bubble.textContent) : '';
                                this.copyToClipboard(text, copyBtn);
                            } else if (row.classList.contains('assistant')) {
                                const mdBody = row.querySelector('.pwanimate-markdown-body');
                                const text = mdBody ? (mdBody.getAttribute('data-raw') || mdBody.innerText) : '';
                                this.copyToClipboard(text, copyBtn);
                            }
                        }
                        return;
                    }

                    // Edit action on user message
                    const editBtn = e.target.closest('.pwanimate-action-btn.edit-btn');
                    if (editBtn) {
                        e.preventDefault();
                        const row = editBtn.closest('.pwanimate-message-row.user');
                        if (row) {
                            const bubble = row.querySelector('.pwanimate-user-bubble');
                            const text = bubble ? (bubble.getAttribute('data-raw') || bubble.textContent) : '';
                            if (this.input) {
                                this.input.value = text;
                                this.resizeTextarea();
                                this.input.focus();
                                this.input.scrollIntoView({ behavior: 'smooth', block: 'end' });
                            }
                        }
                        return;
                    }
                });
            }

            // Consolidated delegated click listener on document for delete, preview close, and model dropdowns
            this._onDocumentClick = (e) => {
                // Delete conversation buttons (delegated on document so desktop sidebar buttons work)
                const deleteBtn = e.target.closest('.pwanimate-conversation-delete');
                if (deleteBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const convId = deleteBtn.dataset.conversationId;
                    if (convId) {
                        this.handleDeleteConversation(convId);
                    }
                    return;
                }

                const openContextPicker = e.target.closest('[data-pwanimate-open-context-picker]');
                if (openContextPicker) {
                    e.preventDefault();
                    this.openContextDocumentPicker();
                    return;
                }

                const mobileContextSheetBtn = e.target.closest('#pwanimateMobileContextSheetBtn');
                if (mobileContextSheetBtn) {
                    e.preventDefault();
                    this.openMobileWorkspaceSheet('context');
                    return;
                }

                // Close desktop preview button (closes active card, leaves rail open in State B)
                const closeDesktopPreview = e.target.closest('#desktopPreviewCloseBtn');
                if (closeDesktopPreview) {
                    e.preventDefault();
                    this.closePreview();
                    return;
                }

                // Workspace Tab Switching: Preview vs Context (Desktop & Mobile)
                const previewTabBtn = e.target.closest('#desktopTabPreviewBtn, #mobileTabPreviewBtn');
                if (previewTabBtn) {
                    e.preventDefault();
                    this.switchWorkspaceTab('preview');
                    return;
                }

                const contextTabBtn = e.target.closest('#desktopTabContextBtn, #mobileTabContextBtn');
                if (contextTabBtn) {
                    e.preventDefault();
                    this.switchWorkspaceTab('context');
                    return;
                }

                // Add to Context buttons (Desktop & Mobile)
                const addContextBtn = e.target.closest('#desktopPreviewAddToContextBtn, #previewSheetAddToContextBtn');
                if (addContextBtn) {
                    e.preventDefault();
                    this.addResourceToContext(this.previewResourceState);
                    return;
                }

                // Remove from Context buttons (Surface header)
                const removeContextBtn = e.target.closest('#desktopContextRemoveBtn, #mobileContextRemoveBtn');
                if (removeContextBtn) {
                    e.preventDefault();
                    this.removeResourceFromContext(this.activeContextIndex);
                    return;
                }

                // Context chip remove button (X icon on chip)
                const chipRemoveBtn = e.target.closest('.pwanimate-chip-remove');
                if (chipRemoveBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const idx = parseInt(chipRemoveBtn.dataset.index, 10);
                    if (!isNaN(idx)) {
                        this.removeResourceFromContext(idx);
                    }
                    return;
                }

                // Context chip selection
                const chipItem = e.target.closest('.pwanimate-context-chip');
                if (chipItem) {
                    e.preventDefault();
                    const idx = parseInt(chipItem.dataset.index, 10);
                    if (!isNaN(idx)) {
                        this.selectContextResource(idx);
                    }
                    return;
                }

                // Close context rail button (closes entire rail)
                const closeContextRail = e.target.closest('#pwanimateContextRailCloseBtn');
                if (closeContextRail) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.closeContextRail();
                    return;
                }

                // Open context rail button (workspace top-right toggle)
                const toggleContextRail = e.target.closest('#pwanimateContextRailToggleBtn');
                if (toggleContextRail) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.openContextRail();
                    return;
                }

                // Left rail toggle buttons (delegated on document so they work across OOB rail swaps)
                const collapseBtn = e.target.closest('#pwanimateLeftRailCollapseBtn');
                if (collapseBtn) {
                    e.preventDefault();
                    this.toggleLeftRail(true);
                    return;
                }

                const expandBtn = e.target.closest('#pwanimateLeftRailExpandBtn');
                if (expandBtn) {
                    e.preventDefault();
                    this.toggleLeftRail(false);
                    return;
                }

                // Model dropdown selection
                const opt = e.target.closest('.pwanimate-model-option');
                if (opt) {
                    e.preventDefault();
                    const provider = opt.dataset.provider || '';
                    const model = opt.dataset.model || '';
                    const display = opt.dataset.display || 'Auto';
                    const providerLabel = opt.dataset.providerLabel || '';
                    this.selectModel(provider, model, display, providerLabel);
                    return;
                }
            };
            document.addEventListener('click', this._onDocumentClick);

            // Escape key listener to close preview
            this._onKeyDown = (e) => {
                if (e.key === 'Escape' || e.key === 'Esc') {
                    if (this.activeWorkspaceTab === 'preview' && (this.previewResourceState || this.activeResourceDetails)) {
                        this.closePreview();
                    }
                }
            };
            document.addEventListener('keydown', this._onKeyDown);

            // Close mobile preview sheet handler
            const previewSheet = document.getElementById('pwanimateResourcePreviewSheet');
            if (previewSheet) {
                previewSheet.addEventListener('hidden.bs.offcanvas', () => {
                    this.resetMediaElements(previewSheet);
                    if (this.previewDocViewer) {
                        try { this.previewDocViewer.destroy(); } catch (err) {}
                        this.previewDocViewer = null;
                    }
                    if (this.contextDocViewer) {
                        try { this.contextDocViewer.destroy(); } catch (err) {}
                        this.contextDocViewer = null;
                    }
                    if (this.lastPreviewTriggerEl && typeof this.lastPreviewTriggerEl.focus === 'function') {
                        this.lastPreviewTriggerEl.focus();
                        this.lastPreviewTriggerEl = null;
                    }
                });
            }

            // Modal model selection
            if (this.modalModelsContainer) {
                this.modalModelsContainer.addEventListener('click', (e) => {
                    const btn = e.target.closest('.pwanimate-modal-select-btn');
                    if (btn && !btn.classList.contains('disabled')) {
                        e.preventDefault();
                        const provider = btn.dataset.provider || '';
                        const model = btn.dataset.model || '';
                        const display = btn.dataset.display || 'Auto';
                        const providerLabel = btn.dataset.providerLabel || '';
                        this.selectModel(provider, model, display, providerLabel);

                        // Dismiss modal
                        if (this.quotaModal) {
                            if (window.bootstrap && typeof window.bootstrap.Modal?.getInstance === 'function') {
                                const instance = window.bootstrap.Modal.getInstance(this.quotaModal);
                                if (instance) instance.hide();
                            } else {
                                const closeBtn = this.quotaModal.querySelector('[data-bs-dismiss="modal"]');
                                if (closeBtn) closeBtn.click();
                            }
                        }
                    }
                });
            }

            // Refresh quota button
            if (this.refreshQuotaBtn) {
                this.refreshQuotaBtn.addEventListener('click', () => {
                    const icon = this.refreshQuotaBtn.querySelector('i');
                    if (icon) icon.classList.add('pwanimate-spin');
                    this.fetchQuotaStatus().finally(() => {
                        setTimeout(() => {
                            if (icon) icon.classList.remove('pwanimate-spin');
                        }, 450);
                    });
                });
            }

            // Quota modal on show
            if (this.quotaModal) {
                this.quotaModal.addEventListener('show.bs.modal', () => {
                    this.fetchQuotaStatus();
                });
            }
        }

        initVoiceInput() {
            if (!this.voiceBtn || !this.input) return;

            if (this.voiceStopBtn) this.voiceStopBtn.addEventListener('click', () => this.stopVoiceCapture());
            if (this.voiceSendBtn) this.voiceSendBtn.addEventListener('click', () => this.stopVoiceCapture(true));
            if (this.voiceCancelBtn) this.voiceCancelBtn.addEventListener('click', () => this.cancelVoiceCapture());

            const nativeBridge = window.AndroidBridge || window.PwaninetBridge;
            if (nativeBridge && typeof nativeBridge.startSpeechRecognition === 'function'
                    && typeof nativeBridge.stopSpeechRecognition === 'function') {
                this.nativeSpeechBridge = nativeBridge;
                this._onNativeSpeechEvent = (event) => {
                    if (this.voiceCancelled) return;
                    const detail = event.detail || {};
                    if (detail.error) {
                        const messages = {
                            permission: 'Microphone access was denied. Allow microphone access in Android app settings.',
                            unavailable: 'Speech recognition is not available on this device.',
                            audio: 'The microphone could not be started. Check your microphone and try again.',
                            network: 'Android’s speech service could not connect. Please try again.',
                            'no-speech': 'No speech was detected. Tap the microphone and try again.',
                            busy: 'Speech recognition is busy. Please try again in a moment.',
                            server: 'Android’s speech service encountered an error. Please try again.',
                            'start-failed': 'Could not start the microphone. Please try again.',
                        };
                        const message = messages[detail.error] || 'Voice input failed. Please try again.';
                        this.voiceErrorMessage = message;
                        if (detail.listening) {
                            this.setVoiceStatus(detail.error === 'no-speech' ? 'Listening for speech' : `${message} Retrying`, detail.error !== 'no-speech');
                        } else {
                            this.setVoiceListening(false);
                            this.setVoiceStatus(message, true);
                            this.finishVoiceCapture();
                        }
                        return;
                    }
                    if (detail.final) {
                        if (detail.text) {
                            this.voiceFinalTranscript = [this.voiceFinalTranscript, detail.text.trim()].filter(Boolean).join(' ');
                        }
                        if (!detail.listening) {
                            this.setVoiceListening(false);
                            this.finishVoiceCapture();
                        } else this.setVoiceStatus('Recording voice message');
                    }
                    if (typeof detail.level === 'number') this.setVoiceWaveformLevel(detail.level);
                };
                window.addEventListener('pwaninet:native-speech', this._onNativeSpeechEvent);
                this.voiceBtn.addEventListener('click', () => {
                    this.voiceFinalTranscript = '';
                    this.voiceErrorMessage = '';
                    this.voiceCancelled = false;
                    this.voiceSelection = {
                        start: this.input.selectionStart ?? this.input.value.length,
                        end: this.input.selectionEnd ?? this.input.value.length,
                    };
                    this.setVoiceListening(true);
                    this.setVoiceStatus('Recording voice message');
                    try {
                        nativeBridge.startSpeechRecognition(document.documentElement.lang === 'sw' ? 'sw-KE' : 'en-US');
                    } catch (error) {
                        this.setVoiceListening(false);
                        this.setVoiceStatus('Could not start the microphone. Please try again.', true);
                    }
                });
                return;
            }

            const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!Recognition) {
                this.voiceBtn.disabled = true;
                this.voiceBtn.title = 'Speech input is not supported in this browser.';
                this.voiceBtn.setAttribute('aria-label', this.voiceBtn.title);
                this.setVoiceStatus('Voice input is not available in this browser. You can still type.', true);
                return;
            }

            const recognition = new Recognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.lang = document.documentElement.lang === 'sw' ? 'sw-KE' : 'en-US';
            this.voiceRecognition = recognition;

            this.voiceBtn.addEventListener('click', () => {
                this.voiceFinalTranscript = '';
                this.voiceErrorMessage = '';
                this.voiceCancelled = false;
                this.voiceSelection = {
                    start: this.input.selectionStart ?? this.input.value.length,
                    end: this.input.selectionEnd ?? this.input.value.length,
                };

                try {
                    recognition.start();
                    this.setVoiceListening(true);
                    this.setVoiceStatus('Recording voice message');
                    this.startVoiceLevelMeter();
                } catch (error) {
                    this.setVoiceListening(false);
                    this.setVoiceStatus('Could not start the microphone. Please try again.', true);
                }
            });

            recognition.onstart = () => {
                this.setVoiceListening(true);
                this.setVoiceStatus('Recording voice message');
            };

            recognition.onresult = (event) => {
                let interimText = '';
                for (let index = event.resultIndex; index < event.results.length; index += 1) {
                    const result = event.results[index];
                    const text = result[0] && result[0].transcript ? result[0].transcript.trim() : '';
                    if (!text) continue;
                    if (result.isFinal) {
                        this.voiceFinalTranscript = [this.voiceFinalTranscript, text].filter(Boolean).join(' ');
                    } else interimText += `${text} `;
                }
                if (interimText.trim()) this.setVoiceStatus('Recording voice message');
            };

            recognition.onerror = (event) => {
                if (this.voiceCancelled) return;
                const messages = {
                    'no-speech': 'No speech was detected. Tap the microphone and try again.',
                    'not-allowed': 'Microphone access was blocked. Allow microphone access in your browser settings.',
                    'service-not-allowed': 'The browser speech service is unavailable or not allowed.',
                    'audio-capture': 'No microphone was found on this device.',
                    network: 'The browser speech service could not connect. Please try again.',
                    aborted: 'Voice input was stopped.',
                };
                this.voiceErrorMessage = messages[event.error] || 'Voice input failed. Please try again.';
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    this.voiceStopping = true;
                    this.setVoiceListening(false);
                }
                this.setVoiceStatus(event.error === 'no-speech' && this.voiceListening ? 'Recording voice message' : this.voiceErrorMessage, event.error !== 'aborted');
            };

            recognition.onend = () => {
                if (this.voiceCancelled) {
                    this.voiceCancelled = false;
                    return;
                }
                if (this.voiceListening) {
                    window.setTimeout(() => {
                        if (!this.voiceListening || this.isGenerating) return;
                        try { recognition.start(); } catch (error) {
                            this.setVoiceListening(false);
                            this.finishVoiceCapture();
                            this.setVoiceStatus('Voice recognition stopped. Review your draft and tap the mic to continue.', true);
                        }
                    }, 250);
                    return;
                }
                this.finishVoiceCapture();
            };
        }

        setVoiceListening(isListening) {
            this.voiceListening = isListening;
            if (this.input) this.input.disabled = isListening || this.voiceStopping || this.isGenerating;
            if (this.composerForm) this.composerForm.classList.toggle('is-voice-recording', isListening || this.voiceStopping);
            if (this.voiceCapture) {
                this.voiceCapture.classList.toggle('is-listening', isListening);
                this.voiceCapture.classList.toggle('is-stopping', this.voiceStopping);
                this.voiceCapture.classList.toggle('d-none', !isListening && !this.voiceStopping);
            }
            if (this.voiceStopBtn) this.voiceStopBtn.disabled = this.voiceStopping || this.isGenerating;
            if (this.voiceSendBtn) this.voiceSendBtn.disabled = this.voiceStopping || this.isGenerating;
            if (!this.voiceBtn) return;
            this.voiceBtn.disabled = this.isGenerating || this.voiceStopping || (!this.voiceRecognition && !this.nativeSpeechBridge);
            this.voiceBtn.classList.toggle('is-listening', isListening);
            this.voiceBtn.setAttribute('aria-pressed', String(isListening));
            this.voiceBtn.setAttribute('aria-label', isListening ? 'Stop voice input' : 'Dictate a message');
            this.voiceBtn.title = isListening ? 'Stop voice input' : 'Dictate a message';
            this.updateSendButtonState();
        }

        setVoiceStatus(message, isError = false) {
            if (!this.voiceStatus) return;
            this.voiceStatus.textContent = message;
            this.voiceStatus.classList.toggle('d-none', !message);
            this.voiceStatus.classList.toggle('is-error', Boolean(isError));
            if (this.voiceFeedback) {
                const showFeedback = Boolean(message) && !this.voiceListening && !this.voiceStopping;
                this.voiceFeedback.textContent = message;
                this.voiceFeedback.classList.toggle('d-none', !showFeedback);
                this.voiceFeedback.classList.toggle('is-error', Boolean(isError));
            }
        }

        finishVoiceCapture() {
            const transcript = (this.voiceFinalTranscript || '').trim();
            const sendAfterTranscription = this.voiceSendAfterTranscription && Boolean(transcript);
            if (transcript) {
                this.insertVoiceTranscript(transcript.replace(/\s+([,.;?!])/g, '$1'));
                this.setVoiceStatus(sendAfterTranscription ? 'Sending transcribed message' : 'Speech added to your draft. Review or edit it before sending.');
            } else if (!this.voiceErrorMessage) {
                this.setVoiceStatus('No speech was captured. Tap the microphone and try again.', true);
            }
            this.voiceFinalTranscript = '';
            this.voiceStopping = false;
            this.voiceSendAfterTranscription = false;
            this.stopVoiceLevelMeter();
            this.setVoiceListening(false);
            this.setVoiceTranscribing(false);
            if (this.voiceStatus) {
                this.setVoiceStatus(this.voiceStatus.textContent, this.voiceStatus.classList.contains('is-error'));
            }
            if (this.input) this.input.disabled = this.isGenerating;
            if (this.voiceBtn) this.voiceBtn.disabled = this.isGenerating || (!this.voiceRecognition && !this.nativeSpeechBridge);
            this.updateSendButtonState();
            if (sendAfterTranscription) this.handleSend();
        }

        stopVoiceCapture(sendAfterTranscription = false) {
            if (!this.voiceListening || this.voiceStopping) return;
            this.voiceErrorMessage = '';
            this.voiceStopping = true;
            this.voiceSendAfterTranscription = sendAfterTranscription;
            this.setVoiceListening(false);
            this.setVoiceTranscribing(true, sendAfterTranscription);
            this.setVoiceStatus(sendAfterTranscription ? 'Transcribing voice message before sending' : 'Transcribing voice message');
            if (this.nativeSpeechBridge) this.nativeSpeechBridge.stopSpeechRecognition();
            else if (this.voiceRecognition) this.voiceRecognition.stop();
        }

        setVoiceTranscribing(isLoading, sending = false) {
            [this.voiceStopBtn, this.voiceSendBtn].forEach((button) => {
                if (!button) return;
                const isActive = isLoading && ((sending && button === this.voiceSendBtn) || (!sending && button === this.voiceStopBtn));
                button.classList.toggle('is-loading', isActive);
                button.disabled = isLoading || this.isGenerating;
            });
        }

        cancelVoiceCapture() {
            if (!this.voiceListening && !this.voiceStopping) return;
            this.voiceCancelled = true;
            this.voiceListening = false;
            this.voiceStopping = false;
            this.voiceSendAfterTranscription = false;
            this.voiceFinalTranscript = '';
            this.voiceErrorMessage = '';
            if (this.nativeSpeechBridge) {
                if (typeof this.nativeSpeechBridge.cancelSpeechRecognition === 'function') this.nativeSpeechBridge.cancelSpeechRecognition();
                else this.nativeSpeechBridge.stopSpeechRecognition();
            }
            if (this.voiceRecognition) {
                try { this.voiceRecognition.abort(); } catch (error) {}
            }
            this.setVoiceListening(false);
            this.setVoiceTranscribing(false);
            this.setVoiceStatus('Voice recording cancelled');
            this.stopVoiceLevelMeter();
            if (this.voiceCapture) this.voiceCapture.classList.add('d-none');
        }

        async startVoiceLevelMeter() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || this.voiceMediaStream) return;
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                if (!this.voiceListening) {
                    stream.getTracks().forEach(track => track.stop());
                    return;
                }
                this.voiceMediaStream = stream;
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                if (!AudioContextClass) return;
                this.voiceAudioContext = new AudioContextClass();
                this.voiceAnalyser = this.voiceAudioContext.createAnalyser();
                this.voiceAnalyser.fftSize = 256;
                this.voiceAudioContext.createMediaStreamSource(stream).connect(this.voiceAnalyser);
                const samples = new Uint8Array(this.voiceAnalyser.fftSize);
                const draw = () => {
                    if (!this.voiceAnalyser) return;
                    this.voiceAnalyser.getByteTimeDomainData(samples);
                    let sum = 0;
                    for (let i = 0; i < samples.length; i += 1) {
                        const amplitude = (samples[i] - 128) / 128;
                        sum += amplitude * amplitude;
                    }
                    this.setVoiceWaveformLevel(Math.min(1, Math.sqrt(sum / samples.length) * 4));
                    this.voiceAnimationFrame = window.requestAnimationFrame(draw);
                };
                draw();
            } catch (error) {
                // Speech recognition still works if a browser does not grant a separate visualizer stream.
            }
        }

        setVoiceWaveformLevel(level) {
            if (!this.voiceCapture || !this.voiceWaveformBars.length) return;
            const normalized = Math.max(0, Math.min(1, Number(level) || 0));
            this.voiceCapture.classList.toggle('is-speaking', normalized > 0.08);
            this.voiceWaveformBars.forEach((bar, index) => {
                const centerBias = 0.45 + 0.55 * Math.sin(Math.PI * (index + 1) / (this.voiceWaveformBars.length + 1));
                const variation = 0.35 + Math.random() * 0.65;
                const height = Math.max(3, 3 + normalized * 31 * centerBias * variation);
                bar.style.height = `${height}px`;
            });
        }

        stopVoiceLevelMeter() {
            if (this.voiceAnimationFrame) window.cancelAnimationFrame(this.voiceAnimationFrame);
            this.voiceAnimationFrame = null;
            this.voiceAnalyser = null;
            if (this.voiceMediaStream) this.voiceMediaStream.getTracks().forEach(track => track.stop());
            this.voiceMediaStream = null;
            if (this.voiceAudioContext) {
                try { this.voiceAudioContext.close(); } catch (error) {}
            }
            this.voiceAudioContext = null;
            this.setVoiceWaveformLevel(0);
        }

        insertVoiceTranscript(transcript) {
            const value = this.input.value;
            const start = this.voiceSelection ? this.voiceSelection.start : value.length;
            const end = this.voiceSelection ? this.voiceSelection.end : value.length;
            const before = value.slice(0, start);
            const after = value.slice(end);
            const needsSpaceBefore = Boolean(before && !/\s$/.test(before));
            const needsSpaceAfter = Boolean(after && !/^\s/.test(after));
            const spokenText = transcript.trim();
            const insertion = `${needsSpaceBefore ? ' ' : ''}${spokenText}${needsSpaceAfter ? ' ' : ''}`;
            const cursor = before.length + insertion.length;

            this.input.value = `${before}${insertion}${after}`;
            this.input.setSelectionRange(cursor, cursor);
            this.input.dispatchEvent(new Event('input', { bubbles: true }));
            this.input.focus({ preventScroll: true });
        }

        scheduleTextareaResize() {
            if (this.resizeFrame) {
                cancelAnimationFrame(this.resizeFrame);
            }
            this.resizeFrame = requestAnimationFrame(() => {
                this.resizeTextarea();
                this.resizeFrame = null;
            });
        }

        resizeTextarea() {
            if (!this.input) return;
            this.input.style.height = 'auto';
            const newHeight = Math.min(this.input.scrollHeight, 160);
            this.input.style.height = `${newHeight}px`;
        }

        resetTextareaHeight() {
            if (this.resizeFrame) {
                cancelAnimationFrame(this.resizeFrame);
                this.resizeFrame = null;
            }
            if (this.input) {
                this.input.style.height = 'auto';
            }
        }

        updateLocationBadge(prefix, page, totalPages = null) {
            let container = null;
            if (prefix === 'desktopPreview') {
                container = document.getElementById('desktopPreviewActive');
            } else if (prefix === 'previewSheet') {
                container = document.getElementById('pwanimateResourcePreviewSheet');
            } else if (prefix === 'desktopContext') {
                container = document.getElementById('desktopContextSurfaceCard');
            } else if (prefix === 'mobileContext') {
                container = document.getElementById('mobileContextActive');
            }
            if (!container) container = document;

            const locBadge = container.querySelector(`#${prefix}LocationBadge`);
            const locText = container.querySelector(`#${prefix}LocationText`);
            if (locBadge && locText) {
                if (page) {
                    locBadge.classList.remove('d-none');
                    locText.textContent = totalPages ? `p. ${page} / ${totalPages}` : `p. ${page}`;
                } else {
                    locBadge.classList.add('d-none');
                }
            }
        }

        static normalizeResource(url, title, meta = {}) {
            meta = meta || {};
            const rawUrl = url || meta.mediaUrl || meta.media_url || meta.url || '#';
            const cleanUrl = typeof rawUrl === 'string' ? rawUrl : '#';

            // Extract authoritative IDs
            let documentShareId = meta.documentShareId || meta.document_share_id || '';
            if (!documentShareId) {
                const docMatch = cleanUrl.match(/\/documents\/document\/([0-9a-fA-F-]+)/i);
                if (docMatch) documentShareId = docMatch[1];
            }

            const documentId = meta.documentId || meta.document_id || documentShareId || '';
            const documentVersionId = meta.documentVersionId || meta.document_version_id || meta.versionId || '';
            const fileId = meta.fileId || meta.file_id || '';

            let postId = meta.postId || meta.post_id || '';
            if (!postId) {
                const postMatch = cleanUrl.match(/\/(?:posts\/)?post\/([0-9a-fA-F-]+)/i);
                if (postMatch) postId = postMatch[1];
            }

            // Media URLs
            const mediaUrl = meta.mediaUrl || meta.media_url || '';
            const hlsUrl = meta.hlsUrl || meta.hls_url || '';
            const thumbnailUrl = meta.thumbnailUrl || meta.thumbnail_url || meta.avatar_url || meta.profile_photo_url || '';

            // File type derivation & normalization
            let fileType = (meta.fileType || meta.file_type || meta.file_extension || meta.extension || '').toLowerCase().trim();
            if (fileType.startsWith('.')) fileType = fileType.substring(1);
            if (!fileType) {
                const candidate = (mediaUrl || cleanUrl || '').split('?')[0].split('#')[0];
                const extMatch = candidate.match(/\.([a-zA-Z0-9]+)$/);
                if (extMatch && extMatch[1].length <= 5) fileType = extMatch[1].toLowerCase();
            }

            // Classification
            const resourceType = String(meta.resourceType || meta.resource_type || meta.type || meta.previewType || meta.preview_type || '').toLowerCase();
            const sourceType = String(meta.sourceType || meta.source_type || meta.source || '').toLowerCase();
            const isProfile = resourceType === 'profile' || resourceType === 'user' ||
                sourceType === 'user' || sourceType === 'profile';
            const isPost = meta.sourceType === 'post' || meta.source_type === 'post' ||
                meta.resourceType === 'post' || meta.resource_type === 'post' ||
                cleanUrl.includes('/post/') || cleanUrl.includes('/posts/');
            const isVideo = meta.resourceType === 'video' || meta.resource_type === 'video' || Boolean(hlsUrl) ||
                /\.(mp4|webm|ogg|m3u8)(\?|#|$)/i.test(mediaUrl || cleanUrl);

            const isImage = !isPost && !isProfile && !isVideo && (meta.resourceType === 'image' || meta.resource_type === 'image' ||
                /\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)/i.test(mediaUrl || cleanUrl) ||
                ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fileType));

            const isDoc = !isVideo && !isImage && !isPost && !isProfile && (meta.resourceType === 'document' || meta.resource_type === 'document' ||
                meta.sourceType === 'document' || meta.source_type === 'document' ||
                Boolean(documentShareId) || cleanUrl.includes('/documents/') ||
                ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'txt', 'md', 'csv', 'log'].includes(fileType));

            let previewType = 'document';
            if (isProfile) previewType = 'profile';
            else if (isVideo) previewType = 'video';
            else if (isPost) previewType = 'post';
            else if (isImage) previewType = 'image';
            else if (isDoc) previewType = 'document';

            // Deterministic Page Number Resolution Order:
            // 1. Explicit structured metadata (highest priority)
            // 2. URL query parameter or hash (?page=12, #page=12)
            // 3. Fallback: parse citation text ("Page 12", "p. 12")
            let pageNumber = null;
            const rawPage = (meta.pageNumber !== undefined && meta.pageNumber !== null && meta.pageNumber !== '') ? meta.pageNumber :
                           ((meta.page_number !== undefined && meta.page_number !== null && meta.page_number !== '') ? meta.page_number : meta.page);
            if (rawPage !== undefined && rawPage !== null && String(rawPage).trim() !== '' && !isNaN(rawPage)) {
                pageNumber = Math.max(1, parseInt(rawPage, 10));
            } else {
                const queryMatch = cleanUrl.match(/[?&](?:page|p)=(\d+)/i);
                const hashMatch = cleanUrl.match(/#(?:page=?|p=?)(\d+)/i);
                if (queryMatch) {
                    pageNumber = Math.max(1, parseInt(queryMatch[1], 10));
                } else if (hashMatch) {
                    pageNumber = Math.max(1, parseInt(hashMatch[1], 10));
                } else {
                    const citText = meta.citation || meta.description || title || '';
                    const textMatch = citText.match(/\b(?:page|p\.|pp\.)\s*(\d+)\b/i);
                    if (textMatch) {
                        pageNumber = Math.max(1, parseInt(textMatch[1], 10));
                    }
                }
            }

            let category = 'Resource';
            let icon = 'bi-link-45deg';
            let badgeClass = 'bg-secondary-subtle text-secondary-emphasis';
            let primaryText = 'Open Resource';
            let primaryIcon = 'bi-box-arrow-up-right';
            let docIcon = 'bi-file-earmark-text';

            if (previewType === 'video') {
                category = 'Video';
                icon = 'bi-play-circle-fill';
                badgeClass = 'bg-danger-subtle text-danger';
                primaryText = 'Watch Video';
                primaryIcon = 'bi-play-btn-fill';
            } else if (previewType === 'image') {
                category = 'Image';
                icon = 'bi-image-fill';
                badgeClass = 'bg-info-subtle text-info';
                primaryText = 'View Full Image';
                primaryIcon = 'bi-arrows-fullscreen';
            } else if (previewType === 'document') {
                category = 'Document';
                icon = 'bi-file-earmark-pdf-fill';
                badgeClass = 'bg-primary-subtle text-primary';
                primaryText = 'Open Document';
                primaryIcon = 'bi-file-earmark-arrow-up';
                docIcon = 'bi-file-earmark-pdf-fill text-danger';
            } else if (previewType === 'post') {
                category = 'Post';
                icon = 'bi-chat-square-text-fill';
                badgeClass = 'bg-success-subtle text-success';
                primaryText = 'View Post';
                primaryIcon = 'bi-chat-square-text';
                docIcon = 'bi-chat-quote-fill text-success';
            } else if (previewType === 'profile') {
                category = 'Student Profile';
                icon = 'bi-person-vcard-fill';
                badgeClass = 'bg-primary-subtle text-primary';
                primaryText = 'Open Profile';
                primaryIcon = 'bi-person-lines-fill';
                docIcon = 'bi-person-circle text-primary';
            }

            let subtitle = category;
            if (meta.author) {
                subtitle = `${category} · By ${meta.author}`;
            } else if (meta.citation) {
                subtitle = `${category} · ${meta.citation}`;
            } else {
                subtitle = `${category} · PwaniNet Repository`;
            }

            const targetSrc = previewType === 'video'
                ? (hlsUrl || mediaUrl || cleanUrl)
                : (mediaUrl || cleanUrl);

            const cleanTitle = title || meta.title || (previewType === 'document' ? 'Document' : (previewType === 'post' ? 'Post' : 'Resource'));
            const person = meta.person || meta.profile || (isProfile ? meta : {});
            const profileUsername = meta.username || person.username ||
                ((cleanUrl.match(/\/users\/user\/([^/?#]+)/i) || [])[1] || '');
            const profileUrl = meta.profileUrl || meta.profile_url || person.profile_url ||
                (profileUsername ? `/users/user/${encodeURIComponent(profileUsername)}/` : cleanUrl);
            const profileCardUrl = meta.profileCardUrl || meta.profile_card_url || person.profile_card_url ||
                `${profileUrl.replace(/\/$/, '')}/pwanimate-card/`;
            const description = meta.description || meta.content || meta.snippet || meta.citation ||
                (previewType === 'document' ? 'Official course or academic document from PwaniNet repository.' :
                (previewType === 'post' ? 'Discussion post on PwaniNet.' :
                (previewType === 'profile' ? [person.headline, person.academic_level, person.programme_name, person.bio].filter(Boolean).join('\n') : 'Resource referenced in this conversation.')));

            return {
                id: documentShareId || postId || person.id || person.username || cleanUrl,
                type: previewType,
                category: category,
                title: cleanTitle,
                subtitle: subtitle,
                url: cleanUrl,
                targetSrc: targetSrc,
                mediaUrl: mediaUrl,
                hlsUrl: hlsUrl,
                thumbnailUrl: thumbnailUrl,
                previewType: previewType,
                documentId: documentId,
                documentShareId: documentShareId,
                documentVersionId: documentVersionId,
                fileId: fileId,
                fileType: fileType,
                pageNumber: pageNumber,
                description: description,
                author: meta.author || '',
                citation: meta.citation || '',
                postId: postId,
                username: profileUsername,
                person: person,
                profileUrl: profileUrl,
                profileCardUrl: profileCardUrl,
                icon: icon,
                badgeClass: badgeClass,
                primaryText: primaryText,
                primaryIcon: primaryIcon,
                docIcon: docIcon,
                rawMeta: meta
            };
        }

        normalizeResource(url, title, meta = {}) {
            return PwanimateChat.normalizeResource(url, title, meta);
        }

        previewResource(url, title, meta = {}) {
            this.lastPreviewTriggerEl = meta.triggerEl || null;
            const resource = this.normalizeResource(url, title, meta);

            const isDesktop = (window.innerWidth >= 1200);
            const prefix = isDesktop ? 'desktopPreview' : 'previewSheet';

            // Check if same document is already mounted in Preview
            const isSameDoc = Boolean(
                this.previewDocViewer && this.previewResourceState &&
                this.previewResourceState.previewType === 'document' && resource.previewType === 'document' &&
                ((resource.documentShareId && this.previewResourceState.documentShareId === resource.documentShareId) ||
                 (resource.documentId && this.previewResourceState.documentId === resource.documentId) ||
                 (resource.mediaUrl && this.previewResourceState.mediaUrl === resource.mediaUrl && resource.mediaUrl !== ''))
            );

            this.activeResourceDetails = resource;
            this.previewResourceState = resource;

            // Switch workspace tab to Preview (non-destructive)
            this.switchWorkspaceTab('preview');

            if (isDesktop) {
                this.openContextRail();
                const emptyState = document.getElementById('desktopPreviewEmpty');
                const activeState = document.getElementById('desktopPreviewActive');
                if (emptyState && activeState) {
                    emptyState.classList.add('d-none');
                    activeState.classList.remove('d-none');
                    activeState.classList.add('d-flex');
                }
            } else {
                const sheetEl = document.getElementById('pwanimateResourcePreviewSheet');
                if (sheetEl && window.bootstrap) {
                    let offcanvas = bootstrap.Offcanvas.getInstance(sheetEl);
                    if (!offcanvas) offcanvas = new bootstrap.Offcanvas(sheetEl);
                    offcanvas.show();
                }
            }

            if (isSameDoc) {
                // Same document already mounted: navigate to page without rebuilding viewer
                if (resource.pageNumber && typeof this.previewDocViewer.goToPage === 'function') {
                    this.previewDocViewer.goToPage(resource.pageNumber);
                }
                this.updateLocationBadge(prefix, resource.pageNumber, this.previewDocViewer.getTotalPages());
            } else {
                // Render or update surface for resource
                this.renderSurface(prefix, resource, false);
            }

            this.updateAddToContextButtons();
        }

        switchWorkspaceTab(tabName) {
            const targetTab = (tabName === 'context') ? 'context' : 'preview';
            this.activeWorkspaceTab = targetTab;

            // Desktop Tab Buttons & Panes
            const deskPrevBtn = document.getElementById('desktopTabPreviewBtn');
            const deskCtxBtn = document.getElementById('desktopTabContextBtn');
            const deskPrevPane = document.getElementById('desktopTabPreviewPane');
            const deskCtxPane = document.getElementById('desktopTabContextPane');

            // Mobile Tab Buttons & Panes
            const mobPrevBtn = document.getElementById('mobileTabPreviewBtn');
            const mobCtxBtn = document.getElementById('mobileTabContextBtn');
            const mobPrevPane = document.getElementById('mobileTabPreviewPane');
            const mobCtxPane = document.getElementById('mobileTabContextPane');

            if (targetTab === 'preview') {
                if (deskPrevBtn) { deskPrevBtn.classList.add('active'); deskPrevBtn.setAttribute('aria-selected', 'true'); }
                if (deskCtxBtn) { deskCtxBtn.classList.remove('active'); deskCtxBtn.setAttribute('aria-selected', 'false'); }
                if (deskPrevPane) { deskPrevPane.classList.add('show', 'active'); }
                if (deskCtxPane) { deskCtxPane.classList.remove('show', 'active'); }

                if (mobPrevBtn) { mobPrevBtn.classList.add('active'); mobPrevBtn.setAttribute('aria-selected', 'true'); }
                if (mobCtxBtn) { mobCtxBtn.classList.remove('active'); mobCtxBtn.setAttribute('aria-selected', 'false'); }
                if (mobPrevPane) { mobPrevPane.classList.add('show', 'active'); }
                if (mobCtxPane) { mobCtxPane.classList.remove('show', 'active'); }

                if (this.previewDocViewer && typeof this.previewDocViewer.handleResize === 'function') {
                    requestAnimationFrame(() => {
                        if (this.previewDocViewer && typeof this.previewDocViewer.handleResize === 'function') {
                            this.previewDocViewer.handleResize();
                        }
                    });
                }
            } else {
                if (deskPrevBtn) { deskPrevBtn.classList.remove('active'); deskPrevBtn.setAttribute('aria-selected', 'false'); }
                if (deskCtxBtn) { deskCtxBtn.classList.add('active'); deskCtxBtn.setAttribute('aria-selected', 'true'); }
                if (deskPrevPane) { deskPrevPane.classList.remove('show', 'active'); }
                if (deskCtxPane) { deskCtxPane.classList.add('show', 'active'); }

                if (mobPrevBtn) { mobPrevBtn.classList.remove('active'); mobPrevBtn.setAttribute('aria-selected', 'false'); }
                if (mobCtxBtn) { mobCtxBtn.classList.add('active'); mobCtxBtn.setAttribute('aria-selected', 'true'); }
                if (mobPrevPane) { mobPrevPane.classList.remove('show', 'active'); }
                if (mobCtxPane) { mobCtxPane.classList.add('show', 'active'); }

                if (this.contextResources.length > 0 && this.activeContextIndex < 0) {
                    this.activeContextIndex = 0;
                }
                this.syncContextView();

                if (this.contextDocViewer && typeof this.contextDocViewer.handleResize === 'function') {
                    requestAnimationFrame(() => {
                        if (this.contextDocViewer && typeof this.contextDocViewer.handleResize === 'function') {
                            this.contextDocViewer.handleResize();
                        }
                    });
                }
            }
        }


        addResourceToContext(resource) {
            if (!resource) return;

            // Deduplicate
            const existingIndex = this.contextResources.findIndex(item =>
                (resource.documentId && item.documentId === resource.documentId) ||
                (resource.mediaUrl && item.mediaUrl === resource.mediaUrl) ||
                (resource.url && item.url === resource.url && item.title === resource.title)
            );

            if (existingIndex >= 0) {
                this.activeContextIndex = existingIndex;
            } else {
                const contextItem = Object.assign({}, resource, {
                    pageNumber: resource.pageNumber || 1
                });
                this.contextResources.push(contextItem);
                this.activeContextIndex = this.contextResources.length - 1;
            }

            this.updateContextCountBadges();
            this.updateAddToContextButtons();
            this.syncContextView();
            this.switchWorkspaceTab('context');
        }

        getContextResourcesForRequest() {
            const resources = [...this.contextResources];
            const preview = this.previewResourceState;
            if (!preview) return resources;

            const alreadyIncluded = resources.some(item =>
                (preview.documentId && item.documentId === preview.documentId) ||
                (preview.documentShareId && item.documentShareId === preview.documentShareId) ||
                (preview.mediaUrl && item.mediaUrl === preview.mediaUrl) ||
                (preview.url && item.url === preview.url)
            );
            if (!alreadyIncluded) resources.push(preview);
            return resources;
        }

        removeResourceFromContext(index) {
            if (index < 0 || index >= this.contextResources.length) return;

            if (this.contextDocViewer && index === this.activeContextIndex) {
                try { this.contextDocViewer.destroy(); } catch (e) {}
                this.contextDocViewer = null;
            }

            this.contextResources.splice(index, 1);

            if (this.contextResources.length === 0) {
                this.activeContextIndex = -1;
            } else if (index < this.activeContextIndex) {
                this.activeContextIndex -= 1;
            } else if (this.activeContextIndex >= this.contextResources.length) {
                this.activeContextIndex = this.contextResources.length - 1;
            }

            this.updateContextCountBadges();
            this.updateAddToContextButtons();
            this.syncContextView();
        }

        selectContextResource(index) {
            if (index < 0 || index >= this.contextResources.length) return;
            if (this.activeContextIndex === index) return;

            this.activeContextIndex = index;
            this.syncContextView();
        }

        updateContextCountBadges() {
            const countStr = this.contextResources.length.toString();
            const deskBadge = document.getElementById('desktopContextCountBadge');
            const mobBadge = document.getElementById('mobileContextCountBadge');
            const mobileComposerBadge = document.getElementById('pwanimateMobileContextSheetCount');
            if (deskBadge) deskBadge.textContent = countStr;
            if (mobBadge) mobBadge.textContent = countStr;
            if (mobileComposerBadge) {
                mobileComposerBadge.textContent = countStr;
                mobileComposerBadge.classList.toggle('d-none', this.contextResources.length === 0);
            }
        }

        updateAddToContextButtons() {
            const isAdded = Boolean(this.previewResourceState && this.contextResources.some(item =>
                (this.previewResourceState.documentId && item.documentId === this.previewResourceState.documentId) ||
                (this.previewResourceState.mediaUrl && item.mediaUrl === this.previewResourceState.mediaUrl) ||
                (this.previewResourceState.url && item.url === this.previewResourceState.url && item.title === this.previewResourceState.title)
            ));

            const deskBtn = document.getElementById('desktopPreviewAddToContextBtn');
            const mobBtn = document.getElementById('previewSheetAddToContextBtn');

            if (deskBtn) {
                if (isAdded) {
                    deskBtn.className = 'btn btn-sm btn-outline-success rounded-pill px-2 py-0 d-inline-flex align-items-center gap-1 disabled';
                    deskBtn.innerHTML = '<i class="bi bi-check-lg"></i> <span>In Context</span>';
                } else {
                    deskBtn.className = 'btn btn-sm btn-primary rounded-pill px-2 py-0 d-inline-flex align-items-center gap-1';
                    deskBtn.innerHTML = '<i class="bi bi-plus-lg"></i> <span id="desktopPreviewAddToContextText">+ Add to Context</span>';
                }
            }

            if (mobBtn) {
                if (isAdded) {
                    mobBtn.className = 'btn btn-sm btn-outline-success rounded-pill px-2 py-0 d-inline-flex align-items-center gap-1 disabled';
                    mobBtn.innerHTML = '<i class="bi bi-check-lg"></i> <span>In Context</span>';
                } else {
                    mobBtn.className = 'btn btn-sm btn-primary rounded-pill px-2 py-0 d-inline-flex align-items-center gap-1';
                    mobBtn.innerHTML = '<i class="bi bi-plus-lg"></i> <span id="previewSheetAddToContextText">+ Add to Context</span>';
                }
            }
        }

        syncContextView() {
            const deskEmpty = document.getElementById('desktopContextEmpty');
            const deskActive = document.getElementById('desktopContextActive');
            const mobEmpty = document.getElementById('mobileContextEmpty');
            const mobActive = document.getElementById('mobileContextActive');

            if (this.contextResources.length === 0) {
                if (deskEmpty) deskEmpty.classList.remove('d-none');
                if (deskActive) { deskActive.classList.remove('d-flex'); deskActive.classList.add('d-none'); }
                if (mobEmpty) mobEmpty.classList.remove('d-none');
                if (mobActive) { mobActive.classList.remove('d-flex'); mobActive.classList.add('d-none'); }

                if (this.contextDocViewer) {
                    try { this.contextDocViewer.destroy(); } catch (e) {}
                    this.contextDocViewer = null;
                }
                return;
            }

            if (deskEmpty) deskEmpty.classList.add('d-none');
            if (deskActive) { deskActive.classList.remove('d-none'); deskActive.classList.add('d-flex'); }
            if (mobEmpty) mobEmpty.classList.add('d-none');
            if (mobActive) { mobActive.classList.remove('d-none'); mobActive.classList.add('d-flex'); }

            const deskChips = document.getElementById('desktopContextChipsList');
            const mobChips = document.getElementById('mobileContextChipsList');

            const chipsHtml = this.contextResources.map((res, idx) => {
                const isActive = idx === this.activeContextIndex;
                const safeTitle = escapeHtml(res.title || 'Resource');
                const safeIcon = escapeHtml(res.icon || 'bi-file-earmark');
                return `
                    <div class="pwanimate-context-chip ${isActive ? 'active' : ''}" data-index="${idx}" role="button" tabindex="0">
                        <i class="bi ${safeIcon} me-1"></i>
                        <span class="pwanimate-chip-title" title="${safeTitle}">${safeTitle}</span>
                        <button type="button" class="pwanimate-chip-remove" data-index="${idx}" aria-label="Remove ${safeTitle}">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                `;
            }).join('');

            if (deskChips) deskChips.innerHTML = chipsHtml;
            if (mobChips) mobChips.innerHTML = chipsHtml;

            const activeResource = this.contextResources[this.activeContextIndex];
            if (activeResource) {
                if (window.innerWidth >= 1200) {
                    this.renderSurface('desktopContext', activeResource, true);
                } else {
                    this.renderSurface('mobileContext', activeResource, true);
                }
            }
        }

        renderSurface(prefix, details, isContext = false) {
            let container = null;
            if (prefix === 'desktopPreview') {
                container = document.getElementById('desktopPreviewActive');
            } else if (prefix === 'previewSheet') {
                container = document.getElementById('pwanimateResourcePreviewSheet');
            } else if (prefix === 'desktopContext') {
                container = document.getElementById('desktopContextSurfaceCard');
            } else if (prefix === 'mobileContext') {
                container = document.getElementById('mobileContextActive');
            }
            if (!container || !details) return;

            container.classList.toggle('pwanimate-profile-mode', details.previewType === 'profile');

            // 1. Header category badge
            const categoryBadge = container.querySelector(`#${prefix}CategoryBadge`);
            const categoryIcon = container.querySelector(`#${prefix}CategoryIcon`);
            const categoryText = container.querySelector(`#${prefix}CategoryText`);
            if (categoryBadge) {
                categoryBadge.className = `pwanimate-preview-badge badge rounded-pill px-2 py-1 ${details.badgeClass}`;
            }
            if (categoryIcon) {
                categoryIcon.className = `bi ${details.icon} me-1`;
            }
            if (categoryText) {
                categoryText.textContent = details.category;
            }

            // Location badge (e.g. p. 1)
            const locBadge = container.querySelector(`#${prefix}LocationBadge`);
            const locText = container.querySelector(`#${prefix}LocationText`);
            if (locBadge && locText) {
                if (details.pageNumber) {
                    locBadge.classList.remove('d-none');
                    locText.textContent = `p. ${details.pageNumber}`;
                } else {
                    locBadge.classList.add('d-none');
                }
            }

            // 2. Body hosts
            const video = container.querySelector(`#${prefix}Video`);
            const imgContainer = container.querySelector(`#${prefix}ImageContainer`);
            const img = container.querySelector(`#${prefix}Image`);
            const docViewer = container.querySelector(`#${prefix}DocViewer`);
            const docContainer = container.querySelector(`#${prefix}DocContainer`);
            const spinner = container.querySelector(`#${prefix}Spinner`);
            const iframe = container.querySelector(`#${prefix}Iframe`);

            // Reset hosts
            if (video) {
                if (video._hlsInstance) {
                    try { video._hlsInstance.destroy(); } catch (e) {}
                    delete video._hlsInstance;
                }
                delete video.dataset.hlsReady;
                video.removeAttribute('data-hls-url');
                video.removeAttribute('data-video-url');
                video.poster = '';
                video.pause();
                video.src = '';
                video.classList.add('d-none');
            }
            if (imgContainer) { imgContainer.classList.add('d-none'); if (img) img.src = ''; }
            if (iframe) { iframe.classList.add('d-none'); iframe.src = ''; }
            if (docContainer) { docContainer.classList.add('d-none'); }
            if (spinner) spinner.classList.add('d-none');

            // Clean up previous doc viewer if present for this pane
            if (isContext && this.contextDocViewer) {
                try { this.contextDocViewer.destroy(); } catch (e) {}
                this.contextDocViewer = null;
            } else if (!isContext && this.previewDocViewer) {
                try { this.previewDocViewer.destroy(); } catch (e) {}
                this.previewDocViewer = null;
            }
            if (docViewer) {
                docViewer.innerHTML = '';
                docViewer.classList.add('d-none');
                docViewer.classList.remove('d-flex');
            }

            const fileType = (details.fileType || this.inferFileType(details.mediaUrl || details.url || '')).toLowerCase();
            const canUseDocViewer = Boolean(
                window.DocumentViewer &&
                docViewer &&
                details.mediaUrl &&
                ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'md', 'txt', 'text', 'csv', 'log'].includes(fileType)
            );

            if (details.previewType === 'video' && video) {
                video.autoplay = true;
                video.playsInline = true;
                video.muted = false;
                if (details.thumbnailUrl) {
                    video.poster = details.thumbnailUrl;
                }
                const hlsStreamUrl = details.hlsUrl || (/\.m3u8/i.test(details.targetSrc) ? details.targetSrc : '');
                const fallbackMp4Url = (!/\.m3u8/i.test(details.targetSrc)) ? details.targetSrc : (details.mediaUrl || '');

                if (hlsStreamUrl) {
                    video.dataset.hlsUrl = hlsStreamUrl;
                    if (fallbackMp4Url && fallbackMp4Url !== hlsStreamUrl) {
                        video.dataset.videoUrl = fallbackMp4Url;
                    }
                    if (typeof window.initHLSForElement === 'function') {
                        window.initHLSForElement(video);
                    } else if (typeof window.Hls !== 'undefined' && window.Hls.isSupported()) {
                        const hls = new window.Hls({
                            startLevel: 0,
                            abrEwmaDefaultEstimate: 400000,
                            capLevelToPlayerSize: true,
                        });
                        hls.loadSource(hlsStreamUrl);
                        hls.attachMedia(video);
                        video._hlsInstance = hls;
                    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                        video.src = hlsStreamUrl;
                    } else if (fallbackMp4Url) {
                        video.src = fallbackMp4Url;
                    }
                } else if (details.targetSrc) {
                    video.src = details.targetSrc;
                }
                video.classList.remove('d-none');
                const tryPlayback = () => {
                    const playback = video.play();
                    if (playback && typeof playback.catch === 'function') {
                        playback.catch((error) => {
                            if (error && error.name === 'NotAllowedError') {
                                video.muted = true;
                                video.play().catch(() => {});
                            }
                        });
                    }
                };
                video.addEventListener('loadeddata', tryPlayback, { once: true });
                tryPlayback();
            } else if (details.previewType === 'image' && imgContainer && img) {
                if (spinner) spinner.classList.remove('d-none');
                img.onload = () => { if (spinner) spinner.classList.add('d-none'); };
                img.onerror = () => { if (spinner) spinner.classList.add('d-none'); };
                img.src = details.targetSrc;
                imgContainer.classList.remove('d-none');
            } else if (canUseDocViewer) {
                docViewer.classList.remove('d-none');
                docViewer.classList.add('d-flex');

                const initialPage = (details.pageNumber && !isNaN(details.pageNumber)) ? parseInt(details.pageNumber, 10) : 1;
                const options = {
                    compact: true,
                    fitContainer: true,
                    initialPage: initialPage,
                    showDownload: true,
                    showFullscreen: true,
                    onPageChange: (page, totalPages) => {
                        details.pageNumber = page;
                        if (locBadge && locText) {
                            locBadge.classList.remove('d-none');
                            locText.textContent = totalPages ? `p. ${page} / ${totalPages}` : `p. ${page}`;
                        }
                    }
                };
                const viewerInstance = new window.DocumentViewer(
                    docViewer,
                    details.mediaUrl,
                    fileType,
                    details.title || 'Document',
                    details.documentId || null,
                    details.documentShareId || null,
                    options
                );
                if (isContext) {
                    this.contextDocViewer = viewerInstance;
                } else {
                    this.previewDocViewer = viewerInstance;
                }
                viewerInstance.initialize().then(() => {
                    if (window.ResizeObserver && !docViewer._resizeObs) {
                        docViewer._resizeObs = new ResizeObserver(() => {
                            if (typeof viewerInstance.handleResize === 'function') {
                                viewerInstance.handleResize();
                            }
                        });
                        docViewer._resizeObs.observe(docViewer);
                    }
                }).catch((err) => {
                    console.warn('[Pwanimate] DocumentViewer initialization failed, falling back to doc card:', err);
                    docViewer.classList.remove('d-flex');
                    docViewer.classList.add('d-none');
                    this.renderDocCard(container, prefix, details);
                });
            } else if (docContainer) {
                this.renderDocCard(container, prefix, details);
            }

            // 3. Footer info
            const titleEl = container.querySelector(`#${prefix}Title`);
            const subtitleEl = container.querySelector(`#${prefix}Subtitle`);
            if (titleEl) titleEl.textContent = details.title;
            if (subtitleEl) subtitleEl.textContent = details.subtitle;

            // Primary action button
            const primaryAction = container.querySelector(`#${prefix}PrimaryAction`);
            const primaryTextEl = container.querySelector(`#${prefix}PrimaryText`);
            const primaryIconEl = container.querySelector(`#${prefix}PrimaryIcon`);
            if (primaryTextEl) primaryTextEl.textContent = details.primaryText;
            if (primaryIconEl) primaryIconEl.className = `bi ${details.primaryIcon} me-1`;

            if (primaryAction) {
                primaryAction.href = details.url;
                const isInternal = details.url.startsWith('/') || (details.url.startsWith('http') && details.url.startsWith(window.location.origin));
                if (isInternal) {
                    primaryAction.removeAttribute('hx-get');
                    primaryAction.removeAttribute('hx-target');
                    primaryAction.removeAttribute('hx-swap');
                    primaryAction.removeAttribute('hx-push-url');
                    primaryAction.setAttribute('data-bypass-htmx', 'true');
                    primaryAction.setAttribute('hx-boost', 'false');
                    primaryAction.removeAttribute('target');
                    primaryAction.onclick = (e) => {
                        if (prefix.startsWith('previewSheet') || prefix.startsWith('mobileContext')) {
                            const sheet = document.getElementById('pwanimateResourcePreviewSheet');
                            if (sheet && window.bootstrap) {
                                const inst = bootstrap.Offcanvas.getInstance(sheet);
                                if (inst) inst.hide();
                            }
                        }
                        window.location.href = details.url;
                    };
                } else {
                    primaryAction.removeAttribute('hx-get');
                    primaryAction.setAttribute('target', '_blank');
                    primaryAction.setAttribute('rel', 'noopener');
                    primaryAction.onclick = null;
                }
            }

            // Secondary action button (original link)
            const origLink = container.querySelector(`#${prefix}OriginalLink`);
            if (origLink) {
                origLink.href = details.url;
                origLink.setAttribute('target', '_blank');
                origLink.setAttribute('rel', 'noopener');
            }

            if (details.previewType === 'profile') {
                this.loadProfilePreviewCard(container, prefix, details);
            }
        }

        async loadProfilePreviewCard(container, prefix, details) {
            const docContainer = container.querySelector(`#${prefix}DocContainer`);
            if (!docContainer) return;
            const profileUrl = details.profileUrl || details.url;
            if (!profileUrl) return;
            const cardUrl = details.profileCardUrl || `${profileUrl.replace(/\/$/, '')}/pwanimate-card/`;
            docContainer.dataset.profileCardUrl = cardUrl;
            docContainer.classList.remove('text-center', 'align-items-center', 'justify-content-center');
            docContainer.classList.add('align-items-stretch', 'justify-content-start', 'p-2');
            docContainer.innerHTML = '<div class="spinner-border spinner-border-sm text-primary m-auto" role="status" aria-label="Loading profile"></div>';
            try {
                const response = await fetch(cardUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error(`Profile card request failed (${response.status})`);
                const html = await response.text();
                if (!html.includes('pwanimate-mini-profile')) throw new Error('The profile endpoint did not return the profile card fragment.');
                if (docContainer.dataset.profileCardUrl !== cardUrl) return;
                docContainer.innerHTML = html;
            } catch (error) {
                if (docContainer.dataset.profileCardUrl !== cardUrl) return;
                docContainer.innerHTML = '<div class="small text-muted text-center m-auto">This profile preview is unavailable.</div>';
                console.warn('[Pwanimate] Profile card preview could not be loaded:', error);
            }
        }

        renderDocCard(container, prefix, details) {
            const docContainer = container.querySelector(`#${prefix}DocContainer`);
            if (!docContainer) return;
            const docThumbWrapper = container.querySelector(`#${prefix}DocThumbnailWrapper`);
            const docThumb = container.querySelector(`#${prefix}DocThumbnail`);
            const docIconWrapper = container.querySelector(`#${prefix}DocIconWrapper`);
            const docIcon = container.querySelector(`#${prefix}DocIcon`);
            const docTitle = container.querySelector(`#${prefix}DocTitle`);
            const docMeta = container.querySelector(`#${prefix}DocMeta`);
            const docDesc = container.querySelector(`#${prefix}DocDescription`);

            if (details.thumbnailUrl && docThumb && docThumbWrapper) {
                docThumb.src = details.thumbnailUrl;
                docThumbWrapper.classList.remove('d-none');
                if (docIconWrapper) docIconWrapper.classList.add('d-none');
            } else {
                if (docThumbWrapper) docThumbWrapper.classList.add('d-none');
                if (docThumb) docThumb.src = '';
                if (docIconWrapper) docIconWrapper.classList.remove('d-none');
            }
            if (docIcon) docIcon.className = `bi ${details.docIcon}`;
            if (docTitle) docTitle.textContent = details.title;
            if (docMeta) docMeta.textContent = details.subtitle;
            if (docDesc) docDesc.textContent = details.description;
            docContainer.classList.remove('d-none');
        }

        inferFileType(url) {
            if (!url || typeof url !== 'string') return '';
            const cleanUrl = url.split('?')[0].split('#')[0];
            const ext = cleanUrl.split('.').pop().toLowerCase();
            return ext && ext.length <= 5 ? ext : '';
        }

        populatePreviewCard(container, details, mode) {
            const prefix = mode === 'desktop' ? 'desktopPreview' : 'previewSheet';
            this.renderSurface(prefix, details, false);
        }

        closePreview() {
            // Dismiss active preview card without closing the context rail (transitions State C -> State B)
            this.activeResourceDetails = null;
            this.previewResourceState = null;

            if (this.previewDocViewer) {
                try { this.previewDocViewer.destroy(); } catch (e) {}
                this.previewDocViewer = null;
            }

            // Desktop
            const emptyState = document.getElementById('desktopPreviewEmpty');
            const activeState = document.getElementById('desktopPreviewActive');
            if (emptyState && activeState) {
                activeState.classList.remove('d-flex');
                activeState.classList.add('d-none');
                emptyState.classList.remove('d-none');
                this.resetMediaElements(activeState);
            }

            // Mobile
            const sheet = document.getElementById('pwanimateResourcePreviewSheet');
            if (sheet && window.bootstrap) {
                const inst = bootstrap.Offcanvas.getInstance(sheet);
                if (inst) inst.hide();
                this.resetMediaElements(sheet);
            }

            this.updateAddToContextButtons();

            // Restore focus
            if (this.lastPreviewTriggerEl && typeof this.lastPreviewTriggerEl.focus === 'function') {
                this.lastPreviewTriggerEl.focus();
                this.lastPreviewTriggerEl = null;
            }
        }

        /* ==========================================================================
           Phase 1 Workspace Geometry, State & Drag Resizer Implementation
           ========================================================================== */

        initWorkspaceGeometry() {
            // 1. Synchronize Left Rail Collapsed State
            this.syncLeftRailState(this.leftRailCollapsed);

            // 2. Bind Left Rail Toggle Buttons
            const collapseBtn = document.getElementById('pwanimateLeftRailCollapseBtn');
            const expandBtn = document.getElementById('pwanimateLeftRailExpandBtn');
            if (collapseBtn) {
                collapseBtn.onclick = (e) => {
                    e.preventDefault();
                    this.toggleLeftRail(true);
                };
            }
            if (expandBtn) {
                expandBtn.onclick = (e) => {
                    e.preventDefault();
                    this.toggleLeftRail(false);
                };
            }

            // 3. Initialize Context Rail Drag Resizer
            this.initRailResizer();

            // 4. Apply Initial Context Rail State on Desktop
            if (this.contextRailOpen && window.innerWidth >= 1200) {
                this.openContextRail();
            } else {
                this.closeContextRail();
            }

            // 6. Bind Responsive Window Resize (dynamic viewport constraint handling)
            this._onWindowResize = () => {
                if (this.contextRailOpen && window.innerWidth >= 1200) {
                    this.updateContextRailWidth(false); // does NOT overwrite savedPreferredWidth
                }
                this.syncContextRailUI();
                if (this.previewDocViewer && typeof this.previewDocViewer.handleResize === 'function') {
                    this.previewDocViewer.handleResize();
                }
                if (this.contextDocViewer && typeof this.contextDocViewer.handleResize === 'function') {
                    this.contextDocViewer.handleResize();
                }
            };
            window.addEventListener('resize', this._onWindowResize);
        }

        toggleLeftRail(collapsed) {
            this.leftRailCollapsed = (collapsed !== undefined) ? collapsed : !this.leftRailCollapsed;
            try {
                localStorage.setItem('pwanimate_left_rail_collapsed', this.leftRailCollapsed ? 'true' : 'false');
            } catch (e) {}
            this.syncLeftRailState(this.leftRailCollapsed);
            if (this.contextRailOpen && window.innerWidth >= 1200) {
                this.updateContextRailWidth(false);
            }
        }

        syncLeftRailState(collapsed) {
            if (collapsed) {
                document.documentElement.classList.add('pwanimate-left-collapsed');
                document.body.classList.add('pwanimate-left-collapsed');
            } else {
                document.documentElement.classList.remove('pwanimate-left-collapsed');
                document.body.classList.remove('pwanimate-left-collapsed');
            }
        }

        calculateEffectiveContextLimits() {
            const availableWidth = window.innerWidth;
            const leftWidth = this.leftRailCollapsed ? 56 : 240;
            const minCenterWidth = 480;
            const configuredMax = 650;
            const configuredMin = 280;

            const effectiveMax = Math.max(configuredMin, Math.min(configuredMax, availableWidth - leftWidth - minCenterWidth));
            return { min: configuredMin, max: effectiveMax };
        }

        updateContextRailWidth(saveToStorage = false) {
            const limits = this.calculateEffectiveContextLimits();
            this.currentRenderedWidth = Math.max(limits.min, Math.min(this.savedPreferredWidth, limits.max));
            document.documentElement.style.setProperty('--pwanimate-context-rail-width', `${this.currentRenderedWidth}px`);
            document.body.style.setProperty('--pwanimate-context-rail-width', `${this.currentRenderedWidth}px`);
            if (this.resizerEl) {
                this.resizerEl.setAttribute('aria-valuenow', this.currentRenderedWidth.toString());
                this.resizerEl.setAttribute('aria-valuemin', limits.min.toString());
                this.resizerEl.setAttribute('aria-valuemax', limits.max.toString());
            }
            if (saveToStorage) {
                this.savedPreferredWidth = this.currentRenderedWidth;
                try {
                    localStorage.setItem('pwanimate_context_rail_width', this.savedPreferredWidth.toString());
                } catch (e) {}
            }
        }

        toggleContextRail(open) {
            const shouldOpen = (open !== undefined) ? open : !this.contextRailOpen;
            if (shouldOpen) {
                this.openContextRail();
            } else {
                this.closeContextRail();
            }
        }

        openMobileWorkspaceSheet(tabName = 'context') {
            this.switchWorkspaceTab(tabName);
            const sheetEl = document.getElementById('pwanimateResourcePreviewSheet');
            if (!sheetEl || !window.bootstrap) return;
            let offcanvas = window.bootstrap.Offcanvas.getInstance(sheetEl);
            if (!offcanvas) offcanvas = new window.bootstrap.Offcanvas(sheetEl);
            offcanvas.show();
        }

        openContextRail() {
            if (window.innerWidth < 1200) {
                this.openMobileWorkspaceSheet('context');
                return;
            }
            this.contextRailOpen = true;
            try {
                localStorage.setItem('pwanimateContextRailOpen', 'true');
            } catch (e) {}
            document.documentElement.classList.add('pwanimate-context-rail-open');
            document.body.classList.add('pwanimate-context-rail-open');
            this.updateContextRailWidth(false);
            this.syncContextRailUI();

            if (this.activeWorkspaceTab === 'context') {
                this.syncContextView();
            } else {
                // Restore preview if active details exist (State D -> State C), otherwise show empty state (State B)
                const emptyState = document.getElementById('desktopPreviewEmpty');
                const activeState = document.getElementById('desktopPreviewActive');
                if (emptyState && activeState) {
                    if (this.previewResourceState || this.activeResourceDetails) {
                        emptyState.classList.add('d-none');
                        activeState.classList.remove('d-none');
                        activeState.classList.add('d-flex');
                    } else {
                        activeState.classList.remove('d-flex');
                        activeState.classList.add('d-none');
                        emptyState.classList.remove('d-none');
                    }
                }
            }
        }

        closeContextRail() {
            this.contextRailOpen = false;
            try {
                localStorage.setItem('pwanimateContextRailOpen', 'false');
            } catch (e) {}
            document.documentElement.classList.remove('pwanimate-context-rail-open');
            document.body.classList.remove('pwanimate-context-rail-open');
            document.documentElement.style.setProperty('--pwanimate-context-rail-width', '0px');
            document.body.style.setProperty('--pwanimate-context-rail-width', '0px');
            this.syncContextRailUI();

            // Pause any playing media without clearing active preview or context state (preserves State D)
            const activeState = document.getElementById('desktopPreviewActive');
            if (activeState) {
                const video = activeState.querySelector('video');
                if (video && !video.paused) {
                    try { video.pause(); } catch (err) {}
                }
            }
            const contextCard = document.getElementById('desktopContextSurfaceCard');
            if (contextCard) {
                const video = contextCard.querySelector('video');
                if (video && !video.paused) {
                    try { video.pause(); } catch (err) {}
                }
            }
        }

        syncContextRailUI() {
            const toggleBtn = document.getElementById('pwanimateContextRailToggleBtn');
            if (toggleBtn) {
                toggleBtn.setAttribute('aria-expanded', this.contextRailOpen ? 'true' : 'false');
                toggleBtn.setAttribute('title', this.contextRailOpen ? 'Close Context Rail' : 'Open Context Rail');
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.className = this.contextRailOpen ? 'bi bi-layout-sidebar-inset-reverse' : 'bi bi-layout-sidebar-reverse';
                }
            }
        }

        initRailResizer() {
            if (typeof this._resizerCleanup === 'function') {
                try { this._resizerCleanup(); } catch (_) {}
                this._resizerCleanup = null;
            }

            this.resizerEl = document.getElementById('pwanimateRailResizer');
            if (!this.resizerEl) return;

            let isDragging = false;
            let startX = 0;
            let startWidth = 0;

            const onPointerDown = (e) => {
                if (e.button !== 0 && e.pointerType === 'mouse') return;
                isDragging = true;
                this.isResizing = true;
                document.body.classList.add('pwanimate-resizing');
                startX = e.clientX;
                startWidth = this.currentRenderedWidth || this.savedPreferredWidth;

                const resizerNode = document.getElementById('pwanimateRailResizer') || this.resizerEl;
                if (resizerNode && typeof resizerNode.setPointerCapture === 'function') {
                    try {
                        resizerNode.setPointerCapture(e.pointerId);
                    } catch (err) {}
                }

                e.preventDefault();
            };

            const onPointerMove = (e) => {
                if (!isDragging) return;
                const deltaX = startX - e.clientX; // dragging left widens the right rail
                const targetWidth = startWidth + deltaX;
                const limits = this.calculateEffectiveContextLimits();
                const clampedWidth = Math.max(limits.min, Math.min(targetWidth, limits.max));

                if (this.resizeFrame) cancelAnimationFrame(this.resizeFrame);
                this.resizeFrame = requestAnimationFrame(() => {
                    this.currentRenderedWidth = clampedWidth;
                    document.documentElement.style.setProperty('--pwanimate-context-rail-width', `${clampedWidth}px`);
                    document.body.style.setProperty('--pwanimate-context-rail-width', `${clampedWidth}px`);
                    const resizerNode = document.getElementById('pwanimateRailResizer');
                    if (resizerNode) {
                        resizerNode.setAttribute('aria-valuenow', clampedWidth.toString());
                    }
                });
            };

            const onPointerUp = (e) => {
                if (!isDragging) return;
                isDragging = false;
                this.isResizing = false;
                document.body.classList.remove('pwanimate-resizing');

                const resizerNode = document.getElementById('pwanimateRailResizer') || this.resizerEl;
                if (resizerNode && typeof resizerNode.releasePointerCapture === 'function') {
                    try {
                        resizerNode.releasePointerCapture(e.pointerId);
                    } catch (err) {}
                }

                // Commit user-preferred width to savedPreferredWidth and localStorage
                this.savedPreferredWidth = this.currentRenderedWidth;
                try {
                    localStorage.setItem('pwanimate_context_rail_width', this.savedPreferredWidth.toString());
                } catch (err) {}

                if (this.previewDocViewer && typeof this.previewDocViewer.handleResize === 'function') {
                    this.previewDocViewer.handleResize();
                }
                if (this.contextDocViewer && typeof this.contextDocViewer.handleResize === 'function') {
                    this.contextDocViewer.handleResize();
                }
            };

            const delegatedPointerDown = (e) => {
                const targetResizer = e.target.closest('#pwanimateRailResizer');
                if (targetResizer) {
                    onPointerDown(e);
                }
            };

            document.addEventListener('pointerdown', delegatedPointerDown);
            window.addEventListener('pointermove', onPointerMove);
            window.addEventListener('pointerup', onPointerUp);
            window.addEventListener('pointercancel', onPointerUp);

            // Keyboard accessibility for resizer (ArrowLeft, ArrowRight, Home, End)
            const onKeyDown = (e) => {
                const targetResizer = e.target.closest('#pwanimateRailResizer');
                if (!targetResizer || !this.contextRailOpen) return;
                const limits = this.calculateEffectiveContextLimits();
                let step = 16;
                let updated = false;

                if (e.key === 'ArrowLeft') {
                    this.currentRenderedWidth = Math.min(limits.max, this.currentRenderedWidth + step);
                    updated = true;
                } else if (e.key === 'ArrowRight') {
                    this.currentRenderedWidth = Math.max(limits.min, this.currentRenderedWidth - step);
                    updated = true;
                } else if (e.key === 'Home') {
                    this.currentRenderedWidth = limits.min;
                    updated = true;
                } else if (e.key === 'End') {
                    this.currentRenderedWidth = limits.max;
                    updated = true;
                }

                if (updated) {
                    e.preventDefault();
                    this.savedPreferredWidth = this.currentRenderedWidth;
                    document.documentElement.style.setProperty('--pwanimate-context-rail-width', `${this.currentRenderedWidth}px`);
                    document.body.style.setProperty('--pwanimate-context-rail-width', `${this.currentRenderedWidth}px`);
                    targetResizer.setAttribute('aria-valuenow', this.currentRenderedWidth.toString());
                    try {
                        localStorage.setItem('pwanimate_context_rail_width', this.savedPreferredWidth.toString());
                    } catch (err) {}

                    if (this.previewDocViewer && typeof this.previewDocViewer.handleResize === 'function') {
                        this.previewDocViewer.handleResize();
                    }
                    if (this.contextDocViewer && typeof this.contextDocViewer.handleResize === 'function') {
                        this.contextDocViewer.handleResize();
                    }
                }
            };
            document.addEventListener('keydown', onKeyDown);

            this._resizerCleanup = () => {
                document.removeEventListener('pointerdown', delegatedPointerDown);
                window.removeEventListener('pointermove', onPointerMove);
                window.removeEventListener('pointerup', onPointerUp);
                window.removeEventListener('pointercancel', onPointerUp);
                document.removeEventListener('keydown', onKeyDown);
                document.body.classList.remove('pwanimate-resizing');
            };
        }

        resetMediaElements(container) {
            if (!container) return;
            const video = container.querySelector('video');
            if (video) {
                if (video._hlsInstance) {
                    try { video._hlsInstance.destroy(); } catch (e) {}
                    delete video._hlsInstance;
                }
                delete video.dataset.hlsReady;
                video.removeAttribute('data-hls-url');
                video.removeAttribute('data-video-url');
                video.poster = '';
                video.pause();
                video.src = '';
            }
            const img = container.querySelector('.pwanimate-preview-img');
            if (img) { img.src = ''; }
            const docThumb = container.querySelector('.pwanimate-preview-doc-thumbnail-wrapper img');
            if (docThumb) { docThumb.src = ''; }
            const docViewer = container.querySelector('.pwanimate-surface-viewer-host');
            if (docViewer && docViewer._resizeObs) {
                try { docViewer._resizeObs.disconnect(); } catch (e) {}
                delete docViewer._resizeObs;
            }
        }

        scrollToBottom(smooth = true) {
            if (!this.transcript) return;
            this.transcript.scrollTo({
                top: this.transcript.scrollHeight,
                behavior: smooth ? 'smooth' : 'auto'
            });
        }

        scrollToMessageStart(message, smooth = true) {
            if (!this.transcript || !message) return;
            const transcriptTop = this.transcript.getBoundingClientRect().top;
            const messageTop = message.getBoundingClientRect().top;
            const targetTop = this.transcript.scrollTop + messageTop - transcriptTop - 12;
            this.transcript.scrollTo({
                top: Math.max(0, targetTop),
                behavior: smooth ? 'smooth' : 'auto'
            });
        }

        appendTranscriptRow(row) {
            if (!this.transcript || !row) return;
            const disclaimer = this.transcript.querySelector('.pwanimate-chat-disclaimer');
            if (disclaimer) this.transcript.insertBefore(row, disclaimer);
            else this.transcript.appendChild(row);
        }

        setGenerating(loading) {
            this.isGenerating = loading;
            if (this.input) this.input.disabled = loading;
            if (this.voiceBtn) this.voiceBtn.disabled = loading || (!this.voiceRecognition && !this.nativeSpeechBridge);
            if (loading && this.voiceListening) {
                this.voiceErrorMessage = '';
                this.setVoiceListening(false);
                if (this.voiceRecognition) this.voiceRecognition.stop();
                if (this.nativeSpeechBridge) this.nativeSpeechBridge.stopSpeechRecognition();
            }
            this.updateSendButtonState();
        }

        updateSendButtonState() {
            if (!this.sendBtn) return;
            if (this.voiceListening || this.voiceStopping) {
                this.sendBtn.disabled = true;
                this.sendBtn.classList.remove('is-active');
                this.sendBtn.setAttribute('aria-label', 'Stop voice input before sending');
                this.sendBtn.setAttribute('title', 'Stop voice input before sending');
                return;
            }
            if (this.isGenerating) {
                this.sendBtn.disabled = false;
                this.sendBtn.classList.add('is-generating');
                this.sendBtn.classList.remove('is-active');
                this.sendBtn.setAttribute('aria-label', 'Stop generating');
                this.sendBtn.setAttribute('title', 'Stop generating (Esc)');
                return;
            }

            this.sendBtn.classList.remove('is-generating');
            const hasText = Boolean(this.input && this.input.value.trim().length > 0);
            const hasAttachments = this.stagedAttachments && this.stagedAttachments.length > 0;
            
            // Check if any attachment is still uploading
            const hasUploadingAttachments = this._composerAttachmentsEl && 
                this._composerAttachmentsEl.querySelector('.pwanimate-staged-chip.is-uploading');
            const pendingDocument = (this.stagedAttachments || []).some(attachment =>
                attachment.attachment_type === 'document' &&
                ['pending', 'processing'].includes(attachment.processing_status)
            );
            const failedDocument = (this.stagedAttachments || []).some(attachment =>
                attachment.attachment_type === 'document' && attachment.processing_status === 'failed'
            );

            if (hasText || hasAttachments) {
                // Disable send button if any attachment is still uploading
                if (hasUploadingAttachments) {
                    this.sendBtn.disabled = true;
                    this.sendBtn.classList.remove('is-active');
                    this.sendBtn.setAttribute('aria-label', 'Wait for attachments to finish uploading');
                    this.sendBtn.setAttribute('title', 'Wait for attachments to finish uploading');
                } else if (pendingDocument) {
                    this.sendBtn.disabled = true;
                    this.sendBtn.classList.remove('is-active');
                    this.sendBtn.setAttribute('aria-label', 'Wait for document processing to finish');
                    this.sendBtn.setAttribute('title', 'Pwanimate is reading the attached document');
                } else if (failedDocument) {
                    this.sendBtn.disabled = true;
                    this.sendBtn.classList.remove('is-active');
                    this.sendBtn.setAttribute('aria-label', 'Remove the document that could not be processed');
                    this.sendBtn.setAttribute('title', 'This document could not be processed. Remove it to continue.');
                } else {
                    this.sendBtn.disabled = false;
                    this.sendBtn.classList.add('is-active');
                    this.sendBtn.setAttribute('aria-label', 'Send message');
                    this.sendBtn.setAttribute('title', 'Send message (Enter)');
                }
            } else {
                this.sendBtn.disabled = true;
                this.sendBtn.classList.remove('is-active');
                this.sendBtn.setAttribute('aria-label', 'Send message');
                this.sendBtn.setAttribute('title', 'Type a message to send');
            }
        }

        // -----------------------------------------------------------------------
        // Attachment Staging & Upload
        // -----------------------------------------------------------------------

        initAttachmentHandlers() {
            this.stagedAttachments = [];
            this._composerAttachmentsEl = this.composerForm && this.composerForm.querySelector('#pwanimate-composer-attachments');

            const photoInput = this.composerForm && this.composerForm.querySelector('#pwanimatePhotoInput');
            const docInput   = this.composerForm && this.composerForm.querySelector('#pwanimateDocInput');
            const fileInput  = this.composerForm && this.composerForm.querySelector('#pwanimateFileInput');
            const cameraInput = this.composerForm && this.composerForm.querySelector('#pwanimateCameraInput');

            const modal = document.getElementById('pwanimateAttachmentModal');

            const wireOption = (optionId, input, useCapacitorCamera) => {
                const opt = document.getElementById(optionId);
                if (!opt) return;
                opt.addEventListener('click', async () => {
                    if (modal) modal.classList.remove('show');

                    // Capacitor camera path (native mobile)
                    if (useCapacitorCamera &&
                        typeof window.Capacitor !== 'undefined' &&
                        window.Capacitor.Plugins &&
                        window.Capacitor.Plugins.Camera) {
                        try {
                            const { Camera } = window.Capacitor.Plugins;
                            const photo = await Camera.getPhoto({
                                quality: 85,
                                resultType: 'base64',
                                source: 'CAMERA',
                                saveToGallery: false,
                            });
                            if (photo && photo.base64String) {
                                const mime = `image/${photo.format || 'jpeg'}`;
                                const byteStr = atob(photo.base64String);
                                const ab = new ArrayBuffer(byteStr.length);
                                const ia = new Uint8Array(ab);
                                for (let i = 0; i < byteStr.length; i++) ia[i] = byteStr.charCodeAt(i);
                                const blob = new Blob([ab], { type: mime });
                                const fileName = `camera_${Date.now()}.${photo.format || 'jpg'}`;
                                const file = new File([blob], fileName, { type: mime });
                                this._stageFiles([file]);
                            }
                        } catch (err) {
                            if (err && err.message && err.message.toLowerCase().includes('cancel')) return;
                            console.warn('[Pwanimate] Capacitor camera error, falling back to file input:', err);
                            if (cameraInput) cameraInput.click();
                        }
                        return;
                    }

                    if (input) input.click();
                });
            };

            wireOption('pwanimateAttachCamera', cameraInput, true);
            wireOption('pwanimateAttachPhotos', photoInput, false);
            wireOption('pwanimateAttachDocs', docInput, false);
            wireOption('pwanimateAttachFiles', fileInput, false);

            const bindInput = (input) => {
                if (!input) return;
                input.addEventListener('change', (e) => {
                    const files = Array.from(e.target.files || []);
                    if (files.length > 0) this._stageFiles(files);
                    input.value = '';
                });
            };
            bindInput(photoInput);
            bindInput(docInput);
            bindInput(fileInput);
            bindInput(cameraInput);
        }

        _stageFiles(files) {
            files.forEach(file => {
                const chipId = `staged-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
                const chip = this._buildChip(chipId, file.name, file.type);
                if (this._composerAttachmentsEl) {
                    this._composerAttachmentsEl.classList.remove('d-none');
                    this._composerAttachmentsEl.appendChild(chip);
                }
                this._uploadFile(file, chipId);
            });
            this.updateSendButtonState();
        }

        _buildChip(chipId, fileName, mimeType) {
            const isImage = mimeType && mimeType.startsWith('image/');
            const chip = document.createElement('div');
            chip.className = 'pwanimate-staged-chip is-uploading';
            chip.id = chipId;
            chip.dataset.attachmentId = '';

            // Create inner media container
            const mediaContainer = document.createElement('div');
            mediaContainer.className = 'pwanimate-staged-media';

            if (isImage) {
                const iconEl = document.createElement('i');
                iconEl.className = 'pwanimate-staged-icon bi bi-image';
                mediaContainer.appendChild(iconEl);
            } else {
                const iconEl = document.createElement('i');
                iconEl.className = 'pwanimate-staged-icon bi bi-file-earmark-text';
                mediaContainer.appendChild(iconEl);
            }

            // Add spinner inside the media container
            const spinner = document.createElement('span');
            spinner.className = 'pwanimate-staged-spinner spinner-border spinner-border-sm text-primary';
            spinner.style.width = '16px';
            spinner.style.height = '16px';
            spinner.setAttribute('role', 'status');
            mediaContainer.appendChild(spinner);

            chip.appendChild(mediaContainer);

            return chip;
        }

        async _uploadFile(file, chipId) {
            const csrfToken = getCsrfToken();
            const formData = new FormData();
            formData.append('file', file);
            if (this.conversationId) {
                formData.append('conversation_id', this.conversationId);
            }

            let chip = document.getElementById(chipId);

            try {
                const response = await fetch('/api/pwanimate/attachments/upload/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json',
                    },
                    credentials: 'same-origin',
                    body: formData,
                });

                const data = await response.json();
                chip = document.getElementById(chipId);

                if (!response.ok || !data.id) {
                    const errMsg = data.error || 'Upload failed.';
                    console.warn('[Pwanimate] Attachment upload failed:', errMsg);
                    if (chip) {
                        chip.classList.remove('is-uploading');
                        chip.classList.add('is-error');
                        const mediaContainer = chip.querySelector('.pwanimate-staged-media');
                        const spinner = chip.querySelector('.pwanimate-staged-spinner');
                        if (spinner && mediaContainer) spinner.remove();
                        // Auto-remove error chips after 3s
                        setTimeout(() => { if (chip && chip.parentNode) chip.parentNode.removeChild(chip); }, 3000);
                    }
                    return;
                }
                // Success
                const stagedAttachment = {
                    id: data.id,
                    file_name: data.file_name,
                    attachment_type: data.attachment_type,
                    processing_status: data.processing_status || 'not_required',
                    url: data.url
                };
                this.stagedAttachments.push(stagedAttachment);
                if (chip) {
                    chip.classList.remove('is-uploading');
                    chip.dataset.attachmentId = data.id;
                    if (data.attachment_type === 'document' && stagedAttachment.processing_status !== 'ready') {
                        chip.classList.add('is-processing');
                        this._setAttachmentStatusLabel(chip, 'Reading pages…');
                    }
                    
                    const mediaContainer = chip.querySelector('.pwanimate-staged-media');
                    const spinner = chip.querySelector('.pwanimate-staged-spinner');
                    if (spinner && mediaContainer) spinner.remove();

                    // If image, show a tiny thumbnail inside the media container
                    if (data.attachment_type === 'image' && data.url && mediaContainer) {
                        const thumb = document.createElement('img');
                        thumb.src = data.url;
                        thumb.className = 'pwanimate-staged-thumb';
                        thumb.alt = data.file_name;
                        const existingIcon = chip.querySelector('.pwanimate-staged-icon');
                        if (existingIcon) {
                            mediaContainer.removeChild(existingIcon);
                        }
                        mediaContainer.appendChild(thumb);
                    }

                    // Remove button
                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'pwanimate-staged-remove';
                    removeBtn.setAttribute('aria-label', `Remove ${data.file_name}`);
                    removeBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
                    removeBtn.addEventListener('click', () => {
                        this.stagedAttachments = this.stagedAttachments.filter(a => a.id !== data.id);
                        if (chip && chip.parentNode) chip.parentNode.removeChild(chip);
                        if (this._composerAttachmentsEl && !this._composerAttachmentsEl.querySelector('.pwanimate-staged-chip')) {
                            this._composerAttachmentsEl.classList.add('d-none');
                        }
                        this.updateSendButtonState();
                    });
                    chip.appendChild(removeBtn);
                }

                if (data.attachment_type === 'document' && stagedAttachment.processing_status !== 'ready') {
                    this._watchAttachmentProcessing(stagedAttachment, chipId);
                }

                this.updateSendButtonState();

            } catch (err) {
                console.error('[Pwanimate] Attachment upload network error:', err);
                chip = document.getElementById(chipId);
                if (chip) {
                    chip.classList.remove('is-uploading');
                    chip.classList.add('is-error');
                    const mediaContainer = chip.querySelector('.pwanimate-staged-media');
                    const spinner = chip.querySelector('.pwanimate-staged-spinner');
                    if (spinner && mediaContainer) spinner.remove();
                    setTimeout(() => { if (chip && chip.parentNode) chip.parentNode.removeChild(chip); }, 3000);
                }
            }
        }

        _setAttachmentStatusLabel(chip, label, isError = false) {
            if (!chip) return;
            let statusEl = chip.querySelector('.pwanimate-staged-status');
            if (!statusEl) {
                statusEl = document.createElement('span');
                statusEl.className = 'pwanimate-staged-status';
                chip.appendChild(statusEl);
            }
            statusEl.textContent = label;
            statusEl.classList.toggle('is-error', isError);
        }

        async _watchAttachmentProcessing(attachment, chipId) {
            for (let attempt = 0; attempt < 180; attempt += 1) {
                if (!this.stagedAttachments.some(item => item.id === attachment.id)) return;
                await new Promise(resolve => setTimeout(resolve, 1000));
                try {
                    const response = await fetch(`/api/pwanimate/attachments/${encodeURIComponent(attachment.id)}/status/`, {
                        credentials: 'same-origin',
                        headers: { 'Accept': 'application/json' }
                    });
                    if (!response.ok) continue;
                    const data = await response.json();
                    attachment.processing_status = data.processing_status;
                    const chip = document.getElementById(chipId);
                    if (data.processing_status === 'ready') {
                        if (chip) {
                            chip.classList.remove('is-processing');
                            chip.title = data.processing_error || '';
                            this._setAttachmentStatusLabel(chip, data.processing_error ? 'Ready · partial' : 'Ready');
                        }
                        this.updateSendButtonState();
                        return;
                    }
                    if (data.processing_status === 'failed') {
                        if (chip) {
                            chip.classList.remove('is-processing');
                            chip.title = data.processing_error || 'Pwanimate could not read this document.';
                            this._setAttachmentStatusLabel(chip, 'Could not read', true);
                        }
                        attachment.processing_error = data.processing_error || '';
                        this.updateSendButtonState();
                        return;
                    }
                } catch (error) {
                    // Keep polling through brief network interruptions.
                }
            }
        }

        _clearStagedAttachments() {
            this.stagedAttachments = [];
            if (this._composerAttachmentsEl) {
                this._composerAttachmentsEl.innerHTML = '';
                this._composerAttachmentsEl.classList.add('d-none');
            }
        }

        handleAbort() {
            if (!this.isGenerating || !this.abortController) return;
            try {
                this.abortController.abort();
            } catch (e) {
                console.error('[Pwanimate] Abort error:', e);
            }
        }

        showSystemNotice(text) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant d-flex justify-content-center';
            row.innerHTML = `
                <div class="pwanimate-system-notice">
                    <i class="bi bi-stop-circle"></i>
                    <span>${escapeHtml(text)}</span>
                </div>
            `;
            this.appendTranscriptRow(row);
            this.scrollToBottom();
        }

        async downloadGeneratedResource(button) {
            const row = button.closest('.pwanimate-message-row');
            const messageId = row && row.dataset.messageId;
            const fileFormat = button.dataset.format;
            if (!messageId || !['pdf', 'docx'].includes(fileFormat)) return;

            const originalMarkup = button.innerHTML;
            const menu = button.closest('.pwanimate-resource-export-menu');
            const menuButtons = menu ? Array.from(menu.querySelectorAll('.pwanimate-resource-download')) : [button];
            menuButtons.forEach((item) => { item.disabled = true; });
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Preparing…';

            try {
                const response = await fetch(`/api/pwanimate/messages/${encodeURIComponent(messageId)}/resources/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'Accept': 'application/json',
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ format: fileFormat }),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Could not create the document. Please try again.');
                button.innerHTML = '<i class="bi bi-check2 me-2"></i>Saved in My Resources';
                window.location.assign(data.download_url);
            } catch (error) {
                console.error('[Pwanimate] Resource export failed:', error);
                button.innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Could not prepare file';
                window.setTimeout(() => { button.innerHTML = originalMarkup; }, 2600);
                return;
            } finally {
                menuButtons.forEach((item) => { item.disabled = false; });
            }
            window.setTimeout(() => { button.innerHTML = originalMarkup; }, 2200);
        }

        async handleSend(retryOptions = null) {
            if (this.voiceListening || this.voiceStopping) {
                this.setVoiceStatus('Stop voice input before sending or editing your draft.');
                return;
            }
            if (this.isGenerating) return;
            const isRetry = Boolean(retryOptions);
            const text = isRetry ? retryOptions.text : (this.input ? this.input.value.trim() : '');
            const hasStagedAttachments = isRetry
                ? (retryOptions.attachments || []).length > 0
                : (this.stagedAttachments && this.stagedAttachments.length > 0);
            if (!text && !hasStagedAttachments) return;

            // Setup AbortController for modern cancellation support
            this.abortController = new AbortController();

            // Clear input & reset height
            if (!isRetry) {
                this.input.value = '';
                this.resetTextareaHeight();
                this.updateSendButtonState();
                this.setVoiceStatus('');
            }

            // Snapshot staged attachments and clear the strip before sending
            const snapshotAttachments = isRetry
                ? (retryOptions.attachments || []).slice()
                : (this.stagedAttachments || []).slice();
            if (!isRetry) this._clearStagedAttachments();

            // Remove empty state if present
            const emptyState = this.transcript.querySelector('#pwanimate-empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // Render optimistic user message (with attachment chips)
            const userRow = isRetry
                ? retryOptions.userRow
                : this.appendUserMessage(text, null, snapshotAttachments);
            this.addImageAttachmentsToContext(userRow);
            this.showTypingIndicator(text);
            this.setGenerating(true);
            this.scrollToBottom();

            const csrfToken = getCsrfToken();
            if (!this.conversationId && !this.pendingConversationId) {
                this.pendingConversationId = window.crypto && window.crypto.randomUUID
                    ? window.crypto.randomUUID()
                    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
                        const r = Math.random() * 16 | 0;
                        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
                    });
            }

            try {
                const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                const payload = {
                    message: text || ' ',
                    local_time: new Date().toISOString(),
                    timezone: (!browserTimezone || browserTimezone === 'UTC' || browserTimezone === 'Etc/UTC')
                        ? 'Africa/Nairobi'
                        : browserTimezone
                };
                if (isRetry) {
                    payload.retry = true;
                    if (retryOptions.userMessageId) {
                        payload.retry_user_message_id = retryOptions.userMessageId;
                    }
                }
                const targetConversationId = this.conversationId || this.pendingConversationId;
                if (targetConversationId) {
                    payload.conversation_id = targetConversationId;
                }
                if (!this.conversationId) {
                    payload.create_conversation = true;
                }
                if (this.selectedProvider) {
                    payload.provider = this.selectedProvider;
                }
                if (this.selectedModel) {
                    payload.model = this.selectedModel;
                }
                if (snapshotAttachments.length > 0) {
                    payload.attachments = snapshotAttachments.map(a => a.id);
                }
                const contextResources = this.getContextResourcesForRequest();
                if (contextResources.length > 0) {
                    payload.context_resources = contextResources;
                }

                const response = await fetch('/api/pwanimate/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin',
                    signal: this.abortController.signal,
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                // Handle conversation ID update even if there's an error, to prevent spawning new conversations
                if (data.conversation_id && !this.conversationId) {
                    this.conversationId = data.conversation_id;
                    this.pendingConversationId = data.conversation_id;
                    this.workspace.dataset.conversationId = data.conversation_id;

                    // Update URL without full page reload
                    const targetUrl = `/pwanimate/${data.conversation_id}/`;
                    window.history.replaceState({ htmx: true }, '', targetUrl);
                }

                if (!response.ok) {
                    let errMsg = data.error || 'Failed to get answer from Pwanimate.';
                    if (response.status === 429) {
                        errMsg = data.error || 'All free-tier model quotas are temporarily depleted. Please wait a moment for limits to reset.';
                    } else if (response.status === 504) {
                        errMsg = 'Request timed out. Please try asking again.';
                    } else if (response.status === 401 || response.status === 403) {
                        errMsg = 'Your session has expired. Please refresh the page to sign in again.';
                    }
                    this.removeTypingIndicator();
                    if (userRow && data.user_message_id) {
                        userRow.dataset.messageId = data.user_message_id;
                    }
                    this.showErrorBubble(errMsg, text, userRow, snapshotAttachments);
                    this.refreshConversationsList();
                    if (data.quota_status) {
                        this.updateQuotaStatus(data.quota_status);
                    }
                    return;
                }

                this.removeTypingIndicator();
                if (userRow && data.user_message_id) {
                    userRow.dataset.messageId = data.user_message_id;
                }

                const meta = data.metadata || {};
                console.log('[Pwanimate Telemetry]', {
                    conversation_id: data.conversation_id,
                    provider: data.provider,
                    model: data.model,
                    finish_reason: data.finish_reason,
                    prompt_tokens: data.prompt_tokens,
                    completion_tokens: data.completion_tokens,
                    thoughts_tokens: meta.thoughts_tokens,
                    total_output_tokens: meta.total_output_tokens,
                    total_tokens: data.total_tokens,
                    max_output_tokens: meta.max_output_tokens,
                    answer_length: data.answer ? data.answer.length : 0,
                    fallback_used: data.fallback_info ? data.fallback_info.fallback_used : false
                });

                const assistantRow = this.appendAssistantMessage(data.answer, data.sources, data.citations, data.fallback_info, data.quota_info, data.people, data.message_id, data.people_html);
                const disclaimer = this.transcript.querySelector('#pwanimate-chat-disclaimer');
                if (disclaimer) disclaimer.classList.remove('d-none');
                this.scrollToMessageStart(assistantRow);
                this.refreshConversationsList();
                this.updateQuotaStatus(data.quota_status);
                this.updateActiveModelChip(data.quota_info);

            } catch (err) {
                if (err.name === 'AbortError') {
                    console.log('[Pwanimate] Chat request aborted by user.');
                    this.removeTypingIndicator();
                    this.showSystemNotice('Generation stopped');
                } else {
                    console.error('[Pwanimate] Chat network error:', err);
                    this.removeTypingIndicator();
                    this.showErrorBubble(
                        'Network connection error. Please check your internet connection.',
                        text,
                        userRow,
                        snapshotAttachments
                    );
                }
            } finally {
                this.abortController = null;
                this.setGenerating(false);
                if (this.input && isFinePointerDevice()) {
                    this.input.focus();
                }
            }
        }

        appendUserMessage(text, messageId = null, attachments = []) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row user';
            if (messageId) {
                row.dataset.messageId = messageId;
            }
            const escaped = escapeHtml(text || '');

            // Build attachment HTML for optimistic rendering
            let attachmentHtml = '';
            if (attachments && attachments.length > 0) {
                const chips = attachments.map(att => {
                    const attachmentUrl = att.url || `/api/pwanimate/attachments/${encodeURIComponent(att.id)}/view/`;
                    const fileName = att.file_name || 'File';
                    const fileType = (fileName.split('.').pop() || '').toLowerCase();
                    const commonAttrs = `href="${escapeHtml(attachmentUrl)}" data-attachment-id="${escapeHtml(att.id || '')}" data-file-name="${escapeHtml(fileName)}" data-file-type="${escapeHtml(fileType)}" data-media-url="${escapeHtml(attachmentUrl)}"`;
                    if (att.attachment_type === 'image' && attachmentUrl) {
                        return `<a ${commonAttrs} class="pwanimate-message-attachment pwanimate-attachment-thumb-link" data-preview-type="image" title="Preview ${escapeHtml(fileName)}">
                            <img src="${escapeHtml(attachmentUrl)}" alt="${escapeHtml(fileName)}" class="pwanimate-attachment-thumb rounded" loading="lazy">
                        </a>`;
                    }
                    return `<a ${commonAttrs} data-preview-type="document" class="pwanimate-message-attachment pwanimate-attachment-doc-chip badge text-decoration-none d-inline-flex align-items-center gap-1 p-2" title="Preview ${escapeHtml(fileName)}">
                        <i class="bi bi-file-earmark-text fs-6"></i>
                        <span class="text-truncate" style="max-width: 140px;">${escapeHtml(fileName)}</span>
                    </a>`;
                }).join('');
                attachmentHtml = `<div class="pwanimate-user-attachments mb-2 d-flex flex-wrap gap-2">${chips}</div>`;
            }

            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-user-bubble-wrapper">
                        ${attachmentHtml}
                        ${escaped ? `<div class="pwanimate-user-bubble" data-raw="${escaped}">${escaped}</div>` : ''}
                    </div>
                    <div class="pwanimate-message-actions user-actions">
                        <button type="button" class="btn pwanimate-action-btn copy-btn" title="Copy message" aria-label="Copy message">
                            <i class="bi bi-clipboard"></i>
                        </button>
                        <button type="button" class="btn pwanimate-action-btn edit-btn" title="Edit message" aria-label="Edit message">
                            <i class="bi bi-pencil"></i>
                        </button>
                    </div>
                </div>
            `;
            this.appendTranscriptRow(row);
            if (escaped) {
                this.checkCollapsibleUserBubbles(row);
                requestAnimationFrame(() => this.checkCollapsibleUserBubbles(row));
            }
            return row;
        }

        getThinkingPhrases(prompt = '') {
            const lower = (prompt || '').toLowerCase();
            const peoplePattern = /\b(who|student|students|peer|peers|classmate|classmates|lecturer|lecturers|people|person|profile|profiles|contact|contacts)\b/i;
            const docPattern = /\b(doc|docs|document|documents|notes|paper|papers|exam|past\s*paper|syllabus|outline|pdf|resource|resources|material|materials|coursework)\b/i;

            if (peoplePattern.test(lower)) {
                return [
                    'Thinking…',
                    'Looking for matches…',
                    'Checking student profiles…',
                    'Finding relevant peers…',
                    'Putting it together…',
                    'Almost there…'
                ];
            }

            if (docPattern.test(lower)) {
                return [
                    'Thinking…',
                    'Checking your resources…',
                    'Finding relevant material…',
                    'Connecting the context…',
                    'Devouring the details…',
                    'Putting it together…',
                    'Almost there…'
                ];
            }

            return [
                'Thinking…',
                'Processing…',
                'Connecting the dots…',
                'Devouring the details…',
                'Checking PwaniNet…',
                'Putting it together…',
                'Almost there…'
            ];
        }

        showTypingIndicator(userPrompt = '') {
            this.removeTypingIndicator();

            const phrases = this.getThinkingPhrases(userPrompt);
            let phraseIndex = 0;

            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant pwanimate-thinking-loader-row';
            row.id = 'pwanimate-typing-row';
            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-assistant-bubble">
                        <div class="pwanimate-assistant-header">
                            <img src="/static/images/pwanimate/pwanimate-transparent.png" class="pwanimate-assistant-avatar" alt="Pwanimate">
                            <span>Pwanimate</span>
                        </div>
                        <div class="pwanimate-thinking-loader pwanimate-typing-indicator" aria-live="polite">
                            <div class="pwanimate-thinking-animation" aria-hidden="true">
                                <span class="pwanimate-thinking-dot dot-1"></span>
                                <span class="pwanimate-thinking-dot dot-2"></span>
                                <span class="pwanimate-thinking-dot dot-3"></span>
                            </div>
                            <span class="pwanimate-thinking-text">${escapeHtml(phrases[0])}</span>
                        </div>
                    </div>
                </div>
            `;
            this.appendTranscriptRow(row);

            const textEl = row.querySelector('.pwanimate-thinking-text');
            if (textEl && phrases.length > 1) {
                this.thinkingTextInterval = setInterval(() => {
                    phraseIndex = (phraseIndex + 1) % phrases.length;
                    textEl.classList.add('fade-out');
                    this.thinkingFadeTimeout = setTimeout(() => {
                        textEl.textContent = phrases[phraseIndex];
                        textEl.classList.remove('fade-out');
                    }, 200);
                }, 2400);
            }
        }

        removeTypingIndicator() {
            if (this.thinkingTextInterval) {
                clearInterval(this.thinkingTextInterval);
                this.thinkingTextInterval = null;
            }
            if (this.thinkingFadeTimeout) {
                clearTimeout(this.thinkingFadeTimeout);
                this.thinkingFadeTimeout = null;
            }
            const typingRows = this.transcript ? this.transcript.querySelectorAll('#pwanimate-typing-row, .pwanimate-thinking-loader-row') : [];
            typingRows.forEach(r => r.remove());
        }

        /**
         * Updates all conversation timestamp elements ([data-ts]) in both
         * desktop and mobile sidebars with live-calculated relative time strings.
         * Safe to call at any time; skips elements with no/invalid timestamp.
         */
        updateTimestamps() {
            const containers = [
                this.sidebarList || document.getElementById('pwanimate-sidebar-list'),
                this.mobileList  || document.getElementById('pwanimate-mobile-list'),
            ];
            containers.forEach((container) => {
                if (!container) return;
                container.querySelectorAll('time[data-ts]').forEach((el) => {
                    const rel = formatRelativeTime(el.getAttribute('data-ts'));
                    if (rel) el.textContent = rel;
                });
            });
        }

        /**
         * Starts a 60-second interval that keeps all sidebar timestamps current.
         * Clears any previously running ticker first to avoid duplicates.
         */
        startTimestampTicker() {
            if (this._timestampTicker) {
                clearInterval(this._timestampTicker);
            }
            this._timestampTicker = setInterval(() => {
                this.updateTimestamps();
            }, 60000);
        }

        initMobileMenuSwipeNavigation() {
            const menu = document.getElementById('pwanimateMobileMenu');
            if (!menu) return;

            this._onMobileMenuTouchStart = (event) => {
                if (!event.touches || event.touches.length !== 1) {
                    this._mobileMenuSwipeStart = null;
                    return;
                }

                const touch = event.touches[0];
                const isOpen = menu.classList.contains('show');
                if (isOpen) {
                    if (!menu.contains(event.target)) {
                        this._mobileMenuSwipeStart = null;
                        return;
                    }
                    this._mobileMenuSwipeStart = { x: touch.clientX, y: touch.clientY, action: 'close' };
                } else if (touch.clientX >= window.innerWidth - 32) {
                    this._mobileMenuSwipeStart = { x: touch.clientX, y: touch.clientY, action: 'open' };
                } else {
                    this._mobileMenuSwipeStart = null;
                }
            };

            this._onMobileMenuTouchEnd = (event) => {
                const start = this._mobileMenuSwipeStart;
                this._mobileMenuSwipeStart = null;
                if (!start || !event.changedTouches || event.changedTouches.length !== 1) return;

                const touch = event.changedTouches[0];
                const deltaX = touch.clientX - start.x;
                const deltaY = touch.clientY - start.y;
                if (Math.abs(deltaX) < 72 || Math.abs(deltaX) < Math.abs(deltaY) * 1.3) return;

                const shouldOpen = start.action === 'open' && deltaX < 0;
                const shouldClose = start.action === 'close' && deltaX > 0;
                if (!shouldOpen && !shouldClose) return;

                const offcanvas = window.bootstrap && window.bootstrap.Offcanvas
                    ? window.bootstrap.Offcanvas.getOrCreateInstance(menu)
                    : null;
                if (!offcanvas) return;
                if (shouldOpen) offcanvas.show();
                else offcanvas.hide();
            };

            this._onMobileMenuTouchCancel = () => {
                this._mobileMenuSwipeStart = null;
            };

            document.addEventListener('touchstart', this._onMobileMenuTouchStart, { passive: true });
            document.addEventListener('touchend', this._onMobileMenuTouchEnd, { passive: true });
            document.addEventListener('touchcancel', this._onMobileMenuTouchCancel, { passive: true });
        }

        destroy() {
            if (this._onNativeSpeechEvent) {
                window.removeEventListener('pwaninet:native-speech', this._onNativeSpeechEvent);
                this._onNativeSpeechEvent = null;
            }
            if ((this.voiceListening || this.voiceStopping) && this.nativeSpeechBridge) {
                try {
                    if (this.nativeSpeechBridge.cancelSpeechRecognition) this.nativeSpeechBridge.cancelSpeechRecognition();
                    else this.nativeSpeechBridge.stopSpeechRecognition();
                } catch (e) {}
            }
            this.stopVoiceLevelMeter();
            this.nativeSpeechBridge = null;
            if (this.voiceRecognition) {
                this.voiceRecognition.onstart = null;
                this.voiceRecognition.onresult = null;
                this.voiceRecognition.onerror = null;
                this.voiceRecognition.onend = null;
                try { this.voiceRecognition.abort(); } catch (e) {}
                this.voiceRecognition = null;
            }
            if (this.isGenerating && this.abortController) {
                try { this.abortController.abort(); } catch (e) {}
            }
            this.removeTypingIndicator();
            if (this._timestampTicker) {
                clearInterval(this._timestampTicker);
                this._timestampTicker = null;
            }
            if (this.resizeFrame) {
                cancelAnimationFrame(this.resizeFrame);
                this.resizeFrame = null;
            }
            if (this._onDocumentClick) {
                document.removeEventListener('click', this._onDocumentClick);
                this._onDocumentClick = null;
            }
            if (this._onKeyDown) {
                document.removeEventListener('keydown', this._onKeyDown);
                this._onKeyDown = null;
            }
            if (this._onMobileMenuTouchStart) {
                document.removeEventListener('touchstart', this._onMobileMenuTouchStart);
                this._onMobileMenuTouchStart = null;
            }
            if (this._onMobileMenuTouchEnd) {
                document.removeEventListener('touchend', this._onMobileMenuTouchEnd);
                this._onMobileMenuTouchEnd = null;
            }
            if (this._onMobileMenuTouchCancel) {
                document.removeEventListener('touchcancel', this._onMobileMenuTouchCancel);
                this._onMobileMenuTouchCancel = null;
            }
            if (this._onWindowResize) {
                window.removeEventListener('resize', this._onWindowResize);
                this._onWindowResize = null;
            }
            if (typeof this._resizerCleanup === 'function') {
                this._resizerCleanup();
                this._resizerCleanup = null;
            }
            if (this.previewDocViewer && typeof this.previewDocViewer.destroy === 'function') {
                try { this.previewDocViewer.destroy(); } catch (_) {}
                this.previewDocViewer = null;
            }
            if (this.contextDocViewer && typeof this.contextDocViewer.destroy === 'function') {
                try { this.contextDocViewer.destroy(); } catch (_) {}
                this.contextDocViewer = null;
            }
            document.body.classList.remove('pwanimate-resizing');
            if (window._activePwanimateChat === this) {
                window._activePwanimateChat = null;
            }
        }


        appendAssistantMessage(answer, sources, citations, fallbackInfo, quotaInfo, people = [], messageId = null, peopleHtmlFromServer = '') {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant';
            if (messageId) {
                row.dataset.messageId = messageId;
            }

            const parsedHtml = this.renderMarkdownWithMathAndCode(answer);

            let peopleHtml = '';
            if (Array.isArray(people) && people.length > 0) {
                peopleHtml = typeof peopleHtmlFromServer === 'string' && peopleHtmlFromServer
                    ? peopleHtmlFromServer
                    : this.renderPeopleCards(people);
            }

            let citationsHtml = '';
            // If people cards are rendered, omit redundant person items from general sources
            const filteredSources = (Array.isArray(people) && people.length > 0)
                ? (sources || []).filter(src => src.source !== 'user')
                : (sources || []);

            if (Array.isArray(filteredSources) && filteredSources.length > 0) {
                const badges = filteredSources.map((src) => {
                    const title = escapeHtml(src.title || src.citation || 'Document');
                    const person = src.person || {};
                    if (src.url) {
                        return `<button type="button" class="pwanimate-citation-badge"
                            data-url="${escapeHtml(src.url)}"
                            data-title="${title}"
                            data-source-type="${escapeHtml(src.source || '')}"
                            data-resource-type="${escapeHtml(src.resource_type || '')}"
                            data-media-url="${escapeHtml(src.media_url || '')}"
                            data-thumbnail-url="${escapeHtml(src.thumbnail_url || '')}"
                            data-hls-url="${escapeHtml(src.hls_url || '')}"
                            data-author="${escapeHtml(src.author || '')}"
                            data-snippet="${escapeHtml(src.snippet || '')}"
                            data-post-id="${escapeHtml(src.post_id || '')}"
                            data-citation="${escapeHtml(src.citation || '')}"
                            data-page-number="${escapeHtml(src.page_number || '')}"
                            data-document-id="${escapeHtml(src.document_id || '')}"
                            data-document-share-id="${escapeHtml(src.document_share_id || '')}"
                            data-file-type="${escapeHtml(src.file_type || src.file_extension || '')}"
                            data-username="${escapeHtml(person.username || '')}"
                            data-profile-url="${escapeHtml(person.profile_url || '')}"
                            data-profile-card-url="${escapeHtml(person.profile_card_url || '')}"
                            data-avatar-url="${escapeHtml(person.avatar_url || person.profile_photo_url || '')}"
                            data-headline="${escapeHtml(person.headline || '')}"
                            data-academic-level="${escapeHtml(person.academic_level || '')}"
                            data-programme-name="${escapeHtml(person.programme_name || person.programme || '')}"
                            data-bio="${escapeHtml(person.bio || '')}"
                            aria-label="View ${title}">
                            <i class="bi bi-link-45deg"></i>
                            <span>${title}</span>
                        </button>`;
                    }
                    return `<span class="pwanimate-citation-badge">
                        <i class="bi bi-file-earmark-text"></i>
                        <span>${title}</span>
                    </span>`;
                }).join('');

                citationsHtml = `
                    <div class="pwanimate-citations">
                        <div class="pwanimate-citations-header">
                            <i class="bi bi-file-earmark-check"></i>
                            <span>Sources referenced</span>
                        </div>
                        <div class="pwanimate-citation-list">${badges}</div>
                    </div>
                `;
            } else if (Array.isArray(citations) && citations.length > 0 && (!Array.isArray(people) || people.length === 0)) {
                const badges = citations.map((cit) => `
                    <span class="pwanimate-citation-badge">
                        <i class="bi bi-bookmark-fill"></i>
                        <span>${escapeHtml(cit)}</span>
                    </span>
                `).join('');

                citationsHtml = `
                    <div class="pwanimate-citations">
                        <div class="pwanimate-citations-header">
                            <i class="bi bi-quote"></i>
                            <span>Citations</span>
                        </div>
                        <div class="pwanimate-citation-list">${badges}</div>
                    </div>
                `;
            }

            let fallbackHtml = '';
            if (fallbackInfo && fallbackInfo.vision_text_fallback) {
                const used = escapeHtml(fallbackInfo.provider_used || 'an available text model');
                fallbackHtml = `
                    <div class="pwanimate-fallback-notice">
                        <i class="bi bi-eye-slash"></i>
                        <span>Image vision models couldn’t process this request. I continued with your text using <strong>${used}</strong>; the image wasn’t analyzed.</span>
                    </div>
                `;
            } else if (quotaInfo && quotaInfo.switched) {
                const orig = escapeHtml(quotaInfo.primary_model || quotaInfo.primary_provider || 'primary model');
                const active = escapeHtml(quotaInfo.active_model || quotaInfo.active_provider || 'alternate model');
                fallbackHtml = `
                    <div class="pwanimate-fallback-notice">
                        <i class="bi bi-lightning-charge-fill"></i>
                        <span>Free-tier limit reached for <strong>${orig}</strong>. Automatically switched to <strong>${active}</strong>.</span>
                    </div>
                `;
            } else if (fallbackInfo && fallbackInfo.fallback_used) {
                const orig = escapeHtml(fallbackInfo.original_provider || '');
                const used = escapeHtml(fallbackInfo.provider_used || '');
                const fallbackText = fallbackInfo.vision_fallback
                    ? `Gemini vision was unavailable. Answered by <strong>${used}</strong>.`
                    : `Answered by <strong>${used}</strong> (${orig} quota exceeded).`;
                fallbackHtml = `
                    <div class="pwanimate-fallback-notice">
                        <i class="bi bi-arrow-repeat"></i>
                        <span>${fallbackText}</span>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-assistant-bubble">
                        <div class="pwanimate-assistant-header">
                            <img src="/static/images/pwanimate/pwanimate-transparent.png" class="pwanimate-assistant-avatar" alt="Pwanimate">
                            <span>Pwanimate</span>
                        </div>
                        <div class="pwanimate-markdown-body" data-raw="${escapeHtml(answer)}">${parsedHtml}</div>
                        ${peopleHtml}
                        ${citationsHtml}
                        ${fallbackHtml}
                    </div>
                    <div class="pwanimate-message-actions assistant-actions">
                        <div class="dropdown pwanimate-resource-export">
                            <button type="button" class="btn pwanimate-action-btn" data-bs-toggle="dropdown" aria-expanded="false" title="Save response to My Resources" aria-label="Save response to My Resources">
                                <i class="bi bi-file-earmark-arrow-down"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end pwanimate-resource-export-menu">
                                <li><button type="button" class="dropdown-item pwanimate-resource-download" data-format="pdf"><i class="bi bi-filetype-pdf me-2"></i>Download PDF</button></li>
                                <li><button type="button" class="dropdown-item pwanimate-resource-download" data-format="docx"><i class="bi bi-filetype-docx me-2"></i>Download Word document</button></li>
                            </ul>
                        </div>
                        <button type="button" class="btn pwanimate-action-btn copy-btn" title="Copy answer" aria-label="Copy answer">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                </div>
            `;

            this.appendTranscriptRow(row);
            const mdBody = row.querySelector('.pwanimate-markdown-body');
            if (mdBody) {
                this.postProcessMarkdownDOM(mdBody);
            }
            if (window.htmx && typeof window.htmx.process === 'function') {
                window.htmx.process(row);
            }
            return row;
        }

        renderPeopleCards(people) {
            if (!Array.isArray(people) || people.length === 0) {
                return '';
            }

            const cardsHtml = people.map(p => {
                const username = escapeHtml(p.username || 'user');
                const displayName = escapeHtml(p.display_name || p.username || 'User');
                const profileUrl = escapeHtml(p.profile_url || `/users/user/${username}/`);
                const personData = escapeHtml(JSON.stringify(p));
                const initial = escapeHtml((p.display_name || p.username || 'U').charAt(0).toUpperCase());

                let avatarHtml = '';
                if (p.avatar_url) {
                    avatarHtml = `<img src="${escapeHtml(p.avatar_url)}" alt="${displayName}" class="rounded-circle object-fit-cover shadow-xs pwanimate-person-avatar" style="width: 48px; height: 48px;" onerror="this.onerror=null; this.src='/static/images/default_pic1.jpg';">`;
                } else {
                    avatarHtml = `<div class="rounded-circle pwanimate-avatar-placeholder d-flex align-items-center justify-content-center fw-bold shadow-xs" style="width: 48px; height: 48px; font-size: 1.1rem;">${initial}</div>`;
                }

                let academicHtml = '';
                if (p.academic_level || p.programme_name) {
                    const level = p.academic_level ? escapeHtml(p.academic_level) : '';
                    const prog = p.programme_name ? escapeHtml(p.programme_name) : '';
                    const sep = (level && prog) ? ' • ' : '';
                    academicHtml = `<div class="pwanimate-person-academic small pwanimate-line-clamp-2 mb-2"><i class="bi bi-mortarboard me-1"></i>${level}${sep}${prog}</div>`;
                }

                let headlineHtml = '';
                if (p.headline) {
                    headlineHtml = `<div class="pwanimate-person-headline small text-muted pwanimate-line-clamp-2 mb-2">${escapeHtml(p.headline)}</div>`;
                }

                let badgesHtml = '';
                if (p.collaboration_status === 'open_to_projects') {
                    badgesHtml += `<span class="badge pwanimate-badge-collab"><i class="bi bi-code-slash me-1"></i>Open to Projects</span>`;
                } else if (p.collaboration_status === 'open_to_study_groups') {
                    badgesHtml += `<span class="badge pwanimate-badge-collab"><i class="bi bi-book me-1"></i>Open to Study Groups</span>`;
                } else if (p.collaboration_status === 'open_to_networking') {
                    badgesHtml += `<span class="badge pwanimate-badge-collab"><i class="bi bi-people me-1"></i>Open to Networking</span>`;
                } else if (p.collaboration_status === 'any_open') {
                    badgesHtml += `<span class="badge pwanimate-badge-collab"><i class="bi bi-person-check me-1"></i>Open to Collaborate</span>`;
                }

                if (Array.isArray(p.matched_skills)) {
                    p.matched_skills.forEach(skill => {
                        badgesHtml += `<span class="badge pwanimate-badge-skill"><i class="bi bi-check2 me-1"></i>${escapeHtml(skill)}</span>`;
                    });
                }

                if (Array.isArray(p.matched_interests)) {
                    p.matched_interests.forEach(interest => {
                        badgesHtml += `<span class="badge pwanimate-badge-interest"><i class="bi bi-star me-1"></i>${escapeHtml(interest)}</span>`;
                    });
                }

                if (p.evidence && typeof p.evidence === 'object') {
                    if (p.evidence.academic_alignment) {
                        badgesHtml += `<span class="badge pwanimate-badge-evidence"><i class="bi bi-mortarboard-fill me-1"></i>${escapeHtml(p.evidence.academic_alignment)}</span>`;
                    }
                    if (p.evidence.mutual_connections_count) {
                        badgesHtml += `<span class="badge pwanimate-badge-evidence"><i class="bi bi-people-fill me-1"></i>${p.evidence.mutual_connections_count} mutual</span>`;
                    }
                    if (p.evidence.shared_groups_count) {
                        badgesHtml += `<span class="badge pwanimate-badge-evidence"><i class="bi bi-collection-fill me-1"></i>${p.evidence.shared_groups_count} groups</span>`;
                    }
                }

                return `
                    <div class="col-12 col-xl-6 pwanimate-person-col">
                        <div class="card h-100 border rounded-4 p-3 shadow-xs pwanimate-person-card">
                            <div class="d-flex align-items-start gap-3">
                                <a href="${profileUrl}" class="text-decoration-none flex-shrink-0" hx-get="${profileUrl}" hx-target="#page-content-target" hx-swap="innerHTML" hx-push-url="true" hx-history="true" title="${displayName}">
                                    <div class="position-relative">
                                        ${avatarHtml}
                                    </div>
                                </a>
                                <div class="flex-grow-1 min-w-0">
                                    <div class="d-flex align-items-center justify-content-between gap-1 mb-1">
                                        <div class="min-w-0 flex-grow-1 pe-1">
                                            <a href="${profileUrl}" class="text-decoration-none pwanimate-person-name fw-bold text-truncate d-block" hx-get="${profileUrl}" hx-target="#page-content-target" hx-swap="innerHTML" hx-push-url="true" hx-history="true" style="font-size: 0.95rem;">
                                                ${displayName}
                                            </a>
                                            <span class="pwanimate-person-handle text-muted small d-block text-truncate" style="font-size: 0.78rem;">
                                                @${username}
                                            </span>
                                        </div>
                                    </div>
                                    ${academicHtml}
                                    ${headlineHtml}
                                    <div class="d-flex flex-wrap gap-1 pwanimate-person-badges mb-2">
                                        ${badgesHtml}
                                    </div>
                                    <div class="d-flex align-items-center justify-content-end gap-2 mt-2 pt-1 border-top" style="border-color: var(--pwanimate-border) !important;">
                                        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3 py-1 pwanimate-person-preview-btn" data-profile-url="${profileUrl}" data-person="${personData}" style="font-size: 0.78rem;">
                                            <i class="bi bi-layout-sidebar-inset me-1"></i>Preview here
                                        </button>
                                        <a href="${profileUrl}" class="btn btn-sm btn-outline-primary rounded-pill px-3 py-1 pwanimate-view-profile-btn" hx-get="${profileUrl}" hx-target="#page-content-target" hx-swap="innerHTML" hx-push-url="true" hx-history="true" style="font-size: 0.78rem;">
                                            <i class="bi bi-person me-1"></i>View Profile
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <div class="pwanimate-people-section mt-3">
                    <div class="pwanimate-people-header d-flex align-items-center gap-2 mb-2 text-muted small fw-semibold">
                        <i class="bi bi-people-fill text-primary"></i>
                        <span>Discovered Students & Peers</span>
                    </div>
                    <div class="pwanimate-people-grid row g-2">
                        ${cardsHtml}
                    </div>
                </div>
            `;
        }

        showErrorBubble(message, originalText, userRow = null, attachments = []) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant';
            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-error-bubble">
                        <div>
                            <i class="bi bi-exclamation-triangle-fill me-2"></i>
                            <span>${escapeHtml(message)}</span>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger pwanimate-retry-btn">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </div>
                </div>
            `;

            const retryBtn = row.querySelector('.pwanimate-retry-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    row.remove();
                    this.handleSend({
                        text: originalText,
                        userRow,
                        userMessageId: userRow && userRow.dataset.messageId,
                        attachments
                    });
                });
            }

            this.appendTranscriptRow(row);
            this.scrollToBottom();
        }

        async handleDeleteConversation(convId) {
            if (!confirm('Are you sure you want to delete this conversation?')) return;

            const csrfToken = getCsrfToken();
            try {
                let res = await fetch(`/pwanimate/${convId}/delete/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    }
                });

                if (res.status === 404 || res.status === 405) {
                    res = await fetch(`/api/pwanimate/conversations/${convId}/`, {
                        method: 'DELETE',
                        headers: {
                            'X-CSRFToken': csrfToken
                        }
                    });
                }

                if (res.status === 204 || res.ok) {
                    // Remove from desktop and mobile lists across the whole document
                    const items = document.querySelectorAll(`.pwanimate-conversation-item[data-id="${convId}"]`);
                    items.forEach((it) => it.remove());

                    // Check if either list is now empty and insert placeholder
                    const desktopList = (this && this.sidebarList) || document.getElementById('pwanimate-sidebar-list');
                    if (desktopList && !desktopList.querySelector('.pwanimate-conversation-item')) {
                        desktopList.innerHTML = '<div class="text-center text-muted p-3 x-small">No conversations yet. Ask a question to start one!</div>';
                    }
                    const mobileList = (this && this.mobileList) || document.getElementById('pwanimate-mobile-list');
                    if (mobileList && !mobileList.querySelector('.pwanimate-conversation-item')) {
                        mobileList.innerHTML = '<div class="text-center text-muted p-3 x-small">No conversations yet. Ask a question to start one!</div>';
                    }

                    // If active conversation was deleted, navigate to index
                    const activeConvId = (this && this.conversationId) || document.getElementById('pwanimate-workspace')?.dataset?.conversationId;
                    if (activeConvId === convId) {
                        if (window.htmx) {
                            window.htmx.ajax('GET', '/pwanimate/', {
                                target: '#page-content-target',
                                pushUrl: true,
                                swap: 'innerHTML'
                            });
                        } else {
                            window.location.href = '/pwanimate/';
                        }
                    }
                } else {
                    alert('Failed to delete conversation.');
                }
            } catch (e) {
                console.error('[Pwanimate] Delete error:', e);
                alert('Network error while deleting conversation.');
            }
        }

        async refreshConversationsList() {
            try {
                const res = await fetch('/api/pwanimate/conversations/', {
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                if (!res.ok) return;
                const conversations = await res.json();
                this.renderConversationsList(conversations);
            } catch (e) {
                console.warn('[Pwanimate] Failed to refresh conversation list:', e);
            }
        }

        renderConversationsList(conversations) {
            if (!Array.isArray(conversations)) return;

            let html = '';
            if (conversations.length === 0) {
                html = `<div class="text-center text-muted p-3 x-small">No conversations yet. Ask a question to start one!</div>`;
            } else {
                html = conversations.map((c) => {
                    const isActive = this.conversationId === c.id ? 'active' : '';
                    const title = escapeHtml(c.title || 'New Conversation');
                    const ts = c.updated_at || c.created_at || '';
                    const relTime = ts ? formatRelativeTime(ts) : 'just now';
                    const tsAttr = ts ? ` data-ts="${escapeHtml(ts)}"` : '';
                    return `
                        <div class="pwanimate-conversation-item ${isActive}"
                             data-id="${c.id}"
                             hx-get="/pwanimate/${c.id}/"
                             hx-target="#page-content-target"
                             hx-swap="innerHTML"
                             hx-push-url="true"
                             role="button"
                             tabindex="0">
                            <div class="pwanimate-conversation-info">
                                <div class="pwanimate-conversation-title" title="${title}">${title}</div>
                                <div class="pwanimate-conversation-time"><time${tsAttr}>${relTime}</time></div>
                            </div>
                            <button type="button"
                                    class="pwanimate-conversation-delete"
                                    data-conversation-id="${c.id}"
                                    aria-label="Delete conversation"
                                    title="Delete conversation"
                                    onclick="event.stopPropagation(); event.preventDefault(); window.handleDeletePwanimateConversation('${c.id}');">
                                <i class="bi bi-trash3"></i>
                            </button>
                        </div>
                    `;
                }).join('');
            }

            const desktopList = this.sidebarList || document.getElementById('pwanimate-sidebar-list');
            if (desktopList) {
                desktopList.innerHTML = html;
                if (window.htmx) window.htmx.process(desktopList);
            }
            const mobileList = this.mobileList || document.getElementById('pwanimate-mobile-list');
            if (mobileList) {
                mobileList.innerHTML = html;
                if (window.htmx) window.htmx.process(mobileList);
            }
        }

        async fetchQuotaStatus() {
            try {
                const res = await fetch('/api/pwanimate/quota-status/', {
                    headers: { 'Accept': 'application/json' },
                    credentials: 'same-origin'
                });
                if (!res.ok) return;
                const data = await res.json();
                this.updateQuotaStatus(data.quota_status);

                // Initialize active model chip from status if available
                if (data.quota_status && Array.isArray(data.quota_status.models) && data.quota_status.models.length > 0) {
                    const primary = data.quota_status.models[0];
                    const active = data.quota_status.models.find((m) => !m.rate_limited) || primary;
                    this.updateActiveModelChip({
                        active_model: active.model || active.provider,
                        primary_model: primary.model || primary.provider,
                        switched: (active.model !== primary.model || active.provider !== primary.provider),
                    });
                }
            } catch (e) {
                console.warn('[Pwanimate] Failed to fetch quota status:', e);
            }
        }

        getDefaultModels() {
            return [
                { provider: 'gemini', model: 'gemini-3.6-flash', display_name: 'Gemini 3.6 Flash', provider_label: 'Google', description: "Google's flagship multimodal reasoning model", is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'groq', model: 'openai/gpt-oss-120b', display_name: 'GPT-OSS 120B', provider_label: 'Groq', description: 'Ultra-fast 120B reasoning model on Groq LPU', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'openrouter', model: 'google/gemini-2.5-flash', display_name: 'Gemini 2.5 Flash', provider_label: 'OpenRouter', description: 'Multimodal Flash hosted on OpenRouter', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'groq', model: 'openai/gpt-oss-20b', display_name: 'GPT-OSS 20B', provider_label: 'Groq', description: 'Sub-second lightweight conversational model', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'gemini', model: 'gemini-3.5-flash', display_name: 'Gemini 3.5 Flash', provider_label: 'Google', description: 'High-speed balanced multimodal model', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'openrouter', model: 'nvidia/nemotron-3.5-lightning:free', display_name: 'Nemotron 3.5 Lightning', provider_label: 'OpenRouter', description: 'NVIDIA fast reasoning model (Free Tier)', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'groq', model: 'qwen/qwen3.8-27b', display_name: 'Qwen 3.8 27B', provider_label: 'Groq', description: 'High-throughput multilingual model', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'gemini', model: 'gemini-3.5-flash-lite', display_name: 'Gemini 3.5 Flash-Lite', provider_label: 'Google', description: 'Ultra-lightweight low-latency model', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'openrouter', model: 'nex-agi/nex-n2.5-pro:free', display_name: 'NeX N2.5 Pro', provider_label: 'OpenRouter', description: 'General conversational agent (Free Tier)', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'groq', model: 'groq/compound-mini', display_name: 'Groq Compound Mini', provider_label: 'Groq', description: 'Compound reasoning model on Groq', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'gemini', model: 'gemini-flash-latest', display_name: 'Gemini Flash Latest', provider_label: 'Google', description: 'Latest stable Gemini Flash channel', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
                { provider: 'openrouter', model: 'liquid/lfm-2.5-2.6b:free', display_name: 'Liquid LFM 2.6B', provider_label: 'OpenRouter', description: 'Liquid neural architecture (Free Tier)', is_configured: true, rate_limited: false, cooldown_remaining: 0 },
            ];
        }

        selectModel(provider, model, display, providerLabel) {
            this.selectedProvider = provider || '';
            this.selectedModel = model || '';
            this.selectedDisplay = display || 'Auto';
            this.selectedProviderLabel = providerLabel || '';

            if (this.selectedModel) {
                localStorage.setItem('pwanimate_selected_provider', this.selectedProvider);
                localStorage.setItem('pwanimate_selected_model', this.selectedModel);
                localStorage.setItem('pwanimate_selected_display', this.selectedDisplay);
                localStorage.setItem('pwanimate_selected_provider_label', this.selectedProviderLabel);
            } else {
                localStorage.removeItem('pwanimate_selected_provider');
                localStorage.removeItem('pwanimate_selected_model');
                localStorage.removeItem('pwanimate_selected_display');
                localStorage.removeItem('pwanimate_selected_provider_label');
            }

            // Dismiss dropdown menu if open
            const dropdownBtn = this.workspace ? this.workspace.querySelector('#pwanimateModelDropdownBtn') : null;
            if (dropdownBtn && window.bootstrap && typeof window.bootstrap.Dropdown?.getInstance === 'function') {
                const inst = window.bootstrap.Dropdown.getInstance(dropdownBtn);
                if (inst) inst.hide();
            }

            this.updateSelectedModelUI();
            if (this.cachedQuotaStatus) {
                this.updateQuotaStatus(this.cachedQuotaStatus);
            } else {
                this.updateQuotaStatus({ models: this.getDefaultModels() });
            }
        }

        updateSelectedModelUI() {
            if (this.selectedModelLabel) {
                this.selectedModelLabel.textContent = this.selectedDisplay || 'Auto';
                if (this.selectedModel) {
                    this.selectedModelLabel.title = `Manual override: ${this.selectedDisplay} (${this.selectedProviderLabel || this.selectedProvider})`;
                } else {
                    this.selectedModelLabel.title = 'Auto routing: Failover across available models';
                }
            }
            this.updateDropdownStatusDot();
        }

        updateDropdownStatusDot() {
            if (!this.dropdownStatusDot) return;

            this.dropdownStatusDot.classList.remove('healthy', 'rate-limited', 'cooldown');

            if (!this.cachedQuotaStatus || !Array.isArray(this.cachedQuotaStatus.models)) {
                this.dropdownStatusDot.classList.add('healthy');
                return;
            }

            const models = this.cachedQuotaStatus.models;
            if (this.selectedModel) {
                const found = models.find((m) => m.model === this.selectedModel);
                if (found) {
                    if (!found.is_configured || (found.rate_limited && found.cooldown_remaining > 0)) {
                        this.dropdownStatusDot.classList.add('rate-limited');
                    } else if (found.rate_limited) {
                        this.dropdownStatusDot.classList.add('cooldown');
                    } else {
                        this.dropdownStatusDot.classList.add('healthy');
                    }
                } else {
                    this.dropdownStatusDot.classList.add('healthy');
                }
            } else {
                const allRateLimited = models.length > 0 && models.every((m) => m.rate_limited);
                const primary = models[0];
                if (allRateLimited) {
                    this.dropdownStatusDot.classList.add('rate-limited');
                } else if (primary && primary.rate_limited) {
                    this.dropdownStatusDot.classList.add('cooldown');
                } else {
                    this.dropdownStatusDot.classList.add('healthy');
                }
            }
        }

        updateQuotaStatus(quotaStatus) {
            if (!quotaStatus) return;
            this.cachedQuotaStatus = quotaStatus;

            if (this.quotaStatusEl) {
                this.quotaStatusEl.innerHTML = '';
            }

            const models = Array.isArray(quotaStatus.models) ? quotaStatus.models : [];
            const isAutoSelected = !this.selectedModel;

            // 1. Update Auto item in dropdown menu
            const autoItem = this.workspace ? this.workspace.querySelector('.pwanimate-model-option[data-model=""]') : null;
            if (autoItem) {
                if (isAutoSelected) {
                    autoItem.classList.add('active');
                    if (!autoItem.querySelector('.pwanimate-check-icon')) {
                        const icon = document.createElement('i');
                        icon.className = 'bi bi-check2 text-primary pwanimate-check-icon';
                        autoItem.appendChild(icon);
                    }
                } else {
                    autoItem.classList.remove('active');
                    const icon = autoItem.querySelector('.pwanimate-check-icon');
                    if (icon) icon.remove();
                }
            }

            // 2. Populate dropdown models list
            if (this.dropdownModelsList && models.length > 0) {
                let dropdownHtml = '';
                let lastProvider = null;
                for (const item of models) {
                    const isSelected = (this.selectedModel === item.model);
                    let dotClass = 'healthy';
                    let statusDesc = 'Available';

                    if (!item.is_configured) {
                        dotClass = 'rate-limited';
                        statusDesc = 'API key not configured';
                    } else if (item.rate_limited) {
                        if (item.cooldown_remaining > 0) {
                            dotClass = 'rate-limited';
                            statusDesc = `Rate limited (${Math.ceil(item.cooldown_remaining)}s cooldown)`;
                        } else {
                            dotClass = 'cooldown';
                            statusDesc = 'Recovering';
                        }
                    } else {
                        dotClass = 'healthy';
                        statusDesc = 'Ready';
                    }

                    if (item.provider !== lastProvider) {
                        lastProvider = item.provider;
                        const pLabel = item.provider_label || item.provider.toUpperCase();
                        dropdownHtml += `
                            <li><h6 class="dropdown-header text-muted py-1 px-3 fw-bold text-uppercase" style="font-size: 0.65rem; letter-spacing: 0.06em; margin-top: 4px; opacity: 0.85;">${escapeHtml(pLabel)}</h6></li>
                        `;
                    }

                    dropdownHtml += `
                        <li>
                            <button class="dropdown-item d-flex align-items-center justify-content-between pwanimate-model-option ${isSelected ? 'active' : ''}"
                                    data-provider="${escapeHtml(item.provider)}"
                                    data-model="${escapeHtml(item.model)}"
                                    data-display="${escapeHtml(item.display_name || item.model)}"
                                    data-provider-label="${escapeHtml(item.provider_label || item.provider)}"
                                    type="button"
                                    ${!item.is_configured ? 'disabled' : ''}>
                                <div class="pe-2">
                                    <div class="d-flex align-items-center gap-1">
                                        <span class="pwanimate-model-status-dot ${dotClass}"></span>
                                        <span class="fw-semibold small">${escapeHtml(item.display_name || item.model)}</span>
                                        <span class="badge bg-secondary-subtle text-secondary" style="font-size: 0.65rem;">${escapeHtml(item.provider_label || item.provider)}</span>
                                    </div>
                                    <div class="text-muted" style="font-size: 0.72rem;">${escapeHtml(statusDesc)}</div>
                                </div>
                                ${isSelected ? '<i class="bi bi-check2 text-primary pwanimate-check-icon"></i>' : ''}
                            </button>
                        </li>
                    `;
                }
                this.dropdownModelsList.innerHTML = dropdownHtml;
            }

            // 3. Populate Modal container
            if (this.modalModelsContainer) {
                let modalHtml = '';

                // Auto routing card
                modalHtml += `
                    <div class="pwanimate-quota-card ${isAutoSelected ? 'selected' : ''}">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <div class="d-flex align-items-center gap-2">
                                <span class="pwanimate-model-status-dot healthy"></span>
                                <span class="fw-bold fs-6">Auto (Recommended)</span>
                                <span class="badge bg-primary-subtle text-primary" style="font-size: 0.7rem;">Smart Failover</span>
                            </div>
                            <span class="pwanimate-status-badge healthy">
                                <i class="bi bi-shield-check"></i> Multi-tier Active
                            </span>
                        </div>
                        <p class="text-muted small mb-3">
                            Automatically routes queries to the fastest available model and fails over without downtime if a provider is rate-limited.
                        </p>
                        <div class="d-flex align-items-center justify-content-between">
                            <span class="text-muted small" style="font-size: 0.75rem;">Default production failover</span>
                            ${isAutoSelected ? `
                                <button type="button" class="btn btn-sm btn-outline-primary active disabled" style="font-size: 0.8rem;">
                                    <i class="bi bi-check2 me-1"></i>Active
                                </button>
                            ` : `
                                <button type="button" class="btn btn-sm btn-outline-primary pwanimate-modal-select-btn"
                                        data-provider=""
                                        data-model=""
                                        data-display="Auto"
                                        data-provider-label=""
                                        style="font-size: 0.8rem;">
                                    Switch to Auto
                                </button>
                            `}
                        </div>
                    </div>
                `;

                // Individual model cards with provider section separators
                let lastModalProvider = null;
                for (const item of models) {
                    const isSelected = (this.selectedModel === item.model);
                    let dotClass = 'healthy';
                    let statusBadgeHtml = '';

                    if (!item.is_configured) {
                        dotClass = 'rate-limited';
                        statusBadgeHtml = `<span class="pwanimate-status-badge rate-limited"><i class="bi bi-exclamation-octagon-fill"></i> Unconfigured</span>`;
                    } else if (item.rate_limited) {
                        if (item.cooldown_remaining > 0) {
                            dotClass = 'rate-limited';
                            statusBadgeHtml = `<span class="pwanimate-status-badge rate-limited"><i class="bi bi-hourglass-split"></i> Rate Limited (${Math.ceil(item.cooldown_remaining)}s)</span>`;
                        } else {
                            dotClass = 'cooldown';
                            statusBadgeHtml = `<span class="pwanimate-status-badge cooldown"><i class="bi bi-arrow-repeat"></i> Recovering</span>`;
                        }
                    } else {
                        dotClass = 'healthy';
                        statusBadgeHtml = `<span class="pwanimate-status-badge healthy"><i class="bi bi-check-circle-fill"></i> Operational</span>`;
                    }

                    if (item.provider !== lastModalProvider) {
                        lastModalProvider = item.provider;
                        const pLabel = item.provider_label || item.provider.toUpperCase();
                        modalHtml += `
                            <div class="d-flex align-items-center gap-2 mt-3 mb-1">
                                <span class="fw-bold small text-uppercase text-muted" style="font-size: 0.75rem; letter-spacing: 0.05em;">${escapeHtml(pLabel)}</span>
                                <hr class="flex-grow-1 m-0 opacity-25">
                            </div>
                        `;
                    }

                    modalHtml += `
                        <div class="pwanimate-quota-card ${isSelected ? 'selected' : ''}">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <div class="d-flex align-items-center gap-2">
                                    <span class="pwanimate-model-status-dot ${dotClass}"></span>
                                    <span class="fw-bold fs-6">${escapeHtml(item.display_name || item.model)}</span>
                                    <span class="badge bg-secondary-subtle text-secondary" style="font-size: 0.7rem;">${escapeHtml(item.provider_label || item.provider)}</span>
                                </div>
                                ${statusBadgeHtml}
                            </div>
                            <p class="text-muted small mb-3">
                                ${escapeHtml(item.description || item.model)}
                            </p>
                            <div class="d-flex align-items-center justify-content-between">
                                <code class="text-muted" style="font-size: 0.75rem;">${escapeHtml(item.model)}</code>
                                ${isSelected ? `
                                    <button type="button" class="btn btn-sm btn-outline-primary active disabled" style="font-size: 0.8rem;">
                                        <i class="bi bi-check2 me-1"></i>Active
                                    </button>
                                ` : `
                                    <button type="button" class="btn btn-sm btn-primary pwanimate-modal-select-btn"
                                            data-provider="${escapeHtml(item.provider)}"
                                            data-model="${escapeHtml(item.model)}"
                                            data-display="${escapeHtml(item.display_name || item.model)}"
                                            data-provider-label="${escapeHtml(item.provider_label || item.provider)}"
                                            ${!item.is_configured ? 'disabled' : ''}
                                            style="font-size: 0.8rem;">
                                        Select Model
                                    </button>
                                `}
                            </div>
                        </div>
                    `;
                }
                this.modalModelsContainer.innerHTML = modalHtml;
            }

            this.updateDropdownStatusDot();
        }

        updateActiveModelChip(quotaInfo) {
            const chip = document.getElementById('pwanimate-active-model-chip');
            const nameEl = document.getElementById('pwanimate-active-model-name');
            if (chip && nameEl && quotaInfo) {
                const activeModel = quotaInfo.active_model || quotaInfo.active_provider || 'gemini';
                nameEl.textContent = activeModel;

                if (quotaInfo.switched) {
                    chip.classList.add('switched');
                    const orig = quotaInfo.primary_model || quotaInfo.primary_provider || '';
                    chip.title = `Switched to ${activeModel} (${orig} free-tier limit reached)`;
                } else {
                    chip.classList.remove('switched');
                    chip.title = `Active model: ${activeModel}`;
                }
            }

            if (!this.selectedModel && quotaInfo && this.selectedModelLabel) {
                const activeModel = quotaInfo.active_model || quotaInfo.active_provider;
                if (activeModel) {
                    if (quotaInfo.switched) {
                        this.selectedModelLabel.textContent = `Auto (${activeModel})`;
                        this.selectedModelLabel.title = `Auto failover active: responding with ${activeModel}`;
                    } else {
                        this.selectedModelLabel.textContent = 'Auto';
                        this.selectedModelLabel.title = `Auto routing: responding with ${activeModel}`;
                    }
                }
            }
        }
    }

    function initPwanimate() {
        const workspace = document.getElementById('pwanimate-workspace');
        if (!workspace) {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.destroy();
                window._activePwanimateChat = null;
            }
            document.documentElement.classList.remove('pwanimate-active');
            document.body.classList.remove('pwanimate-active');
            return;
        }
        document.documentElement.classList.add('pwanimate-active');
        document.body.classList.add('pwanimate-active');
        // Guard against double-init on the *same* workspace node (e.g. DOMContentLoaded
        // firing alongside an htmx:afterSwap). We intentionally do NOT block re-init
        // when the workspace element itself has changed (HTMX navigation between conversations),
        // which is why we compare by reference rather than a data-initialized attribute.
        if (window._activePwanimateChat && window._activePwanimateChat.workspace === workspace) {
            window._activePwanimateChat.initWorkspaceGeometry();
            return;
        }
        if (window._activePwanimateChat) {
            window._activePwanimateChat.destroy();
            window._activePwanimateChat = null;
        }
        window._activePwanimateChat = new PwanimateChat(workspace);
    }

    window.initPwanimate = initPwanimate;

    window.pwanimateWorkspace = {
        toggleContextRail: () => {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.toggleContextRail();
            } else {
                const workspace = document.getElementById('pwanimate-workspace');
                if (workspace) workspace.classList.toggle('pwanimate-context-open');
            }
        },
        openContextRail: () => {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.openContextRail();
            } else {
                const workspace = document.getElementById('pwanimate-workspace');
                if (workspace) workspace.classList.add('pwanimate-context-open');
            }
        },
        closeContextRail: () => {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.closeContextRail();
            } else {
                const workspace = document.getElementById('pwanimate-workspace');
                if (workspace) workspace.classList.remove('pwanimate-context-open');
            }
        },
        switchWorkspaceTab: (tab) => {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.switchWorkspaceTab(tab);
            }
        },
        toggleLeftRail: (collapse) => {
            if (window._activePwanimateChat) {
                window._activePwanimateChat.toggleLeftRail(collapse);
            } else {
                const workspace = document.getElementById('pwanimate-workspace');
                if (workspace) {
                    if (collapse) workspace.classList.add('pwanimate-left-collapsed');
                    else workspace.classList.remove('pwanimate-left-collapsed');
                }
            }
        }
    };

    window.handleDeletePwanimateConversation = function (convId) {
        if (!convId) return;
        if (window._activePwanimateChat && typeof window._activePwanimateChat.handleDeleteConversation === 'function') {
            window._activePwanimateChat.handleDeleteConversation(convId);
        } else {
            const activeConvId = document.getElementById('pwanimate-workspace')?.dataset?.conversationId || null;
            PwanimateChat.prototype.handleDeleteConversation.call({ conversationId: activeConvId }, convId);
        }
    };

    window.switchPwanimateSettingsTab = function (scope, tabName) {
        if (!tabName) return;
        const isModal = scope === 'modal';
        const tabsContainerId = isModal ? 'pwanimate-modal-tabs' : 'pwanimate-mobile-tabs';
        const panePrefix = isModal ? 'pwanimate-modal-pane-' : 'pwanimate-mobile-pane-';
        const targetPaneId = panePrefix + tabName;

        // 1. Update tab button active states
        const tabsContainer = document.getElementById(tabsContainerId);
        if (tabsContainer) {
            tabsContainer.querySelectorAll('.nav-link').forEach(function (btn) {
                const btnTab = btn.getAttribute('data-tab') || (btn.id ? btn.id.replace(/^(modal|mobile)-tab-/, '') : '');
                if (btnTab === tabName) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        // 2. Switch content pane
        const targetPane = document.getElementById(targetPaneId);
        if (targetPane) {
            const parent = targetPane.parentElement;
            if (parent) {
                const panes = parent.querySelectorAll('.pwanimate-settings-pane');
                panes.forEach(function (pane) {
                    if (pane === targetPane) {
                        pane.classList.remove('d-none');
                        requestAnimationFrame(function () {
                            pane.classList.add('active');
                        });
                    } else {
                        pane.classList.remove('active');
                        pane.classList.add('d-none');
                    }
                });
            }
            // Scroll to top of scroll container
            if (isModal) {
                const modalBody = document.getElementById('pwanimate-settings-modal-body');
                if (modalBody) modalBody.scrollTop = 0;
            } else {
                const scrollContainer = document.querySelector('.pwanimate-settings-mobile') || document.getElementById('pwanimate-workspace');
                if (scrollContainer) scrollContainer.scrollTop = 0;
            }
        } else {
            // Graceful fallback for HTMX dynamic swap if panes weren't preloaded
            const urlMap = {
                personalization: '/pwanimate/settings/personalization/',
                usage: '/pwanimate/settings/usage/',
                about: '/pwanimate/settings/about/'
            };
            const targetId = isModal ? '#pwanimate-settings-modal-body' : '#pwanimate-settings-mobile-content';
            if (window.htmx && urlMap[tabName]) {
                window.htmx.ajax('GET', urlMap[tabName], { target: targetId, swap: 'innerHTML' });
            }
        }
    };

    window.setPwanimateModalActiveTab = function (el) {
        if (!el) return;
        const tab = el.getAttribute('data-tab') || (el.id ? el.id.replace('modal-tab-', '') : 'personalization');
        window.switchPwanimateSettingsTab('modal', tab);
    };

    window.setPwanimateMobileActiveTab = function (el) {
        if (!el) return;
        const tab = el.getAttribute('data-tab') || (el.id ? el.id.replace('mobile-tab-', '') : 'personalization');
        window.switchPwanimateSettingsTab('mobile', tab);
    };

    // Global listener to sync choice card selections with radio button state
    document.addEventListener('change', function (e) {
        if (e.target && e.target.type === 'radio' && e.target.closest && e.target.closest('.pwanimate-choice-card')) {
            const form = e.target.closest('form');
            if (form) {
                form.querySelectorAll('.pwanimate-choice-card').forEach(function (card) {
                    const r = card.querySelector('input[type="radio"]');
                    if (r && r.checked) {
                        card.classList.add('selected');
                    } else {
                        card.classList.remove('selected');
                    }
                });
            }
        }
    });

    // Ensure modal shows active pane when opened
    document.addEventListener('show.bs.modal', function (e) {
        if (e.target && e.target.id === 'pwanimateSettingsModal') {
            const activeModalTab = e.target.querySelector('#pwanimate-modal-tabs .nav-link.active');
            const tabName = activeModalTab ? activeModalTab.getAttribute('data-tab') : 'personalization';
            window.switchPwanimateSettingsTab('modal', tabName || 'personalization');
        }
    });

    function cleanupPwanimateModals() {
        const modalEl = document.getElementById('pwanimateSettingsModal');
        if (modalEl && window.bootstrap && typeof window.bootstrap.Modal?.getInstance === 'function') {
            const inst = window.bootstrap.Modal.getInstance(modalEl);
            if (inst) {
                inst.hide();
            }
        }
        document.querySelectorAll('.modal-backdrop').forEach(bd => bd.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }

    // Attach to lifecycle
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPwanimate);
    } else {
        initPwanimate();
    }

    if (!window._pwanimateSwapListenerAttached) {
        window._pwanimateSwapListenerAttached = true;
        document.body.addEventListener('htmx:beforeSwap', function (evt) {
            if (evt.detail && evt.detail.target && evt.detail.target.id === 'page-content-target') {
                if (window._activePwanimateChat) {
                    window._activePwanimateChat.destroy();
                    window._activePwanimateChat = null;
                }
                cleanupPwanimateModals();
                if (!evt.detail.xhr || !evt.detail.xhr.responseText.includes('pwanimate-workspace')) {
                    document.documentElement.classList.remove('pwanimate-active');
                    document.body.classList.remove('pwanimate-active');
                }
            }
        });

        document.body.addEventListener('htmx:afterSwap', function (evt) {
            if (document.getElementById('pwanimate-workspace')) {
                initPwanimate();
            } else {
                document.documentElement.classList.remove('pwanimate-active');
                document.body.classList.remove('pwanimate-active');
            }
        });
    }
})();
