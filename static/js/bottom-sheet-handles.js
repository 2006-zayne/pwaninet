/**
 * Shared drag behavior for mobile bottom-sheet grab handles.
 * Drag up to expand, drag down to collapse, and pull down far enough to close.
 */
(function () {
    'use strict';

    const HANDLE_SELECTOR = [
        '[data-bottom-sheet-handle]',
        '.comments-modal-handle',
        '.reel-quick-tools-handle',
        '.people-modal-handle',
        '.connections-sheet-handle',
        '.push-sheet-handle-bar',
        '.chooser-drag-handle',
        '.attachment-sheet-handle',
        '.pwanimate-attachment-sheet-handle'
    ].join(', ');

    let activeDrag = null;

    function findSheet(handle) {
        const modal = handle.closest('.modal');
        if (modal) {
            const panel = modal.querySelector('.modal-content');
            return panel ? { kind: 'modal', root: modal, panel } : null;
        }

        const offcanvas = handle.closest('.offcanvas-bottom');
        if (offcanvas) return { kind: 'offcanvas', root: offcanvas, panel: offcanvas };

        const pushSheet = handle.closest('#push-sheet-container');
        if (pushSheet) return { kind: 'push', root: pushSheet, panel: pushSheet };

        const chooser = handle.closest('#pwaninet-link-chooser-card');
        if (chooser) return { kind: 'chooser', root: chooser, panel: chooser };

        const attachmentModal = handle.closest('.attachment-modal, .pwanimate-attachment-modal');
        if (attachmentModal) {
            const panel = attachmentModal.querySelector('.attachment-modal-content, .pwanimate-attachment-modal-content');
            return panel ? { kind: 'custom', root: attachmentModal, panel } : null;
        }

        return null;
    }

    function closeSheet(sheet) {
        if (sheet.kind === 'modal' && window.bootstrap?.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(sheet.root).hide();
        } else if (sheet.kind === 'offcanvas' && window.bootstrap?.Offcanvas) {
            window.bootstrap.Offcanvas.getOrCreateInstance(sheet.root).hide();
        } else if (sheet.kind === 'push' && typeof window.dismissPushPromptSheet === 'function') {
            window.dismissPushPromptSheet();
        } else if (sheet.kind === 'chooser' && typeof window.dismissPwaninetLinkChooser === 'function') {
            window.dismissPwaninetLinkChooser();
        } else if (sheet.kind === 'custom') {
            sheet.root.classList.remove('show');
        }

        window.setTimeout(() => {
            const stillVisible = sheet.root.classList.contains('show') ||
                sheet.root.classList.contains('visible') ||
                sheet.root.classList.contains('showing');
            if (stillVisible) return;
            sheet.panel.style.removeProperty('height');
            sheet.panel.style.removeProperty('max-height');
            sheet.panel.style.removeProperty('transition');
            sheet.panel.classList.remove('bottom-sheet-is-dragged');
            delete sheet.panel.dataset.bottomSheetSize;
        }, 420);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(value, max));
    }

    document.addEventListener('pointerdown', (event) => {
        const handle = event.target.closest(HANDLE_SELECTOR);
        if (!handle || event.button > 0 || window.innerWidth >= 1200) return;

        const sheet = findSheet(handle);
        if (!sheet) return;

        const rect = sheet.panel.getBoundingClientRect();
        const viewportHeight = window.visualViewport?.height || window.innerHeight;
        const safeTop = Number.parseFloat(getComputedStyle(document.documentElement)
            .getPropertyValue('--pwaninet-safe-area-top')) || 0;
        const maxHeight = Math.max(280, viewportHeight - Math.max(16, safeTop + 8));
        const minHeight = Math.min(240, rect.height);

        activeDrag = {
            pointerId: event.pointerId,
            startY: event.clientY,
            lastY: event.clientY,
            lastTime: performance.now(),
            velocityY: 0,
            startHeight: rect.height,
            currentHeight: rect.height,
            minHeight,
            maxHeight,
            originalHeight: sheet.panel.style.getPropertyValue('height'),
            originalMaxHeight: sheet.panel.style.getPropertyValue('max-height'),
            originalTransition: sheet.panel.style.getPropertyValue('transition'),
            sheet
        };

        sheet.panel.classList.add('bottom-sheet-is-dragged');
        sheet.panel.style.transition = 'none';
        handle.setPointerCapture?.(event.pointerId);
        event.preventDefault();
    });

    document.addEventListener('pointermove', (event) => {
        if (!activeDrag || event.pointerId !== activeDrag.pointerId) return;
        const drag = activeDrag;
        const now = performance.now();
        const deltaY = event.clientY - drag.startY;
        const elapsed = Math.max(1, now - drag.lastTime);
        drag.velocityY = (event.clientY - drag.lastY) / elapsed;
        drag.lastY = event.clientY;
        drag.lastTime = now;
        drag.currentHeight = clamp(drag.startHeight - deltaY, drag.minHeight, drag.maxHeight);
        drag.sheet.panel.style.setProperty('height', `${drag.currentHeight}px`, 'important');
        drag.sheet.panel.style.setProperty('max-height', `${drag.maxHeight}px`, 'important');
        event.preventDefault();
    });

    function finishDrag(event) {
        if (!activeDrag || (event.pointerId !== undefined && event.pointerId !== activeDrag.pointerId)) return;
        const drag = activeDrag;
        activeDrag = null;

        const deltaY = event.clientY - drag.startY;
        if (Math.abs(deltaY) < 24) {
            drag.sheet.panel.style.setProperty('height', drag.originalHeight);
            drag.sheet.panel.style.setProperty('max-height', drag.originalMaxHeight);
            drag.sheet.panel.style.setProperty('transition', drag.originalTransition);
            drag.sheet.panel.classList.remove('bottom-sheet-is-dragged');
            return;
        }
        const shouldClose = deltaY > 120 || (deltaY > 48 && drag.velocityY > 0.8);
        if (shouldClose) {
            closeSheet(drag.sheet);
            return;
        }

        const expandedHeight = drag.maxHeight;
        const collapsedHeight = Math.min(
            expandedHeight,
            Math.max(drag.minHeight, Math.min(drag.startHeight, window.innerHeight * 0.56))
        );
        const targetHeight = deltaY < -48
            ? expandedHeight
            : deltaY > 36
                ? collapsedHeight
                : (drag.currentHeight >= (expandedHeight + collapsedHeight) / 2 ? expandedHeight : collapsedHeight);

        drag.sheet.panel.style.setProperty('transition', 'height 220ms cubic-bezier(0.2, 0.8, 0.2, 1)', 'important');
        drag.sheet.panel.style.setProperty('height', `${targetHeight}px`, 'important');
        drag.sheet.panel.style.setProperty('max-height', `${expandedHeight}px`, 'important');
        drag.sheet.panel.dataset.bottomSheetSize = targetHeight === expandedHeight ? 'expanded' : 'collapsed';
    }

    document.addEventListener('pointerup', finishDrag);
    document.addEventListener('pointercancel', finishDrag);

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape' || !activeDrag) return;
        activeDrag.sheet.panel.style.removeProperty('height');
        activeDrag.sheet.panel.style.removeProperty('max-height');
        activeDrag.sheet.panel.style.removeProperty('transition');
        activeDrag.sheet.panel.classList.remove('bottom-sheet-is-dragged');
        activeDrag = null;
    });
})();
