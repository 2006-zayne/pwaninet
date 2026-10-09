/**
 * PwaniNet Conversation Realtime & Pinning Manager
 * Provides:
 * 1. Bi-directional real-time conversation list updates (sidebar rail & mobile list)
 * 2. Telegram/WhatsApp-style instant re-ordering with pinning (max 3 pinned chats)
 * 3. Rich snippet formatting (🎤 Voice, 📷 Photo, 🎥 Video, 📄 Document)
 * 4. Solid unread badge recalculation & active conversation sync
 * 5. Right-click custom context menu + 3-dot dropdown menu for Pin/Unpin
 */

(function() {
    'use strict';

    // Helper to get CSRF token
    function getCsrfToken() {
        const input = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (input && input.value) return input.value;
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // Helper to show modern floating toast
    function showToast(message, type = 'info') {
        const existing = document.getElementById('chatToastContainer');
        let container = existing;
        if (!container) {
            container = document.createElement('div');
            container.id = 'chatToastContainer';
            container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 10550; display: flex; flex-direction: column; gap: 8px; pointer-events: none;';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : (type === 'success' ? 'success' : 'primary')} shadow-sm border-0 py-2 px-3 m-0 d-flex align-items-center gap-2 fade show`;
        toast.style.cssText = 'pointer-events: auto; border-radius: 12px; font-size: 0.88rem; min-width: 260px; max-width: 360px;';
        
        let icon = 'bi-info-circle-fill';
        if (type === 'success') icon = 'bi-check-circle-fill';
        if (type === 'error') icon = 'bi-exclamation-triangle-fill';

        toast.innerHTML = `
            <i class="bi ${icon} fs-5"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close ms-auto" style="font-size: 0.7rem;"></button>
        `;

        toast.querySelector('.btn-close').addEventListener('click', () => toast.remove());
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 250);
        }, 3500);
    }

    // ─────────────────────────────────────────────────────────────
    // 1. PIN / UNPIN CONTROLLER (MAX 3)
    // ─────────────────────────────────────────────────────────────
    async function togglePin(conversationId, targetAction) {
        if (!conversationId) return;
        const action = targetAction || 'pin';
        const csrfToken = getCsrfToken();

        try {
            const response = await fetch(`/messaging/v1/conversations/${conversationId}/${action}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });

            if (!response.ok) {
                let errorMsg = 'Could not update pin status';
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errData.detail || errorMsg;
                } catch (_) {}
                showToast(errorMsg, 'error');
                return;
            }

            const data = await response.json();
            const isPinned = Boolean(data.is_pinned);
            updateConversationPinState(conversationId, isPinned);

            if (isPinned) {
                showToast('Chat pinned to top', 'success');
            } else {
                showToast('Chat unpinned', 'info');
            }
        } catch (err) {
            console.error('[PIN] Failed to toggle pin:', err);
            showToast('Network error while pinning chat', 'error');
        }
    }

    function updateConversationPinState(conversationId, isPinned) {
        const items = document.querySelectorAll(`[data-conversation-id="${conversationId}"]`);
        items.forEach(item => {
            item.setAttribute('data-is-pinned', isPinned ? 'true' : 'false');
            item.dataset.isPinned = isPinned ? 'true' : 'false';

            // Pin badge in header/time area
            let pinIcon = item.querySelector('.chat-pin-icon');
            if (isPinned) {
                if (!pinIcon) {
                    pinIcon = document.createElement('i');
                    pinIcon.className = 'bi bi-pin-angle-fill text-primary ms-1 chat-pin-icon';
                    pinIcon.title = 'Pinned';
                    pinIcon.style.fontSize = '0.78rem';
                    const targetContainer = item.querySelector('.whatsapp-chat-name, .chat-name, .chat-top-line');
                    if (targetContainer) targetContainer.appendChild(pinIcon);
                }
            } else {
                if (pinIcon) pinIcon.remove();
            }

            // Update dropdown / context menu button text
            const pinBtn = item.querySelector('.pin-toggle-btn');
            if (pinBtn) {
                pinBtn.dataset.action = isPinned ? 'unpin' : 'pin';
                pinBtn.innerHTML = `<i class="bi bi-pin-angle${isPinned ? '-fill' : ''} me-2 text-primary"></i> ${isPinned ? 'Unpin chat' : 'Pin chat'}`;
            }

            // Immediately re-order the conversation within its parent list
            reorderConversationElement(item, isPinned);
        });
    }

    function reorderConversationElement(element, isPinned) {
        // Resolve wrapper if inside .whatsapp-chat-item-wrapper
        const row = element.closest('.whatsapp-chat-item-wrapper') || element;
        const container = row.parentElement;
        if (!container) return;

        if (isPinned) {
            // Pinned chats go to the very top
            if (container.firstChild !== row) {
                container.insertBefore(row, container.firstChild);
            }
        } else {
            // Find all pinned sibling rows in this container
            const pinnedRows = Array.from(container.children).filter(child => {
                if (child === row) return false;
                const inner = child.querySelector('[data-is-pinned="true"]') || (child.getAttribute('data-is-pinned') === 'true' ? child : null);
                return !!inner;
            });

            if (pinnedRows.length > 0) {
                const lastPinned = pinnedRows[pinnedRows.length - 1];
                if (lastPinned.nextSibling !== row) {
                    container.insertBefore(row, lastPinned.nextSibling);
                }
            } else {
                if (container.firstChild !== row) {
                    container.insertBefore(row, container.firstChild);
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 2. REALTIME CONVERSATION UPDATE HANDLER
    // ─────────────────────────────────────────────────────────────
    function updateConversationInList(data) {
        if (!data || !data.conversation_id) return;
        const convId = String(data.conversation_id);
        const activeContainer = document.getElementById('chatMainArea');
        const activeConvId = activeContainer?.dataset?.conversationId;
        const isCurrentActive = Boolean(activeConvId && String(activeConvId) === convId);

        // Query conversation items in sidebar, mobile list, or cards
        const items = document.querySelectorAll(`[data-conversation-id="${convId}"]`);
        if (!items || items.length === 0) return;

        items.forEach(item => {
            // 1. Format snippet with rich icons
            const snippetEl = item.querySelector('.whatsapp-chat-snippet, .chat-preview-text, .conversation-card-preview');
            if (snippetEl) {
                let previewHtml = '';
                const pType = data.preview_type || 'text';
                const previewText = data.message_preview || 'New message';

                if (pType === 'audio' || previewText.includes('Voice message') || previewText.includes('🎤')) {
                    previewHtml = `<i class="bi bi-mic-fill text-primary me-1"></i> ${escapeHtml(previewText.replace('🎤', '').trim())}`;
                } else if (pType === 'image' || previewText.includes('📷') || previewText.includes('Photo')) {
                    previewHtml = `<i class="bi bi-camera-fill text-muted me-1"></i> ${escapeHtml(previewText.replace('📷', '').trim())}`;
                } else if (pType === 'video' || previewText.includes('🎥') || previewText.includes('Video')) {
                    previewHtml = `<i class="bi bi-camera-video-fill text-muted me-1"></i> ${escapeHtml(previewText.replace('🎥', '').trim())}`;
                } else if (pType === 'document' || previewText.includes('📄') || previewText.includes('Document')) {
                    previewHtml = `<i class="bi bi-file-earmark-text-fill text-muted me-1"></i> ${escapeHtml(previewText.replace('📄', '').trim())}`;
                } else {
                    previewHtml = escapeHtml(previewText);
                }

                snippetEl.innerHTML = previewHtml;

                // Professional formatting:
                // If user is currently in active conversation or unread_count is 0 -> muted normal font
                // If message is unread and user is NOT active -> bold text and text-body
                const unreadCountVal = isCurrentActive ? 0 : Number(data.unread_count || 0);
                if (unreadCountVal > 0) {
                    snippetEl.classList.remove('text-muted', 'fw-normal');
                    snippetEl.classList.add('fw-bold', 'text-body', 'unread');
                } else {
                    snippetEl.classList.remove('fw-bold', 'text-body', 'unread');
                    snippetEl.classList.add('text-muted', 'fw-normal');
                }
            }

            // 2. Update Timestamp
            const timeEl = item.querySelector('.whatsapp-chat-time, .chat-time, .conversation-card-time');
            if (timeEl) {
                timeEl.textContent = 'now';
            }

            // 3. Update Unread Badge accurately
            const badgeEl = item.querySelector('.whatsapp-chat-unread-badge, .unread-badge, .conversation-card-badge, .messaging-rail-unread-dot');
            const unreadCount = isCurrentActive ? 0 : Number(data.unread_count || 0);

            if (unreadCount > 0) {
                const displayCount = unreadCount > 99 ? '99+' : unreadCount;
                if (badgeEl) {
                    badgeEl.textContent = displayCount;
                    badgeEl.style.display = '';
                    badgeEl.classList.remove('d-none');
                } else {
                    // Create badge dynamically if it was not in DOM
                    const badgeContainer = item.querySelector('.chat-meta') || item.querySelector('.d-flex.align-items-center.justify-content-between:last-child');
                    if (badgeContainer) {
                        const newBadge = document.createElement('span');
                        newBadge.className = 'whatsapp-chat-unread-badge ms-2 flex-shrink-0';
                        newBadge.textContent = displayCount;
                        badgeContainer.appendChild(newBadge);
                    }
                }
            } else if (badgeEl) {
                badgeEl.style.display = 'none';
                badgeEl.classList.add('d-none');
            }

            // 4. Reorder element with pinning priority (moves up immediately)
            const isPinned = item.getAttribute('data-is-pinned') === 'true';
            reorderConversationElement(item, isPinned);

            // 5. Visual pulse animation
            item.classList.add('chat-item-updated');
            setTimeout(() => item.classList.remove('chat-item-updated'), 1200);
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ─────────────────────────────────────────────────────────────
    // 3. CONTEXT MENU & THREE-DOT DROPDOWN INTERACTION
    // ─────────────────────────────────────────────────────────────
    let activeContextMenu = null;

    function hideContextMenu() {
        if (activeContextMenu) {
            activeContextMenu.remove();
            activeContextMenu = null;
        }
    }

    function showCustomContextMenu(e, item) {
        e.preventDefault();
        e.stopPropagation();
        hideContextMenu();

        const convId = item.dataset.conversationId;
        if (!convId) return;

        const isPinned = item.getAttribute('data-is-pinned') === 'true';
        const href = item.getAttribute('href') || `/messaging/conversation/${convId}/`;

        const menu = document.createElement('div');
        menu.className = 'chat-custom-context-menu shadow-lg bg-body rounded-3 py-1';
        menu.style.cssText = `
            position: fixed;
            top: ${Math.min(e.clientY, window.innerHeight - 150)}px;
            left: ${Math.min(e.clientX, window.innerWidth - 180)}px;
            z-index: 10500;
            min-width: 170px;
            border: 1px solid var(--border-color, rgba(0,0,0,0.12));
            backdrop-filter: blur(12px);
        `;

        menu.innerHTML = `
            <a href="${href}" class="dropdown-item py-2 px-3 small d-flex align-items-center gap-2">
                <i class="bi bi-box-arrow-up-right text-muted"></i> Open chat
            </a>
            <button type="button" class="dropdown-item py-2 px-3 small d-flex align-items-center gap-2 context-pin-btn">
                <i class="bi bi-pin-angle${isPinned ? '-fill' : ''} text-primary"></i> ${isPinned ? 'Unpin chat' : 'Pin to top'}
            </button>
            <button type="button" class="dropdown-item py-2 px-3 small d-flex align-items-center gap-2 context-read-btn">
                <i class="bi bi-check2-all text-info"></i> Mark as read
            </button>
        `;

        menu.querySelector('.context-pin-btn').addEventListener('click', (ev) => {
            ev.stopPropagation();
            hideContextMenu();
            togglePin(convId, isPinned ? 'unpin' : 'pin');
        });

        menu.querySelector('.context-read-btn').addEventListener('click', async (ev) => {
            ev.stopPropagation();
            hideContextMenu();
            try {
                await fetch(`/messaging/v1/conversations/${convId}/mark_read/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrfToken() }
                });
                const badge = item.querySelector('.whatsapp-chat-unread-badge, .unread-badge');
                if (badge) badge.style.display = 'none';
                const snippet = item.querySelector('.whatsapp-chat-snippet, .chat-preview-text');
                if (snippet) snippet.classList.remove('unread');
                showToast('Marked as read', 'success');
            } catch (err) {
                console.error('Error marking as read:', err);
            }
        });

        document.body.appendChild(menu);
        activeContextMenu = menu;
    }

    // Mark conversation as read helper
    async function markConversationAsRead(conversationId) {
        if (!conversationId) return;
        const convStr = String(conversationId);

        // Optimistic DOM update across all items representing this conversation
        const items = document.querySelectorAll(`[data-conversation-id="${convStr}"]`);
        items.forEach(item => {
            const wrapper = item.closest('.whatsapp-chat-item-wrapper, .chat-row-wrapper') || item;
            const badge = wrapper.querySelector('.whatsapp-chat-unread-badge, .unread-badge, .conversation-card-badge, .messaging-rail-unread-dot');
            if (badge) {
                badge.style.display = 'none';
                badge.classList.add('d-none');
            }
            const snippet = wrapper.querySelector('.whatsapp-chat-snippet, .chat-preview-text, .conversation-card-preview');
            if (snippet) {
                snippet.classList.remove('fw-bold', 'unread', 'text-body');
                snippet.classList.add('text-muted', 'fw-normal');
            }
        });

        try {
            await fetch(`/messaging/v1/conversations/${convStr}/mark_read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            });
            showToast('Marked as read', 'success');
        } catch (err) {
            console.error('[MARK_READ] Error marking conversation as read:', err);
        }
    }

    // Capture-phase listener: intercept pin and mark-read before any anchor clicks or navigation
    function handleItemActionClick(e) {
        const pinBtn = e.target.closest('.pin-toggle-btn, .context-pin-btn');
        if (pinBtn) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
            const convId = pinBtn.dataset.conversationId ||
                           pinBtn.closest('[data-conversation-id]')?.dataset?.conversationId ||
                           pinBtn.closest('.whatsapp-chat-item-wrapper, .chat-row-wrapper')?.querySelector('[data-conversation-id]')?.dataset?.conversationId;
            const action = pinBtn.dataset.action || 'pin';
            togglePin(convId, action);
            hideContextMenu();
            return false;
        }

        const markReadBtn = e.target.closest('.mark-read-btn, .context-read-btn');
        if (markReadBtn) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
            const convId = markReadBtn.dataset.conversationId ||
                           markReadBtn.closest('[data-conversation-id]')?.dataset?.conversationId ||
                           markReadBtn.closest('.whatsapp-chat-item-wrapper, .chat-row-wrapper')?.querySelector('[data-conversation-id]')?.dataset?.conversationId;
            if (convId) {
                markConversationAsRead(convId);
            }
            hideContextMenu();
            return false;
        }
    }

    // Attach in capture phase (true) so it intercepts ahead of any bubbling links
    document.addEventListener('click', handleItemActionClick, true);

    // Attach global click listeners in bubble phase
    document.addEventListener('click', (e) => {
        handleItemActionClick(e);
        hideContextMenu();
    });

    document.addEventListener('contextmenu', (e) => {
        const item = e.target.closest('.whatsapp-chat-item, .chat-row');
        if (item) {
            showCustomContextMenu(e, item);
        } else {
            hideContextMenu();
        }
    });

    // Cache DOM conversations into offline cache
    async function cacheDOMConversations() {
        if (!window.offlineCache) return;
        try {
            if (!window.offlineCache.db) {
                await window.offlineCache.init();
            }
            const items = document.querySelectorAll('.whatsapp-chat-item, .chat-row');
            const convsToSave = [];
            items.forEach(item => {
                const id = item.dataset.conversationId;
                if (!id) return;
                const name = item.querySelector('.whatsapp-chat-name, .chat-name')?.textContent?.trim() || '';
                const snippet = item.querySelector('.whatsapp-chat-snippet, .chat-preview-text')?.textContent?.trim() || '';
                const isPinned = item.getAttribute('data-is-pinned') === 'true';
                convsToSave.push({
                    id: Number(id) || id,
                    name: name,
                    preview: { text: snippet },
                    is_pinned: isPinned,
                    cached_at: new Date().toISOString()
                });
            });
            if (convsToSave.length > 0 && typeof window.offlineCache.saveConversations === 'function') {
                await window.offlineCache.saveConversations(convsToSave);
            }
        } catch (e) {
            console.warn('[OFFLINE_CACHE] Error auto-caching conversations from list:', e);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', cacheDOMConversations);
    } else {
        cacheDOMConversations();
    }

    // Mark conversation as active, reset unread state to muted, and move up under pinned
    function markConversationAsActive(convId) {
        if (!convId) return;
        const convStr = String(convId);
        document.querySelectorAll(`[data-conversation-id]`).forEach(item => {
            const rowConvId = String(item.dataset.conversationId || '');
            if (rowConvId === convStr) {
                item.classList.add('active');
                const badge = item.querySelector('.whatsapp-chat-unread-badge, .unread-badge, .messaging-rail-unread-dot');
                if (badge) {
                    badge.style.display = 'none';
                    badge.classList.add('d-none');
                }
                const snippet = item.querySelector('.whatsapp-chat-snippet, .chat-preview-text, .conversation-card-preview');
                if (snippet) {
                    snippet.classList.remove('fw-bold', 'unread', 'text-body');
                    snippet.classList.add('text-muted', 'fw-normal');
                }
            } else if (item.classList.contains('whatsapp-chat-item') || item.classList.contains('chat-row') || item.classList.contains('messaging-rail-avatar-link')) {
                item.classList.remove('active');
            }
        });
    }

    // Dropdown open/close event listeners to elevate wrapper z-index and prevent clipping
    document.addEventListener('show.bs.dropdown', function(e) {
        const row = e.target.closest('.whatsapp-chat-item-wrapper, .whatsapp-chat-item, .chat-row');
        if (row) row.classList.add('dropdown-open');
    });

    document.addEventListener('hidden.bs.dropdown', function(e) {
        const row = e.target.closest('.whatsapp-chat-item-wrapper, .whatsapp-chat-item, .chat-row');
        if (row) row.classList.remove('dropdown-open');
    });

    // Immediate click interaction on conversation items in rail
    document.addEventListener('click', (e) => {
        const chatItem = e.target.closest('.whatsapp-chat-item, .chat-row, .messaging-rail-avatar-link');
        if (chatItem && !e.target.closest('.dropdown, .chat-item-dropdown, button, .pin-toggle-btn, .mark-read-btn')) {
            const convId = chatItem.dataset.conversationId;
            if (convId) {
                markConversationAsActive(convId);
            }
        }

        // Dedicated Media button in desktop/mobile header, or 3-dots dropdown View Media
        const mediaBtn = e.target.closest('#headerMediaBtn, #headerMobileMediaBtn, #whatsappMediaRailToggleBtn, #viewMediaBtn, #headerProfileTrigger');
        if (mediaBtn) {
            e.preventDefault();
            e.stopPropagation();
            toggleMediaRail('tab-media-btn');
            return;
        }

        const infoBtn = e.target.closest('#headerInfoTrigger');
        if (infoBtn) {
            e.preventDefault();
            e.stopPropagation();
            toggleMediaRail('tab-media-btn');
            return;
        }

        const closeBtn = e.target.closest('#closeRightRailBtn');
        if (closeBtn) {
            e.preventDefault();
            e.stopPropagation();
            closeMediaRail();
            return;
        }
    });

    let lastMediaRailToggleTime = 0;

    function openMediaRail(tabId) {
        const rightRail = document.getElementById('whatsappRightRail');
        const layout = document.getElementById('whatsappLayout');
        if (!rightRail) return;

        rightRail.classList.remove('d-none');
        rightRail.classList.add('open');
        rightRail.style.setProperty('display', 'flex', 'important');
        if (layout) layout.classList.add('whatsapp-media-rail-open');
        document.body.classList.add('whatsapp-media-rail-open');

        const targetTabId = tabId || 'tab-media-btn';
        const tabEl = document.getElementById(targetTabId);
        if (tabEl) {
            try {
                if (window.bootstrap && bootstrap.Tab) {
                    const tab = bootstrap.Tab.getOrCreateInstance(tabEl);
                    tab.show();
                } else {
                    tabEl.click();
                }
            } catch (e) {
                tabEl.click();
            }
        }

        const mediaType = targetTabId.replace('tab-', '').replace('-btn', '') || 'media';
        loadMediaTab(mediaType);
    }

    function closeMediaRail() {
        const rightRail = document.getElementById('whatsappRightRail');
        const layout = document.getElementById('whatsappLayout');
        if (!rightRail) return;

        rightRail.classList.remove('open');
        rightRail.classList.add('d-none');
        rightRail.style.setProperty('display', 'none', 'important');
        if (layout) layout.classList.remove('whatsapp-media-rail-open');
        document.body.classList.remove('whatsapp-media-rail-open');
    }

    function toggleMediaRail(tabId) {
        const now = Date.now();
        if (now - lastMediaRailToggleTime < 300) {
            return; // Debounce double-clicks and bubbling events
        }
        lastMediaRailToggleTime = now;

        const rightRail = document.getElementById('whatsappRightRail');
        if (!rightRail) return;

        const isOpen = rightRail.classList.contains('open') &&
                       !rightRail.classList.contains('d-none') &&
                       rightRail.style.display !== 'none';
        if (isOpen) {
            closeMediaRail();
        } else {
            openMediaRail(tabId);
        }
    }

    function loadMediaTab(type, force = false) {
        const pane = document.getElementById(`tab-${type}-content`);
        if (!pane) return;

        if (!force && pane.dataset.loaded === 'true') {
            return; // Don't re-fetch already loaded media
        }

        const chatContainer = document.getElementById('chatMainArea') || document.querySelector('[data-conversation-id]');
        const convId = chatContainer?.dataset?.conversationId || document.body.dataset.conversationId;
        if (!convId) return;

        pane.innerHTML = `
            <div class="text-center py-5 text-muted small media-tab-placeholder">
                <div class="spinner-border spinner-border-sm text-primary mb-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div>Loading ${type}...</div>
            </div>`;

        fetch(`/messaging/conversation/${convId}/media/?type=${type}&page=1`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('HTTP error ' + response.status);
            return response.text();
        })
        .then(html => {
            pane.innerHTML = html;
            pane.dataset.loaded = 'true';
            if (window.htmx) {
                window.htmx.process(pane);
            }
        })
        .catch(err => {
            console.error('[MEDIA_RAIL] Failed to load tab ' + type + ':', err);
            pane.innerHTML = `
                <div class="text-center py-5 text-muted small">
                    <i class="bi bi-exclamation-circle text-warning fs-3 d-block mb-2"></i>
                    Failed to load ${type}. <br>
                    <button class="btn btn-sm btn-outline-primary mt-2 rounded-pill px-3" onclick="window.loadMediaTab('${type}', true)">Retry</button>
                </div>`;
        });
    }

    // Lazy load when tabs are switched
    document.addEventListener('shown.bs.tab', function(e) {
        const target = e.target;
        if (!target) return;
        const mediaType = target.dataset?.mediaType || (target.id ? target.id.replace('tab-', '').replace('-btn', '') : null);
        if (mediaType && ['media', 'docs', 'audio', 'links'].includes(mediaType)) {
            loadMediaTab(mediaType);
        }
    });

    // Synchronize active conversation on HTMX swap
    document.addEventListener('htmx:afterSwap', (evt) => {
        const target = evt.detail.target;
        if (target && (target.id === 'chatMainAreaWrapper' || target.closest('#chatMainAreaWrapper'))) {
            const chatMainArea = document.getElementById('chatMainArea');
            const newConvId = chatMainArea?.dataset?.conversationId;
            if (newConvId) {
                markConversationAsActive(newConvId);
            }

            // Reset media tabs for the new conversation
            const rightRail = document.getElementById('whatsappRightRail');
            if (rightRail) {
                rightRail.querySelectorAll('.tab-pane[data-loaded="true"]').forEach(pane => {
                    pane.dataset.loaded = 'false';
                });
                if (rightRail.classList.contains('open')) {
                    const activeTabBtn = rightRail.querySelector('.whatsapp-media-tabs .nav-link.active');
                    const mediaType = activeTabBtn?.dataset?.mediaType || 'media';
                    loadMediaTab(mediaType, true);
                }
            }
        }
    });

    // Reconnection and online retry handler
    window.addEventListener('online', () => {
        console.log('[CONV_REALTIME] Network restored: reconnecting and retrying pending messages');
        if (window.webSocketManager && typeof window.webSocketManager.reconnect === 'function' && !window.webSocketManager.isConnected()) {
            window.webSocketManager.reconnect();
        }
        if (window.messageService && typeof window.messageService.processMessageQueue === 'function') {
            window.messageService.processMessageQueue();
        }
    });

    // Expose functions globally on window
    window.updateConversationInList = updateConversationInList;
    window.togglePinConversation = togglePin;
    window.markConversationAsActive = markConversationAsActive;
    window.openMediaRail = openMediaRail;
    window.closeMediaRail = closeMediaRail;
    window.toggleMediaRail = toggleMediaRail;
    window.loadMediaTab = loadMediaTab;

})();
