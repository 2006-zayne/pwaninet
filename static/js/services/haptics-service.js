/**
 * PwaniNet Unified Haptics Engine
 * Provides ultra-responsive, zero-latency tactile feedback for Android Capacitor and Web
 * Cascades: AndroidBridge (0ms sync) -> Capacitor.Plugins.Haptics -> navigator.vibrate
 */

(function() {
    'use strict';

    class HapticsEngine {
        constructor() {
            this.enabled = true;
            this.lastTriggerTime = 0;
            this.minIntervalMs = 25; // Cooldown between rapid haptics to prevent motor buzz
            this._initPreferences();
        }

        _initPreferences() {
            // Respect accessibility reduced-motion preference
            if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                this.enabled = false;
            }

            // Respect user preference if explicitly disabled
            try {
                const saved = localStorage.getItem('pwaninet_haptics_enabled');
                if (saved === 'false') {
                    this.enabled = false;
                }
            } catch (e) {}
        }

        _canTrigger() {
            if (!this.enabled) return false;
            const now = performance.now();
            if (now - this.lastTriggerTime < this.minIntervalMs) {
                return false;
            }
            this.lastTriggerTime = now;
            return true;
        }

        /**
         * Light impact - optimal for bottom navigation tabs, buttons, likes, chips
         */
        impactLight() {
            if (!this._canTrigger()) return;

            // Tier 1: Direct synchronous native bridge (0ms delay)
            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticImpact === 'function') {
                try {
                    bridge.hapticImpact('light');
                    return;
                } catch (e) {}
            }

            // Tier 2: Capacitor Haptics Plugin
            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.impact({ style: 'LIGHT' });
                    return;
                } catch (e) {}
            }

            // Tier 3: Web Vibration API fallback
            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate(22);
                } catch (e) {}
            }
        }

        /**
         * Medium impact - optimal for long-press, modal open, action sheets
         */
        impactMedium() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticImpact === 'function') {
                try {
                    bridge.hapticImpact('medium');
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.impact({ style: 'MEDIUM' });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate(38);
                } catch (e) {}
            }
        }

        /**
         * Heavy impact - optimal for primary/destructive confirmations
         */
        impactHeavy() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticImpact === 'function') {
                try {
                    bridge.hapticImpact('heavy');
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.impact({ style: 'HEAVY' });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate(55);
                } catch (e) {}
            }
        }

        /**
         * Selection tick - optimal for switches, toggles, segment pickers
         */
        selection() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticSelection === 'function') {
                try {
                    bridge.hapticSelection();
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.selectionChanged();
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate(18);
                } catch (e) {}
            }
        }

        /**
         * Success notification - double pulse for completed tasks, uploads, sent messages
         */
        success() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticNotification === 'function') {
                try {
                    bridge.hapticNotification('success');
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.notification({ type: 'SUCCESS' });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate([20, 50, 30]);
                } catch (e) {}
            }
        }

        /**
         * Warning notification - form warnings, alerts
         */
        warning() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticNotification === 'function') {
                try {
                    bridge.hapticNotification('warning');
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.notification({ type: 'WARNING' });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate([40, 60, 40]);
                } catch (e) {}
            }
        }

        /**
         * Error notification - failed submissions, network drops
         */
        error() {
            if (!this._canTrigger()) return;

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.hapticNotification === 'function') {
                try {
                    bridge.hapticNotification('error');
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.notification({ type: 'ERROR' });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate([40, 50, 40, 50, 60]);
                } catch (e) {}
            }
        }

        /**
         * Raw timed vibrate
         */
        vibrate(durationMs) {
            if (!this._canTrigger()) return;
            const ms = Math.max(10, Math.min(durationMs || 200, 2000));

            const bridge = window.AndroidBridge || window.PwaninetBridge;
            if (bridge && typeof bridge.vibrate === 'function') {
                try {
                    bridge.vibrate(ms);
                    return;
                } catch (e) {}
            }

            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
                try {
                    window.Capacitor.Plugins.Haptics.vibrate({ duration: ms });
                    return;
                } catch (e) {}
            }

            if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try {
                    navigator.vibrate(ms);
                } catch (e) {}
            }
        }

        /**
         * Toggle haptic preference
         */
        setEnabled(enable) {
            this.enabled = Boolean(enable);
            try {
                localStorage.setItem('pwaninet_haptics_enabled', this.enabled ? 'true' : 'false');
            } catch (e) {}
        }
    }

    const instance = new HapticsEngine();
    window.Haptics = instance;
    window.HapticsService = instance;

    /**
     * Declarative event delegation for haptic attributes and mobile nav
     */
    function attachGlobalHapticListeners() {
        document.addEventListener('touchstart', function(e) {
            const hapticEl = e.target.closest('[data-haptic]');
            if (hapticEl) {
                const type = hapticEl.getAttribute('data-haptic');
                if (type === 'medium') instance.impactMedium();
                else if (type === 'heavy') instance.impactHeavy();
                else if (type === 'selection') instance.selection();
                else if (type === 'success') instance.success();
                else if (type === 'error') instance.error();
                else instance.impactLight();
                return;
            }

            // Bottom Navigation Chips
            const navChip = e.target.closest('.mobile-bottom-nav .nav-chip');
            if (navChip) {
                instance.impactLight();
                return;
            }

            // Interactive Switches & Checkboxes
            const toggleEl = e.target.closest('.form-check-input, .switch, [role="switch"]');
            if (toggleEl) {
                instance.selection();
                return;
            }
        }, { passive: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachGlobalHapticListeners);
    } else {
        attachGlobalHapticListeners();
    }
})();
