/** Shared drag-to-expand and drag-to-dismiss behavior for mobile sheets. */
(function () {
    'use strict';

    const HANDLE_SELECTOR = [
        '[data-bottom-sheet-handle]', '.comments-modal-handle', '.reel-quick-tools-handle',
        '.people-modal-handle', '.connections-sheet-handle', '.push-sheet-handle-bar',
        '.chooser-drag-handle', '.attachment-sheet-handle', '.pwanimate-attachment-sheet-handle'
    ].join(',');
    let drag = null;

    function resolveSheet(handle) {
        const modal = handle.closest('.modal');
        if (modal) return { root: modal, panel: modal.querySelector('.modal-content'), kind: 'modal' };
        const offcanvas = handle.closest('.offcanvas-bottom');
        if (offcanvas) return { root: offcanvas, panel: offcanvas, kind: 'offcanvas' };
        const push = handle.closest('#push-sheet-container');
        if (push) return { root: push, panel: push, kind: 'push' };
        const chooser = handle.closest('#pwaninet-link-chooser-card');
        if (chooser) return { root: chooser, panel: chooser, kind: 'chooser' };
        const custom = handle.closest('.attachment-modal, .pwanimate-attachment-modal');
        if (custom) return { root: custom, panel: custom.querySelector('.attachment-modal-content, .pwanimate-attachment-modal-content'), kind: 'custom' };
        return null;
    }

    function dismiss(sheet) {
        if (sheet.kind === 'modal' && window.bootstrap?.Modal) window.bootstrap.Modal.getOrCreateInstance(sheet.root).hide();
        else if (sheet.kind === 'offcanvas' && window.bootstrap?.Offcanvas) window.bootstrap.Offcanvas.getOrCreateInstance(sheet.root).hide();
        else if (sheet.kind === 'push') window.dismissPushPromptSheet?.();
        else if (sheet.kind === 'chooser') window.dismissPwaninetLinkChooser?.();
        else if (sheet.kind === 'custom') sheet.root.classList.remove('show');
        window.setTimeout(() => reset(sheet.panel), 450);
    }

    function reset(panel) {
        if (!panel) return;
        panel.style.removeProperty('height');
        panel.style.removeProperty('max-height');
        panel.style.removeProperty('transform');
        panel.style.removeProperty('transition');
        panel.classList.remove('bottom-sheet-is-dragged');
        delete panel.dataset.bottomSheetSize;
    }

    function onPointerMove(event) {
        if (!drag || event.pointerId !== drag.pointerId) return;
        drag.deltaY = event.clientY - drag.startY;
        if (drag.deltaY > 0) {
            drag.panel.style.setProperty('transform', `translate3d(0, ${drag.deltaY}px, 0)`, 'important');
        } else {
            drag.panel.style.removeProperty('transform');
            drag.panel.style.setProperty('height', `${Math.min(drag.maxHeight, drag.startHeight - drag.deltaY)}px`, 'important');
            drag.panel.style.setProperty('max-height', `${drag.maxHeight}px`, 'important');
        }
        if (event.cancelable) event.preventDefault();
    }

    function detachActiveDragListeners() {
        document.removeEventListener('pointermove', onPointerMove);
        document.removeEventListener('pointerup', finish);
        document.removeEventListener('pointercancel', finish);
    }

    function finish(event) {
        if (!drag || (event.pointerId !== undefined && event.pointerId !== drag.pointerId)) return;
        const current = drag;
        drag = null;
        detachActiveDragListeners();
        if (current.deltaY > 90) {
            current.panel.style.setProperty('transition', 'transform 180ms ease-out', 'important');
            dismiss(current.sheet);
            return;
        }
        if (current.deltaY < -48) {
            current.panel.style.removeProperty('transform');
            current.panel.style.setProperty('transition', 'height 200ms ease-out', 'important');
            current.panel.style.setProperty('height', `${current.maxHeight}px`, 'important');
            current.panel.style.setProperty('max-height', `${current.maxHeight}px`, 'important');
            current.panel.dataset.bottomSheetSize = 'expanded';
            return;
        }
        current.panel.style.setProperty('transition', 'transform 160ms ease-out', 'important');
        current.panel.style.removeProperty('transform');
        if (current.deltaY >= 0) current.panel.style.removeProperty('height');
        window.setTimeout(() => current.panel.classList.remove('bottom-sheet-is-dragged'), 180);
    }

    document.addEventListener('pointerdown', (event) => {
        if (window.innerWidth >= 1200 || (event.pointerType === 'mouse' && event.button !== 0)) return;
        const handle = event.target.closest?.(HANDLE_SELECTOR);
        if (!handle) return;
        const sheet = resolveSheet(handle);
        if (!sheet?.panel) return;
        const rect = sheet.panel.getBoundingClientRect();
        const viewportHeight = window.visualViewport?.height || window.innerHeight;
        const safeTop = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--pwaninet-safe-area-top')) || 0;
        drag = {
            pointerId: event.pointerId,
            startY: event.clientY,
            panel: sheet.panel,
            sheet,
            startHeight: rect.height,
            maxHeight: Math.max(280, viewportHeight - Math.max(16, safeTop + 8)),
            deltaY: 0
        };
        sheet.panel.classList.add('bottom-sheet-is-dragged');
        sheet.panel.style.setProperty('transition', 'none', 'important');
        try {
            handle.setPointerCapture?.(event.pointerId);
        } catch (_) {}
        document.addEventListener('pointermove', onPointerMove, { passive: false });
        document.addEventListener('pointerup', finish, { passive: true });
        document.addEventListener('pointercancel', finish, { passive: true });
    }, { passive: true });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape' || !drag) return;
        reset(drag.panel);
        drag = null;
        detachActiveDragListeners();
    });
})();
