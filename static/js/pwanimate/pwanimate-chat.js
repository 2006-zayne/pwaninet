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
        const anchor = (element.tagName === 'A') ? element : (typeof element.closest === 'function' ? element.closest('a') : null);
        if (!anchor) return false;
        if (anchor.classList && anchor.classList.contains('pwanimate-citation-badge')) return true;
        if (typeof anchor.closest === 'function') {
            if (anchor.closest('.pwanimate-citations') || anchor.closest('.pwanimate-citation-list')) return true;
        }
        if (typeof anchor.hasAttribute === 'function') {
            if (anchor.hasAttribute('data-pwanimate-resource') || anchor.hasAttribute('data-citation')) return true;
        }
        const ds = anchor.dataset || {};
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
            this.transcript = workspace.querySelector('#pwanimate-transcript');
            this.composerForm = workspace.querySelector('#pwanimate-composer-form');
            this.input = workspace.querySelector('#pwanimate-input');
            this.sendBtn = workspace.querySelector('#pwanimate-send-btn');
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
            this.initMarkdown();
            this.renderExistingMarkdown();
            this.checkCollapsibleUserBubbles();
            requestAnimationFrame(() => this.checkCollapsibleUserBubbles());
            this.bindEvents();
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

                    const badge = e.target.closest('a');
                    if (badge && isPwanimateCitationLink(badge)) {
                        e.preventDefault();
                        const url = badge.getAttribute('href');
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
                            citation: badge.dataset.citation || '',
                            pageNumber: badge.dataset.pageNumber || null,
                            documentId: badge.dataset.documentId || '',
                            documentShareId: badge.dataset.documentShareId || '',
                            fileType: badge.dataset.fileType || '',
                            postId: badge.dataset.postId || '',
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
            const thumbnailUrl = meta.thumbnailUrl || meta.thumbnail_url || '';

            // File type derivation & normalization
            let fileType = (meta.fileType || meta.file_type || meta.file_extension || meta.extension || '').toLowerCase().trim();
            if (fileType.startsWith('.')) fileType = fileType.substring(1);
            if (!fileType) {
                const candidate = (mediaUrl || cleanUrl || '').split('?')[0].split('#')[0];
                const extMatch = candidate.match(/\.([a-zA-Z0-9]+)$/);
                if (extMatch && extMatch[1].length <= 5) fileType = extMatch[1].toLowerCase();
            }

            // Classification
            const isVideo = (meta.resourceType === 'video' || meta.resource_type === 'video' || Boolean(hlsUrl) ||
                /\.(mp4|webm|ogg|m3u8)(\?|#|$)/i.test(mediaUrl || cleanUrl));

            const isImage = !isVideo && (meta.resourceType === 'image' || meta.resource_type === 'image' ||
                /\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)/i.test(mediaUrl || cleanUrl) ||
                ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fileType));

            const isDoc = !isVideo && !isImage && (meta.resourceType === 'document' || meta.resource_type === 'document' ||
                meta.sourceType === 'document' || meta.source_type === 'document' ||
                Boolean(documentShareId) || cleanUrl.includes('/documents/') ||
                ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'txt', 'md', 'csv', 'log'].includes(fileType));

            const isPost = !isVideo && !isImage && !isDoc && (meta.sourceType === 'post' || meta.source_type === 'post' ||
                meta.resourceType === 'post' || meta.resource_type === 'post' ||
                cleanUrl.includes('/post/') || cleanUrl.includes('/posts/'));

            let previewType = 'document';
            if (isVideo) previewType = 'video';
            else if (isImage) previewType = 'image';
            else if (isDoc) previewType = 'document';
            else if (isPost) previewType = 'post';

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
            const description = meta.description || meta.content || meta.snippet || meta.citation ||
                (previewType === 'document' ? 'Official course or academic document from PwaniNet repository.' :
                (previewType === 'post' ? 'Discussion post on PwaniNet.' : 'Resource referenced in this conversation.'));

            return {
                id: documentShareId || postId || cleanUrl,
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
            if (deskBadge) deskBadge.textContent = countStr;
            if (mobBadge) mobBadge.textContent = countStr;
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
                ['pdf', 'docx', 'pptx', 'txt', 'text', 'csv', 'log'].includes(fileType)
            );

            if (details.previewType === 'video' && video) {
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

        openContextRail() {
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

        setGenerating(loading) {
            this.isGenerating = loading;
            if (this.input) this.input.disabled = loading;
            this.updateSendButtonState();
        }

        updateSendButtonState() {
            if (!this.sendBtn) return;
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

            if (hasText) {
                this.sendBtn.disabled = false;
                this.sendBtn.classList.add('is-active');
                this.sendBtn.setAttribute('aria-label', 'Send message');
                this.sendBtn.setAttribute('title', 'Send message (Enter)');
            } else {
                this.sendBtn.disabled = true;
                this.sendBtn.classList.remove('is-active');
                this.sendBtn.setAttribute('aria-label', 'Send message');
                this.sendBtn.setAttribute('title', 'Type a message to send');
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
            this.transcript.appendChild(row);
            this.scrollToBottom();
        }

        async handleSend() {
            if (this.isGenerating) return;
            const text = this.input ? this.input.value.trim() : '';
            if (!text) return;

            // Setup AbortController for modern cancellation support
            this.abortController = new AbortController();

            // Clear input & reset height
            this.input.value = '';
            this.resetTextareaHeight();
            this.updateSendButtonState();

            // Remove empty state if present
            const emptyState = this.transcript.querySelector('#pwanimate-empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // Render optimistic user message
            const userRow = this.appendUserMessage(text);
            this.showTypingIndicator(text);
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
                    signal: this.abortController.signal,
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

                this.appendAssistantMessage(data.answer, data.sources, data.citations, data.fallback_info, data.quota_info, data.people, data.message_id);
                this.scrollToBottom();
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
                    this.showErrorBubble('Network connection error. Please check your internet connection.', text);
                }
            } finally {
                this.abortController = null;
                this.setGenerating(false);
                if (this.input && isFinePointerDevice()) {
                    this.input.focus();
                }
            }
        }

        appendUserMessage(text, messageId = null) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row user';
            if (messageId) {
                row.dataset.messageId = messageId;
            }
            const escaped = escapeHtml(text);
            row.innerHTML = `
                <div class="pwanimate-message-content">
                    <div class="pwanimate-user-bubble-wrapper">
                        <div class="pwanimate-user-bubble" data-raw="${escaped}">${escaped}</div>
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
            this.transcript.appendChild(row);
            this.checkCollapsibleUserBubbles(row);
            requestAnimationFrame(() => this.checkCollapsibleUserBubbles(row));
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
            this.transcript.appendChild(row);

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

        destroy() {
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


        appendAssistantMessage(answer, sources, citations, fallbackInfo, quotaInfo, people = [], messageId = null) {
            const row = document.createElement('div');
            row.className = 'pwanimate-message-row assistant';
            if (messageId) {
                row.dataset.messageId = messageId;
            }

            const parsedHtml = this.renderMarkdownWithMathAndCode(answer);

            let peopleHtml = '';
            if (Array.isArray(people) && people.length > 0) {
                peopleHtml = this.renderPeopleCards(people);
            }

            let citationsHtml = '';
            // If people cards are rendered, omit redundant person items from general sources
            const filteredSources = (Array.isArray(people) && people.length > 0)
                ? (sources || []).filter(src => src.source !== 'user')
                : (sources || []);

            if (Array.isArray(filteredSources) && filteredSources.length > 0) {
                const badges = filteredSources.map((src) => {
                    const title = escapeHtml(src.title || src.citation || 'Document');
                    if (src.url) {
                        return `<a href="${escapeHtml(src.url)}" class="pwanimate-citation-badge" target="_blank" rel="noopener"
                            data-title="${title}"
                            data-source-type="${escapeHtml(src.source || '')}"
                            data-resource-type="${escapeHtml(src.resource_type || '')}"
                            data-media-url="${escapeHtml(src.media_url || '')}"
                            data-thumbnail-url="${escapeHtml(src.thumbnail_url || '')}"
                            data-hls-url="${escapeHtml(src.hls_url || '')}"
                            data-author="${escapeHtml(src.author || '')}"
                            data-citation="${escapeHtml(src.citation || '')}"
                            data-page-number="${escapeHtml(src.page_number || '')}"
                            data-document-id="${escapeHtml(src.document_id || '')}"
                            data-document-share-id="${escapeHtml(src.document_share_id || '')}"
                            data-file-type="${escapeHtml(src.file_type || src.file_extension || '')}">
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
                        <div class="pwanimate-markdown-body" data-raw="${escapeHtml(answer)}">${parsedHtml}</div>
                        ${peopleHtml}
                        ${citationsHtml}
                        ${fallbackHtml}
                    </div>
                    <div class="pwanimate-message-actions assistant-actions">
                        <button type="button" class="btn pwanimate-action-btn copy-btn" title="Copy answer" aria-label="Copy answer">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                </div>
            `;

            this.transcript.appendChild(row);
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
                                    <div class="d-flex align-items-center justify-content-end mt-2 pt-1 border-top" style="border-color: var(--pwanimate-border) !important;">
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
