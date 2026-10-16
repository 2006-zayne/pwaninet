/**
 * Upload Manager page (Phase 3): renders account-wide history from
 * GET /api/uploads/ with status filters, search, retry/cancel actions,
 * and live progress from the ResumableUpload engine.
 */
(function () {
    'use strict';

    const listEl = document.getElementById('um-list');
    const emptyEl = document.getElementById('um-empty');
    const searchEl = document.getElementById('um-search');
    const filtersEl = document.getElementById('um-filters');
    const refreshBtn = document.getElementById('um-refresh');

    if (!listEl) return;

    let activeFilter = '';
    let searchTerm = '';
    let refreshTimer = null;

    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const match = document.cookie.match(/(?:^|;\s*)(csrftoken|vasto_local_csrftoken)=([^;]*)/);
        return match ? decodeURIComponent(match[2]) : '';
    }

    async function api(path, method, body) {
        const headers = { 'X-CSRFToken': getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest' };
        const opts = { method: method || 'GET', headers, credentials: 'same-origin' };
        if (body !== undefined) {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        const res = await fetch('/api/uploads/' + path, opts);
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error((data && data.detail) || `Request failed: ${res.status}`);
        return data;
    }

    function formatBytes(n) {
        if (!n && n !== 0) return '—';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        let v = n;
        while (v >= 1024 && i < units.length - 1) {
            v /= 1024;
            i += 1;
        }
        return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
    }

    function statusBadge(statusValue) {
        const map = {
            uploading: 'primary', verifying: 'primary', processing: 'warning',
            publishing: 'warning', queued: 'secondary', preparing: 'secondary',
            paused: 'secondary', completed: 'success', failed: 'danger', cancelled: 'dark',
        };
        return `<span class="badge bg-${map[statusValue] || 'secondary'}">${statusValue}</span>`;
    }

    function card(item) {
        const pct = item.total_bytes
            ? Math.round((100 * (item.progress_bytes || 0)) / item.total_bytes)
            : 0;
        const canRetry = item.status === 'failed' || item.status === 'paused';
        const canCancel = ['queued', 'preparing', 'uploading', 'verifying', 'paused', 'failed'].includes(item.status);
        const canDelete = item.status !== 'uploading' && item.status !== 'verifying' && item.status !== 'processing';
        const queueInfo = item.queue_position ? `<span class="badge bg-info ms-2">#${item.queue_position}</span>` : '';
        return `
        <div class="card" data-id="${item.id}">
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-center gap-2">
                    <div class="text-truncate">
                        <strong class="d-block text-truncate">${item.filename}${queueInfo}</strong>
                        <small class="text-muted">${formatBytes(item.total_bytes)} · ${item.session_protocol || ''}</small>
                    </div>
                    <div>${statusBadge(item.status)}</div>
                </div>
                <div class="progress my-2" style="height: 6px;">
                    <div class="progress-bar" role="progressbar" style="width: ${pct}%;" data-progress></div>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted" data-note>${item.error_message || `${pct}%`}</small>
                    <div class="btn-group btn-group-sm">
                        ${canRetry ? '<button class="btn btn-outline-primary" data-action="retry">Retry</button>' : ''}
                        ${canCancel ? '<button class="btn btn-outline-danger" data-action="cancel">Cancel</button>' : ''}
                        ${canDelete ? '<button class="btn btn-outline-secondary" data-action="delete">Delete</button>' : ''}
                        ${item.post ? `<a class="btn btn-outline-success" href="/post/${item.post_share_id || ''}/">View post</a>` : ''}
                    </div>
                </div>
            </div>
        </div>`;
    }

    async function load() {
        const params = new URLSearchParams();
        if (activeFilter) params.set('status', activeFilter);
        const data = await api('?' + params.toString(), 'GET');
        let items = data.results || [];
        if (searchTerm) {
            items = items.filter((i) => (i.filename || '').toLowerCase().includes(searchTerm));
        }
        listEl.innerHTML = items.map(card).join('');
        emptyEl.hidden = items.length > 0;
    }

    async function scheduleRefresh() {
        if (refreshTimer) clearTimeout(refreshTimer);
        refreshTimer = setTimeout(async () => {
            try {
                await load();
            } finally {
                scheduleRefresh();
            }
        }, 10000);
    }

    listEl.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const id = btn.closest('.card').dataset.id;
        btn.disabled = true;
        try {
            await api(`${id}/${btn.dataset.action}/`, 'POST', {});
            await load();
        } catch (err) {
            btn.disabled = false;
            alert(err.message);
        }
    });

    filtersEl.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-filter]');
        if (!btn) return;
        activeFilter = btn.dataset.filter;
        filtersEl.querySelectorAll('button').forEach((b) => {
            const on = b === btn;
            b.classList.toggle('btn-primary', on);
            b.classList.toggle('btn-outline-primary', !on);
        });
        load().catch(() => {});
    });

    searchEl.addEventListener('input', () => {
        searchTerm = searchEl.value.trim().toLowerCase();
        load().catch(() => {});
    });

    refreshBtn.addEventListener('click', () => load().catch(() => {}));

    window.addEventListener('resumable-upload-progress', (e) => {
        const { serverId, loaded, total } = e.detail;
        const el = listEl.querySelector(`[data-id="${serverId}"]`);
        if (!el) return;
        const pct = total ? Math.round((100 * loaded) / total) : 0;
        const bar = el.querySelector('[data-progress]');
        const note = el.querySelector('[data-note]');
        if (bar) bar.style.width = `${pct}%`;
        if (note) note.textContent = `${pct}%`;
    });

    load().then(scheduleRefresh).catch(() => scheduleRefresh());
    window.addEventListener('beforeunload', () => {
        if (refreshTimer) clearTimeout(refreshTimer);
    });

    // Auto-resume locally persisted uploads on web. On Android the native
    // worker sweep runs first (see native_upload.js); the engine only takes
    // sessions the native side does not own.
    if (!window.NativeUploads || !window.NativeUploads.isAvailable()) {
        if (window.resumableUpload) {
            window.resumableUpload.resumeAll().catch(() => {});
        }
    }
})();
