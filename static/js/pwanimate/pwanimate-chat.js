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

    class PwanimateChat {
        constructor(workspace) {
            this.workspace = workspace;
            this.conversationId = workspace.dataset.conversationId || null;
            this.transcript = workspace.querySelector('#pwanimate-transcript');
            this.composerForm = workspace.querySelector('#pwanimate-composer-form');
            this.input = workspace.querySelector('#pwanimate-input');
            this.sendBtn = workspace.querySelector('#pwanimate-send-btn');
            this.sidebarList = workspace.querySelector('#pwanimate-sidebar-list');
            this.mobileList = workspace.querySelector('#pwanimate-mobile-list');
            this.quotaStatusEl = document.getElementById('pwanimate-quota-status');
            this.isGenerating = false;
            this.resizeFrame = null;

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
            this.initMarkdown();
            this.renderExistingMarkdown();
            this.bindEvents();
            this.updateQuotaStatus({ models: this.getDefaultModels() });
            this.updateSelectedModelUI();
            if (this.input && this.input.value) {
                this.resizeTextarea();
            }
            this.scrollToBottom(false);
            this.fetchQuotaStatus();
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
                if (!window.marked) return;
                const mdElements = this.transcript.querySelectorAll('.pwanimate-markdown-body[data-raw]');
                mdElements.forEach((el) => {
                    const raw = el.getAttribute('data-raw');
                    if (raw) {
                        try {
                            el.innerHTML = window.marked.parse(raw);
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

        bindEvents() {
            // Form submission
            if (this.composerForm) {
                this.composerForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleSend();
                });
            }

            // Keyboard navigation in textarea
            if (this.input) {
                this.input.addEventListener('keydown', (e) => {
                    if (e.isComposing || e.keyCode === 229) {
                        return;
                    }
                    if (e.key === 'Enter' && !e.shiftKey) {
                        if (isFinePointerDevice()) {
                            e.preventDefault();
                            this.handleSend();
                        }
                        // On touch/coarse devices, do not preventDefault: native newline is inserted
                    }
                });

                // Auto-resize textarea with rAF batching to eliminate synchronous layout thrashing
                this.input.addEventListener('input', () => {
                    this.scheduleTextareaResize();
                });
            }

            // Suggestion chips and Citation badges
            if (this.transcript) {
                this.transcript.addEventListener('click', (e) => {
                    const chip = e.target.closest('.pwanimate-suggestion-chip');
                    if (chip && chip.dataset.prompt) {
                        e.preventDefault();
                        if (this.input) {
                            this.input.value = chip.dataset.prompt;
                            this.handleSend();
                        }
                        return;
                    }

                    const badge = e.target.closest('a.pwanimate-citation-badge');
                    if (badge) {
                        e.preventDefault();
                        const url = badge.getAttribute('href');
                        let title = 'Resource Preview';
                        const span = badge.querySelector('span');
                        if (span) {
                            title = span.textContent;
                        }
                        this.previewResource(url, title);
                    }
                });
            }

            // Delete conversation buttons (delegated on document so desktop sidebar buttons work)
            document.addEventListener('click', (e) => {
                const deleteBtn = e.target.closest('.pwanimate-conversation-delete');
                if (deleteBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const convId = deleteBtn.dataset.conversationId;
                    if (convId) {
                        this.handleDeleteConversation(convId);
                    }
                }
            });

            // Close desktop preview button
            const closeDesktopPreview = document.getElementById('desktopPreviewCloseBtn');
            if (closeDesktopPreview) {
                closeDesktopPreview.addEventListener('click', () => {
                    const emptyState = document.getElementById('desktopPreviewEmpty');
                    const activeState = document.getElementById('desktopPreviewActive');
                    if (emptyState && activeState) {
                        activeState.classList.remove('d-flex');
                        activeState.classList.add('d-none');
                        emptyState.classList.remove('d-none');
                        const iframe = document.getElementById('desktopPreviewIframe');
                        if (iframe) iframe.src = '';
                    }
                });
            }

            // Model dropdown selection
            document.addEventListener('click', (e) => {
                const opt = e.target.closest('.pwanimate-model-option');
                if (opt) {
                    e.preventDefault();
                    const provider = opt.dataset.provider || '';
                    const model = opt.dataset.model || '';
                    const display = opt.dataset.display || 'Auto';
                    const providerLabel = opt.dataset.providerLabel || '';
                    this.selectModel(provider, model, display, providerLabel);
                }
            });

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

        previewResource(url, title) {
            if (window.innerWidth >= 1200) {
                // Desktop Right Rail
                const emptyState = document.getElementById('desktopPreviewEmpty');
                const activeState = document.getElementById('desktopPreviewActive');
                if (emptyState && activeState) {
                    emptyState.classList.add('d-none');
                    activeState.classList.remove('d-none');
                    activeState.classList.add('d-flex');
                    document.getElementById('desktopPreviewTitle').textContent = title;
                    document.getElementById('desktopPreviewOriginalLink').href = url;
                    const iframe = document.getElementById('desktopPreviewIframe');
                    iframe.classList.add('d-none');
                    iframe.onload = () => iframe.classList.remove('d-none');
                    iframe.src = url;
                }
            } else {
                // Mobile Bottom Sheet
                document.getElementById('previewSheetTitle').textContent = title;
                document.getElementById('previewSheetOriginalLink').href = url;
                const iframe = document.getElementById('previewSheetIframe');
                iframe.classList.add('d-none');
                iframe.onload = () => iframe.classList.remove('d-none');
                iframe.src = url;
                
                const sheetEl = document.getElementById('pwanimateResourcePreviewSheet');
                if (sheetEl && window.bootstrap) {
                    let offcanvas = bootstrap.Offcanvas.getInstance(sheetEl);
                    if (!offcanvas) offcanvas = new bootstrap.Offcanvas(sheetEl);
                    offcanvas.show();
                }
            }
        }

        scrollToBottom(smooth = true) {
            if (!this.transcript) return;
            this.transcript.scrollTo({
                top: this.transcript.scrollHeight,
                behavior: smooth ? 'smooth' : 'auto'
            });
        }

        setGenerating(loading) {
            this.isGenerating = loading;
            if (this.input) this.input.disabled = loading;
            if (this.sendBtn) this.sendBtn.disabled = loading;
        }

        async handleSend() {
            if (this.isGenerating) return;
            const text = this.input ? this.input.value.trim() : '';
            if (!text) return;

            // Clear input & reset height
            this.input.value = '';
            this.resetTextareaHeight();

            // Remove empty state if present
            const emptyState = this.transcript.querySelector('#pwanimate-empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // Render optimistic user message
            this.appendUserMessage(text);
            this.showTypingIndicator();
            this.setGenerating(true);
            this.scrollToBottom();

            const csrfToken = getCsrfToken();

            try {
                const payload = {
                    message: text
                };
                if (this.conversationId) {
                    payload.conversation_id = this.conversationId;
                }
                if (this.selectedProvider) {
                    payload.provider = this.selectedProvider;
                }
                if (this.selectedModel) {
                    payload.model = this.selectedModel;
                }

                const response = await fetch('/api/pwanimate/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                // Handle conversation ID update even if there's an error, to prevent spawning new conversations
                if (data.conversation_id && !this.conversationId) {
                    this.conversationId = data.conversation_id;
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
                    this.showErrorBubble(errMsg, text);
                    this.refreshConversationsList();
                    if (data.quota_status) {
                        this.updateQuotaStatus(data.quota_status);
                    }
                    return;
                }

                this.removeTypingIndicator();
                this.appendAssistantMessage(data.answer, data.sources, data.citations, data.fallback_info, data.quota_info);
                this.scrollToBottom();
                this.refreshConversationsList();
                this.updateQuotaStatus(data.quota_status);
                this.updateActiveModelChip(data.quota_info);

            } catch (err) {
                console.error('[Pwanimate] Chat network error:', err);
                this.removeTypingIndicator();
                this.showErrorBubble('Network connection error. Please check your internet connection.', text);
            } finally {
                this.setGenerating(false);
                if (this.input && isFinePointerDevice()) {
                    this.input.focus();
                }
            }
        }

        appendUserMessage(text) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row user';
            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-user-bubble">${escapeHtml(text)}</div>
                </div>
            `;
            this.transcript.appendChild(row);
        }

        showTypingIndicator() {
            this.removeTypingIndicator();
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant';
            row.id = 'pwanimate-typing-row';
            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-typing-indicator" aria-label="Pwanimate is thinking">
                        <div class="pwanimate-typing-dot"></div>
                        <div class="pwanimate-typing-dot"></div>
                        <div class="pwanimate-typing-dot"></div>
                    </div>
                </div>
            `;
            this.transcript.appendChild(row);
        }

        removeTypingIndicator() {
            const typingRow = this.transcript.querySelector('#pwanimate-typing-row');
            if (typingRow) {
                typingRow.remove();
            }
        }

        appendAssistantMessage(answer, sources, citations, fallbackInfo, quotaInfo) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant';

            let parsedHtml = escapeHtml(answer);
            if (window.marked && typeof window.marked.parse === 'function') {
                try {
                    parsedHtml = window.marked.parse(answer);
                } catch (e) {
                    console.warn('[Pwanimate] Parse error:', e);
                }
            }

            let citationsHtml = '';
            if (Array.isArray(sources) && sources.length > 0) {
                const badges = sources.map((src) => {
                    const title = escapeHtml(src.title || src.citation || 'Document');
                    if (src.url) {
                        return `<a href="${escapeHtml(src.url)}" class="pwanimate-citation-badge" target="_blank" rel="noopener">
                            <i class="bi bi-link-45deg"></i>
                            <span>${title}</span>
                        </a>`;
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
            } else if (Array.isArray(citations) && citations.length > 0) {
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
            if (quotaInfo && quotaInfo.switched) {
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
                fallbackHtml = `
                    <div class="pwanimate-fallback-notice">
                        <i class="bi bi-arrow-repeat"></i>
                        <span>Answered by <strong>${used}</strong> (${orig} quota exceeded)</span>
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
                        <div class="pwanimate-markdown-body">${parsedHtml}</div>
                        ${citationsHtml}
                        ${fallbackHtml}
                    </div>
                </div>
            `;

            this.transcript.appendChild(row);
        }

        showErrorBubble(message, originalText) {
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
                    if (this.input) {
                        this.input.value = originalText;
                        this.handleSend();
                    }
                });
            }

            this.transcript.appendChild(row);
            this.scrollToBottom();
        }

        async handleDeleteConversation(convId) {
            if (!confirm('Are you sure you want to delete this conversation?')) return;

            const csrfToken = getCsrfToken();
            try {
                const res = await fetch(`/api/pwanimate/conversations/${convId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });

                if (res.status === 204 || res.ok) {
                    // Remove from desktop and mobile lists
                    const items = this.workspace.querySelectorAll(`.pwanimate-conversation-item[data-id="${convId}"]`);
                    items.forEach((it) => it.remove());

                    // If active conversation was deleted, navigate to index
                    if (this.conversationId === convId) {
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
                html = `<div class="text-center text-muted p-3 x-small">No conversations yet.</div>`;
            } else {
                html = conversations.map((c) => {
                    const isActive = this.conversationId === c.id ? 'active' : '';
                    const title = escapeHtml(c.title || 'New Conversation');
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
                                <div class="pwanimate-conversation-time">just now</div>
                            </div>
                            <button type="button"
                                    class="pwanimate-conversation-delete"
                                    data-conversation-id="${c.id}"
                                    aria-label="Delete conversation"
                                    title="Delete conversation"
                                    onclick="event.stopPropagation();">
                                <i class="bi bi-trash3"></i>
                            </button>
                        </div>
                    `;
                }).join('');
            }

            if (this.sidebarList) {
                this.sidebarList.innerHTML = html;
                if (window.htmx) window.htmx.process(this.sidebarList);
            }
            if (this.mobileList) {
                this.mobileList.innerHTML = html;
                if (window.htmx) window.htmx.process(this.mobileList);
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
            document.body.classList.remove('pwanimate-active');
            return;
        }
        document.body.classList.add('pwanimate-active');
        if (workspace.dataset.initialized === 'true') return;
        workspace.dataset.initialized = 'true';
        new PwanimateChat(workspace);
    }

    window.initPwanimate = initPwanimate;

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
                if (!evt.detail.xhr || !evt.detail.xhr.responseText.includes('pwanimate-workspace')) {
                    document.body.classList.remove('pwanimate-active');
                }
            }
        });

        document.body.addEventListener('htmx:afterSwap', function (evt) {
            if (document.getElementById('pwanimate-workspace')) {
                initPwanimate();
            } else {
                document.body.classList.remove('pwanimate-active');
            }
        });
    }
})();
