/**
 * Native PWA & Android APK Installation Manager
 * Handles tiered installation flow:
 *  1. Standard Mobile Browser: Can see both PWA install and APK download options.
 *  2. Installed Standalone PWA: Suppress PWA install prompt, show APK upgrade banner on Android.
 *  3. Native APK (Capacitor / PwaniNetApp): Suppress both prompts completely.
 */

// Explicit environment detection functions
function isNativeAppContainer() {
    return (
        document.documentElement.classList.contains('is-native-app') ||
        document.documentElement.classList.contains('is-capacitor') ||
        typeof window.Capacitor !== 'undefined' ||
        Boolean(window.AndroidBridge || window.PwaninetBridge) ||
        navigator.userAgent.includes('PwaniNetApp')
    );
}

function isStandalonePWA() {
    return (
        window.matchMedia('(display-mode: standalone)').matches ||
        window.matchMedia('(display-mode: fullscreen)').matches ||
        window.matchMedia('(display-mode: minimal-ui)').matches ||
        window.navigator.standalone === true
    );
}

function isAndroidUser() {
    return /Android/i.test(navigator.userAgent || navigator.vendor || window.opera || '');
}

// Expose globally for cross-script consumption
window.isNativeAppContainer = isNativeAppContainer;
window.isStandalonePWA = isStandalonePWA;
window.isAndroidUser = isAndroidUser;

class NativePWAInstallManager {
    constructor() {
        this.deferredPrompt = null;
        this.installPromptShown = false;
        this.userEngagement = {
            pageViews: 0,
            timeSpent: 0,
            interactions: 0,
            lastInteraction: Date.now()
        };
        // Lower criteria so prompt appears sooner but still respect user gesture
        this.installCriteria = {
            minTimeSpent: 5000, // 5 seconds
            minInteractions: 1,
            minPageViews: 1
        };
        this._autoPromptListener = null;
        this._dismissTimer = null; // Track dismiss timer to prevent spamming

        this.init();
    }

    init() {
        // Tier 1 & 2: Check APK download/upgrade banner for Android users outside the native container
        this.checkApkDownloadBanner();

        // Desktop QR Install Modal handler
        this.initDesktopQrModal();

        // Silent download handler (prevents page reload on 302 downloads)
        this.initSilentDownload();

        // Tier 2 & 3: Check PWA install prompt (suppressed in native container AND standalone PWA)
        if (this.isInstalled()) {
            this.disableInstallPrompts();
            return;
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            if (this.isInstalled()) {
                e.preventDefault();
                this.disableInstallPrompts();
                return;
            }

            e.preventDefault();
            this.deferredPrompt = e;
            console.log('[PWA] Native install prompt captured');

            // Immediately show visible CTA banner and attach a one-time user gesture to prompt
            this.showInstallBanner();
            this.attachAutoPromptOnFirstGesture();
        });

        window.addEventListener('appinstalled', () => {
            console.log('[PWA] PWA installed');
            this.deferredPrompt = null;
            this.installPromptShown = true;
            this.disableInstallPrompts();
            this.showInstallSuccess();
        });

        this.trackUserEngagement();
        this.checkInstallPrompt();
    }

    isInstalled() {
        // PWA install banner is suppressed if already inside native app or standalone PWA
        return isNativeAppContainer() || isStandalonePWA();
    }

    disableInstallPrompts() {
        this.installPromptShown = true;
        this.deferredPrompt = null;
        localStorage.setItem('pwaInstalled', 'true');

        const pwaBanner = document.getElementById('pwa-install-banner');
        if (pwaBanner) pwaBanner.remove();

        const genericBanners = document.querySelectorAll('[id*="install"]:not(#pwaninet-apk-banner), [class*="install"]:not([class*="apk"])');
        genericBanners.forEach(b => {
            if (b.id !== 'pwaninet-apk-banner' && !b.closest('#pwaninet-apk-banner')) {
                b.remove();
            }
        });

        this.detachAutoPrompt();

        if (this._dismissTimer) {
            clearTimeout(this._dismissTimer);
            this._dismissTimer = null;
        }

        // Tier 3: If running in native app container, ensure APK banner is also removed
        if (isNativeAppContainer()) {
            const apkBanner = document.getElementById('pwaninet-apk-banner');
            if (apkBanner) apkBanner.remove();
        }
    }

    checkApkDownloadBanner() {
        // Tier 3: Suppress completely if running in native app container
        if (isNativeAppContainer()) {
            const existingApkBanner = document.getElementById('pwaninet-apk-banner');
            if (existingApkBanner) existingApkBanner.remove();
            return;
        }

        // Only show to Android users
        if (!isAndroidUser()) {
            return;
        }

        // 1. Check if user permanently opted out ("Never")
        if (localStorage.getItem('pwaninet_apk_banner_never') === 'true') {
            return;
        }

        // Legacy check for prior dismissals
        if (localStorage.getItem('pwaninet_apk_banner_dismissed') === 'true') {
            return;
        }

        // 2. Check if currently snoozed ("Not now")
        const snoozedUntil = parseInt(localStorage.getItem('pwaninet_apk_banner_snoozed_until') || '0', 10);
        if (snoozedUntil && Date.now() < snoozedUntil) {
            return;
        }

        // Delay slightly after load for a smoother UX
        setTimeout(() => {
            if (isNativeAppContainer()) return;
            if (localStorage.getItem('pwaninet_apk_banner_never') === 'true') return;
            if (localStorage.getItem('pwaninet_apk_banner_dismissed') === 'true') return;

            const currentSnooze = parseInt(localStorage.getItem('pwaninet_apk_banner_snoozed_until') || '0', 10);
            if (currentSnooze && Date.now() < currentSnooze) return;

            this.showApkDownloadBanner();
        }, 1500);
    }

    showApkDownloadBanner() {
        if (isNativeAppContainer()) return;
        if (localStorage.getItem('pwaninet_apk_banner_never') === 'true') return;
        if (localStorage.getItem('pwaninet_apk_banner_dismissed') === 'true') return;

        const snoozedUntil = parseInt(localStorage.getItem('pwaninet_apk_banner_snoozed_until') || '0', 10);
        if (snoozedUntil && Date.now() < snoozedUntil) return;

        if (document.getElementById('pwaninet-apk-banner')) return;

        this.injectBannerStyles();

        const isStandalone = isStandalonePWA();
        const banner = document.createElement('div');
        banner.id = 'pwaninet-apk-banner';
        banner.className = 'pwaninet-banner-toast';
        banner.innerHTML = `
            <div class="pwaninet-apk-banner-inner">
                <div class="pwaninet-apk-banner-icon">
                    <img src="/static/images/pwaninet-app-icon.png" alt="PwaniNet" width="42" height="42" style="border-radius:10px;"/>
                </div>
                <div class="pwaninet-apk-banner-content">
                    <div class="pwaninet-apk-banner-title">
                        <span>PwaniNet for Android</span>
                        <span class="pwaninet-apk-badge">APK</span>
                    </div>
                    <div class="pwaninet-apk-banner-sub">
                        ${isStandalone ? 'Upgrade to native app for faster speed & background push.' : 'Download the official Android APK for native speed & alerts.'}
                    </div>
                </div>
                <div class="pwaninet-apk-banner-actions">
                    <a id="pwaninet-apk-download-btn" href="/download/android/" class="btn btn-primary btn-sm" download>
                        <i class="bi bi-download me-1"></i>Download
                    </a>
                    <div class="pwaninet-apk-banner-secondary-actions">
                        <button id="pwaninet-apk-snooze-btn" class="pwaninet-btn-text" type="button" title="Remind me in 7 days">
                            Not now
                        </button>
                        <span class="pwaninet-action-divider">•</span>
                        <button id="pwaninet-apk-never-btn" class="pwaninet-btn-text" type="button" title="Don't show again">
                            Never
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(banner);

        const downloadBtn = document.getElementById('pwaninet-apk-download-btn');
        const snoozeBtn = document.getElementById('pwaninet-apk-snooze-btn');
        const neverBtn = document.getElementById('pwaninet-apk-never-btn');

        // "Not now" -> snooze for 7 days
        if (snoozeBtn) {
            snoozeBtn.addEventListener('click', () => {
                banner.remove();
                const sevenDaysLater = Date.now() + (7 * 24 * 60 * 60 * 1000);
                localStorage.setItem('pwaninet_apk_banner_snoozed_until', sevenDaysLater.toString());
                console.log('[PWA] APK banner snoozed for 7 days');
            });
        }

        // "Never" -> snooze forever
        if (neverBtn) {
            neverBtn.addEventListener('click', () => {
                banner.remove();
                localStorage.setItem('pwaninet_apk_banner_never', 'true');
                console.log('[PWA] APK banner dismissed permanently');
            });
        }

        // "Download" -> starts download and snoozes for 14 days
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                const fourteenDaysLater = Date.now() + (14 * 24 * 60 * 60 * 1000);
                localStorage.setItem('pwaninet_apk_banner_snoozed_until', fourteenDaysLater.toString());
                setTimeout(() => {
                    if (banner.parentNode) banner.parentNode.removeChild(banner);
                }, 2000);
            });
        }
    }

    showInstallBanner() {
        if (this.isInstalled()) return;
        const existing = document.getElementById('pwa-install-banner');
        if (existing) return;

        this.injectBannerStyles();

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-install-inner">
                <div class="pwa-install-left">
                    <img src="/static/images/web-app-manifest-192x192.png" alt="PwaniNet" width="42" height="42" style="border-radius:10px;"/>
                </div>
                <div class="pwa-install-body">
                    <div class="pwa-install-title">Install PwaniNet</div>
                    <div class="pwa-install-sub">Get quicker access and offline support</div>
                </div>
                <div class="pwa-install-actions">
                    <button id="pwa-install-accept" class="btn btn-primary" type="button">Install</button>
                    <button id="pwa-install-dismiss" class="btn btn-outline-secondary" type="button">Dismiss</button>
                </div>
            </div>
        `;

        document.body.appendChild(banner);

        const accept = document.getElementById('pwa-install-accept');
        const dismiss = document.getElementById('pwa-install-dismiss');

        if (accept) {
            accept.addEventListener('click', (ev) => {
                ev.preventDefault();
                this.showNativeInstallPrompt();
            });
        }

        if (dismiss) {
            dismiss.addEventListener('click', () => {
                banner.remove();
                this.detachAutoPrompt();

                this._dismissTimer = setTimeout(() => {
                    if (!this.isInstalled()) {
                        this.showInstallReminder();
                    }
                }, 1800000); // 30 minutes
            });
        }

        // Auto-hide after 30s if not interacted
        setTimeout(() => { if (banner.parentNode) banner.parentNode.removeChild(banner); }, 30000);
    }

    injectBannerStyles() {
        if (document.getElementById('pwaninet-banner-styles')) return;

        const style = document.createElement('style');
        style.id = 'pwaninet-banner-styles';
        style.textContent = `
            #pwaninet-apk-banner, #pwa-install-banner {
                position: fixed;
                right: 16px;
                left: 16px;
                max-width: 420px;
                margin: 0 auto;
                bottom: calc(84px + var(--pwaninet-safe-area-bottom, env(safe-area-inset-bottom, 0px)));
                z-index: 10001;
                background: var(--card-bg, #ffffff);
                color: var(--text-dark, #0f172a);
                border: 1px solid var(--border, #e2e8f0);
                border-radius: 14px;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.16);
                overflow: hidden;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                animation: pwaninet-banner-fade-up 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }

            @media (min-width: 768px) {
                #pwaninet-apk-banner, #pwa-install-banner {
                    left: auto;
                    right: 24px;
                    bottom: 24px;
                    width: 380px;
                }
            }

            /* When both banners coexist on standard browser, stack APK banner above PWA banner */
            #pwa-install-banner ~ #pwaninet-apk-banner,
            #pwaninet-apk-banner ~ #pwa-install-banner {
                bottom: calc(180px + var(--pwaninet-safe-area-bottom, env(safe-area-inset-bottom, 0px)));
            }
            @media (min-width: 768px) {
                #pwa-install-banner ~ #pwaninet-apk-banner,
                #pwaninet-apk-banner ~ #pwa-install-banner {
                    bottom: 120px;
                }
            }

            .pwaninet-apk-banner-inner, .pwa-install-inner {
                display: flex;
                gap: 12px;
                align-items: center;
                padding: 12px 14px;
            }

            .pwaninet-apk-banner-icon, .pwa-install-left {
                flex-shrink: 0;
                display: flex;
                align-items: center;
            }

            .pwaninet-apk-banner-content, .pwa-install-body {
                flex: 1;
                min-width: 0;
            }

            .pwaninet-apk-banner-title, .pwa-install-title {
                font-weight: 700;
                font-size: 14px;
                color: var(--text-dark, #0f172a);
                display: flex;
                align-items: center;
                gap: 6px;
                line-height: 1.2;
            }

            .pwaninet-apk-badge {
                background: var(--primary-light, #dbeafe);
                color: var(--primary, #2563eb);
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 6px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            [data-theme="dark"] .pwaninet-apk-badge {
                background: var(--primary-light, #312e81);
                color: #a5b4fc;
            }

            .pwaninet-apk-banner-sub, .pwa-install-sub {
                font-size: 12px;
                color: var(--text-secondary, #64748b);
                margin-top: 3px;
                line-height: 1.3;
            }

            .pwaninet-apk-banner-actions, .pwa-install-actions {
                display: flex;
                flex-direction: column;
                gap: 6px;
                flex-shrink: 0;
            }

            .pwaninet-apk-banner-actions .btn, .pwa-install-actions .btn {
                font-size: 12px;
                padding: 6px 12px;
                border-radius: 8px;
                font-weight: 600;
                white-space: nowrap;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
            }

            .pwaninet-apk-banner-secondary-actions {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-top: 2px;
            }

            .pwaninet-btn-text {
                background: transparent;
                border: none;
                padding: 0;
                font-size: 11px;
                font-weight: 500;
                color: var(--text-secondary, #64748b);
                cursor: pointer;
                transition: color 0.15s ease;
                text-decoration: underline;
                text-underline-offset: 2px;
            }

            .pwaninet-btn-text:hover {
                color: var(--text-dark, #0f172a);
            }

            [data-theme="dark"] .pwaninet-btn-text {
                color: var(--text-secondary, #94a3b8);
            }

            [data-theme="dark"] .pwaninet-btn-text:hover {
                color: #ffffff;
            }

            .pwaninet-action-divider {
                font-size: 10px;
                color: var(--text-secondary, #94a3b8);
                opacity: 0.6;
            }

            @keyframes pwaninet-banner-fade-up {
                from {
                    opacity: 0;
                    transform: translateY(16px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }

    trackUserEngagement() {
        this.userEngagement.pageViews++;
        const start = Date.now();
        setInterval(() => { this.userEngagement.timeSpent = Date.now() - start; }, 1000);
        ['click','scroll','keydown','touchstart'].forEach(ev => {
            document.addEventListener(ev, () => {
                this.userEngagement.interactions++;
                this.userEngagement.lastInteraction = Date.now();
            }, { passive: true });
        });
    }

    meetsInstallCriteria() {
        const { minTimeSpent, minInteractions, minPageViews } = this.installCriteria;
        const { timeSpent, interactions, pageViews } = this.userEngagement;
        return timeSpent >= minTimeSpent && interactions >= minInteractions && pageViews >= minPageViews;
    }

    scheduleNativeInstallPrompt() {
        const checkInterval = setInterval(() => {
            if (this.isInstalled() || this.installPromptShown) { clearInterval(checkInterval); return; }
            if (this.meetsInstallCriteria() && this.deferredPrompt) { clearInterval(checkInterval); this.showNativeInstallPrompt(); }
        }, 2000);
    }

    checkInstallPrompt() {
        if (this.isInstalled()) return;
        const delay = 1800000; // 30 minutes in milliseconds
        setTimeout(() => {
            if (!this.deferredPrompt && !this.installPromptShown) this.showInstallInstructions();
        }, delay);
    }

    attachAutoPromptOnFirstGesture() {
        if (!this.deferredPrompt) return;
        if (this._autoPromptListener) return;

        this._autoPromptListener = () => {
            try {
                if (!this.installPromptShown && this.deferredPrompt) {
                    this.showNativeInstallPrompt();
                }
            } finally {
                this.detachAutoPrompt();
            }
        };

        ['pointerdown','keydown','touchstart','click'].forEach(ev => document.addEventListener(ev, this._autoPromptListener, { once: true, passive: true }));
    }

    detachAutoPrompt() {
        if (!this._autoPromptListener) return;
        ['pointerdown','keydown','touchstart','click'].forEach(ev => document.removeEventListener(ev, this._autoPromptListener));
        this._autoPromptListener = null;
    }

    showNativeInstallPrompt() {
        if (this.isInstalled()) { this.disableInstallPrompts(); return; }
        if (this.installPromptShown) return;
        if (!this.deferredPrompt) return;

        this.installPromptShown = true;
        const dp = this.deferredPrompt;
        dp.prompt();
        dp.userChoice.then(choice => {
            if (choice.outcome === 'accepted') {
                this.showInstallSuccess();
                localStorage.setItem('pwaInstalled', 'true');
            } else {
                this.showInstallReminder();
            }
            this.deferredPrompt = null;
        }).catch(err => {
            console.warn('[PWA] Install prompt failed:', err);
            this.deferredPrompt = null;
        });
    }

    showInstallInstructions() {
        const id = 'pwa-install-instructions';
        if (document.getElementById(id)) return;
        const div = document.createElement('div');
        div.id = id;
        div.innerHTML = `
            <div class="pwa-install-instr">
                <div><strong>Install PwaniNet</strong></div>
                <div style="font-size:13px; margin-top:6px">Tap Share → Add to Home Screen (iOS) or use Install in browser menu (Android/Desktop)</div>
                <button id="pwa-install-instr-dismiss" style="margin-top:8px;padding:6px 10px;border-radius:8px;border:none;background:var(--primary, #2563eb);color:#fff">Got it</button>
            </div>
        `;
        const style = document.createElement('style');
        style.textContent = `#${id}{position:fixed;left:16px;right:16px;bottom:calc(84px + var(--pwaninet-safe-area-bottom, 0px));background:rgba(0,0,0,0.85);color:#fff;padding:12px;border-radius:12px;z-index:10001;text-align:center}`;
        document.head.appendChild(style);
        document.body.appendChild(div);
        document.getElementById('pwa-install-instr-dismiss').addEventListener('click', () => div.remove());
    }

    showInstallReminder() {
        const r = document.createElement('div');
        r.className = 'pwa-install-reminder';
        r.innerHTML = '<div style="padding:8px 12px;background:var(--primary, #2563eb);color:#fff;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">Install PwaniNet for best experience</div>';
        r.style.position = 'fixed';
        r.style.bottom = 'calc(84px + var(--pwaninet-safe-area-bottom, 0px))';
        r.style.right = '16px';
        r.style.zIndex = '10001';
        document.body.appendChild(r);
        setTimeout(() => r.remove(), 7000);
    }

    showInstallSuccess() {
        const s = document.createElement('div');
        s.innerHTML = '<div style="padding:10px 14px;background:#10b981;color:#fff;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">Installed ✓</div>';
        s.style.position = 'fixed';
        s.style.bottom = 'calc(84px + var(--pwaninet-safe-area-bottom, 0px))';
        s.style.right = '16px';
        s.style.zIndex = '10001';
        document.body.appendChild(s);
        setTimeout(() => s.remove(), 5000);
    }

    forceShowNativeInstall() {
        if (!this.isInstalled() && this.deferredPrompt) this.showNativeInstallPrompt();
        else this.showInstallInstructions();
    }

    getInstallStatus() {
        return {
            isInstalled: this.isInstalled(),
            isNativeApp: isNativeAppContainer(),
            isStandalonePWA: isStandalonePWA(),
            isAndroid: isAndroidUser(),
            deferredPromptAvailable: !this.deferredPrompt,
            promptShown: this.installPromptShown,
            userEngagement: this.userEngagement,
            meetsCriteria: this.meetsInstallCriteria()
        };
    }

    initSilentDownload() {
        const triggerSilentDownload = (url) => {
            let iframe = document.getElementById('pwaninet-download-target');
            if (!iframe) {
                iframe = document.createElement('iframe');
                iframe.id = 'pwaninet-download-target';
                iframe.name = 'pwaninet-download-target';
                iframe.style.display = 'none';
                iframe.style.width = '0';
                iframe.style.height = '0';
                iframe.style.border = 'none';
                document.body.appendChild(iframe);
            }
            iframe.src = url || '/download/android/';
            console.log('[PWA] Triggered silent APK download via iframe:', iframe.src);
        };

        // Expose globally
        window.triggerPwaninetDownload = triggerSilentDownload;

        // Global click interceptor: prevents top-level page navigation & reloads on downloads
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href*="/download/android/"], a[href*="/apk/"], [data-apk-download]');
            if (link) {
                e.preventDefault();
                e.stopPropagation();
                triggerSilentDownload(link.href || '/download/android/');
            }
        });
    }

    initDesktopQrModal() {
        // QR code is now a server-rendered SVG served at /apk/qr/ and embedded
        // as a plain <img> tag in the modal — no canvas or JS QR generation needed.

        // Delegated copy button handler for #qr-modal-copy-btn
        document.addEventListener('click', (e) => {
            const copyBtn = e.target.closest('#qr-modal-copy-btn');
            if (!copyBtn) return;

            if (typeof window.copyApkLink === 'function') {
                window.copyApkLink(copyBtn);
                return;
            }

            if (copyBtn.dataset.copying === 'true') return;
            copyBtn.dataset.copying = 'true';

            const input = document.getElementById('qr-modal-link-input');
            const textToCopy = (input && input.value) ? input.value : 'https://pwaninet.app/apk/';

            const originalHtml = copyBtn.getAttribute('data-original-html') || copyBtn.innerHTML;
            if (!copyBtn.getAttribute('data-original-html')) {
                copyBtn.setAttribute('data-original-html', originalHtml);
            }

            const showSuccess = () => {
                copyBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
                copyBtn.classList.remove('btn-outline-primary');
                copyBtn.classList.add('btn-success');
                setTimeout(() => {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.classList.remove('btn-success');
                    copyBtn.classList.add('btn-outline-primary');
                    delete copyBtn.dataset.copying;
                }, 2000);
            };

            const fallbackCopy = () => {
                let copied = false;
                try {
                    const temp = document.createElement('textarea');
                    temp.value = textToCopy;
                    temp.style.position = 'fixed';
                    temp.style.top = '0';
                    temp.style.left = '0';
                    temp.style.width = '2em';
                    temp.style.height = '2em';
                    temp.style.padding = '0';
                    temp.style.border = 'none';
                    temp.style.outline = 'none';
                    temp.style.boxShadow = 'none';
                    temp.style.background = 'transparent';
                    temp.setAttribute('readonly', '');
                    document.body.appendChild(temp);
                    temp.focus();
                    temp.select();
                    temp.setSelectionRange(0, textToCopy.length);
                    copied = document.execCommand('copy');
                    document.body.removeChild(temp);
                } catch (err) {
                    console.warn('[Clipboard] fallback textarea error:', err);
                }

                if (!copied && input) {
                    try {
                        input.focus();
                        input.select();
                        input.setSelectionRange(0, 99999);
                        copied = document.execCommand('copy');
                    } catch (e) {
                        console.warn('[Clipboard] fallback input error:', e);
                    }
                }

                showSuccess();
            };

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(textToCopy)
                    .then(() => showSuccess())
                    .catch(() => fallbackCopy());
            } else {
                fallbackCopy();
            }
        });
    }

}

window.nativePWAInstallManager = new NativePWAInstallManager();
