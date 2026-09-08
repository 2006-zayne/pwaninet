/**
 * Push Notification Soft-Prompt Bottom Sheet Controller (Web / PWA)
 * Manages contextual bottom sheet prompt for push notifications with cooldown logic.
 */
(function() {
    'use strict';

    const STORAGE_KEY_DISMISSED = 'pwaninet_push_sheet_dismissed_at';
    const STORAGE_KEY_SUBSCRIBED = 'pwaninet_push_subscribed';
    const COOLDOWN_DAYS = 7;
    const COOLDOWN_MS = COOLDOWN_DAYS * 24 * 60 * 60 * 1000;
    const SHOW_DELAY_MS = 3500;

    let sheetRoot = null;
    let sheetBackdrop = null;
    let sheetContainer = null;
    let enableBtn = null;
    let dismissBtn = null;
    let closeBtn = null;
    let isInitialized = false;

    function isNativeApp() {
        return (
            (typeof window.Capacitor !== 'undefined' &&
             typeof window.Capacitor.isNativePlatform === 'function' &&
             window.Capacitor.isNativePlatform()) ||
            document.documentElement.classList.contains('is-capacitor') ||
            document.documentElement.classList.contains('is-native-app')
        );
    }

    function isSupported() {
        return (
            'Notification' in window &&
            'serviceWorker' in navigator &&
            'PushManager' in window
        );
    }

    function isEligible() {
        // 1. Don't show in Capacitor native shell (handled by native OS on boot)
        if (isNativeApp()) {
            return false;
        }

        // 2. Browser feature support
        if (!isSupported()) {
            return false;
        }

        // 3. Only show if permission is 'default' (not granted, not denied)
        if (Notification.permission !== 'default') {
            return false;
        }

        // 4. Check if already marked subscribed
        if (localStorage.getItem(STORAGE_KEY_SUBSCRIBED) === 'true') {
            return false;
        }

        // 5. Check cooldown from previous dismissal
        const dismissedAt = localStorage.getItem(STORAGE_KEY_DISMISSED);
        if (dismissedAt) {
            const timeSinceDismiss = Date.now() - parseInt(dismissedAt, 10);
            if (timeSinceDismiss < COOLDOWN_MS) {
                return false;
            }
        }

        return true;
    }

    function showSheet() {
        if (!sheetRoot || !sheetContainer) return;

        sheetRoot.style.display = 'block';
        // Force reflow for animation
        sheetContainer.offsetHeight;

        sheetContainer.classList.add('visible');
        if (sheetBackdrop) {
            sheetBackdrop.classList.add('visible');
        }

        console.log('[PUSH-SHEET] Push prompt bottom sheet presented');
    }

    function hideSheet(rememberDismissal) {
        if (rememberDismissal === undefined) rememberDismissal = true;
        if (!sheetContainer) return;

        sheetContainer.classList.remove('visible');
        if (sheetBackdrop) {
            sheetBackdrop.classList.remove('visible');
        }

        setTimeout(function() {
            if (sheetRoot) {
                sheetRoot.style.display = 'none';
            }
        }, 400);

        if (rememberDismissal) {
            localStorage.setItem(STORAGE_KEY_DISMISSED, Date.now().toString());
            console.log('[PUSH-SHEET] Push prompt dismissed, cooldown saved for', COOLDOWN_DAYS, 'days');
        }
    }

    async function handleEnablePush() {
        if (!enableBtn) return;

        const btnText = enableBtn.querySelector('.btn-text');
        const btnSpinner = enableBtn.querySelector('.btn-spinner');

        try {
            if (btnText) btnText.classList.add('d-none');
            if (btnSpinner) btnSpinner.classList.remove('d-none');
            enableBtn.disabled = true;

            if (typeof PushSubscriptionManager === 'undefined') {
                throw new Error('PushSubscriptionManager not loaded');
            }

            const manager = new PushSubscriptionManager();
            const success = await manager.subscribe();

            if (success) {
                localStorage.setItem(STORAGE_KEY_SUBSCRIBED, 'true');
                console.log('[PUSH-SHEET] Push subscription successful');
                showToast('Notifications enabled successfully!');
                hideSheet(false);
            } else {
                console.warn('[PUSH-SHEET] Push permission not granted or cancelled');
                hideSheet(true);
            }
        } catch (err) {
            console.error('[PUSH-SHEET] Error subscribing to push:', err);
            hideSheet(true);
        } finally {
            if (btnText) btnText.classList.remove('d-none');
            if (btnSpinner) btnSpinner.classList.add('d-none');
            if (enableBtn) enableBtn.disabled = false;
        }
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'push-toast-alert';
        toast.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> ' + message;
        toast.style.cssText = [
            'position: fixed',
            'bottom: 30px',
            'left: 50%',
            'transform: translateX(-50%)',
            'background: #10b981',
            'color: #ffffff',
            'padding: 12px 24px',
            'border-radius: 9999px',
            'font-size: 0.95rem',
            'font-weight: 600',
            'box-shadow: 0 10px 25px rgba(0,0,0,0.2)',
            'z-index: 10060',
            'display: flex',
            'align-items: center'
        ].join(';');
        document.body.appendChild(toast);
        setTimeout(function() {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(function() { toast.remove(); }, 300);
        }, 3000);
    }

    function initPushSheet() {
        if (isInitialized) return;

        sheetRoot = document.getElementById('push-notification-sheet-root');
        if (!sheetRoot) return;

        sheetBackdrop = document.getElementById('push-sheet-backdrop');
        sheetContainer = document.getElementById('push-sheet-container');
        enableBtn = document.getElementById('btn-push-sheet-enable');
        dismissBtn = document.getElementById('btn-push-sheet-dismiss');
        closeBtn = document.getElementById('push-sheet-close-btn');

        if (enableBtn) {
            enableBtn.addEventListener('click', handleEnablePush);
        }

        if (dismissBtn) {
            dismissBtn.addEventListener('click', function() { hideSheet(true); });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', function() { hideSheet(true); });
        }

        if (sheetBackdrop) {
            sheetBackdrop.addEventListener('click', function() { hideSheet(true); });
        }

        isInitialized = true;

        // Check eligibility and schedule presentation
        if (isEligible()) {
            setTimeout(showSheet, SHOW_DELAY_MS);
        }
    }

    // Expose programmatic trigger on window
    window.showPushPromptSheet = function() {
        if (!sheetRoot) initPushSheet();
        showSheet();
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPushSheet);
    } else {
        initPushSheet();
    }
})();
