/**
 * Native PWA Install Manager
 * Handles native browser install prompts (Chrome omnibox, etc.)
 */

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
        // Be more aggressive: lower criteria so prompt appears sooner but still respect user gesture
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
            console.log('Native install prompt captured');

            // Immediately show visible CTA banner and attach a one-time user gesture to prompt
            this.showInstallBanner();
            this.attachAutoPromptOnFirstGesture();
        });

        window.addEventListener('appinstalled', () => {
            console.log('PWA installed');
            this.deferredPrompt = null;
            this.installPromptShown = true;
            this.disableInstallPrompts();
            this.showInstallSuccess();
        });

        this.trackUserEngagement();
        this.checkInstallPrompt();
    }

    isInstalled() {
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isIOSStandalone = window.navigator.standalone === true;
        const pwaInstalled = localStorage.getItem('pwaInstalled') === 'true';
        return isStandalone || isIOSStandalone || pwaInstalled;
    }

    disableInstallPrompts() {
        this.installPromptShown = true;
        this.deferredPrompt = null;
        localStorage.setItem('pwaInstalled', 'true');
        const banners = document.querySelectorAll('[id*="install"], [class*="install"]');
        banners.forEach(b => b.remove());
        this.detachAutoPrompt();

        // DELAY FIX: Clear dismiss timer when PWA is installed to prevent reminder showing after install
        if (this._dismissTimer) {
            clearTimeout(this._dismissTimer);
            this._dismissTimer = null;
        }
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
        // Keep for compatibility but primary flow uses banner + user gesture
        const checkInterval = setInterval(() => {
            if (this.isInstalled() || this.installPromptShown) { clearInterval(checkInterval); return; }
            if (this.meetsInstallCriteria() && this.deferredPrompt) { clearInterval(checkInterval); this.showNativeInstallPrompt(); }
        }, 2000);
    }

    checkInstallPrompt() {
        if (this.isInstalled()) return;
        // If browser didn't fire beforeinstallprompt, show instructions after 30 minutes
        const delay = 1800000; // 30 minutes in milliseconds
        setTimeout(() => {
            if (!this.deferredPrompt && !this.installPromptShown) this.showInstallInstructions();
        }, delay);
    }

    // create a prominent install banner with explicit Install button
    showInstallBanner() {
        // Remove existing
        const existing = document.getElementById('pwa-install-banner');
        if (existing) return;

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-install-inner">
                <div class="pwa-install-left">
                    <img src="/static/images/web-app-manifest-192x192.png" alt="icon" width="44" height="44" style="border-radius:10px;"/>
                </div>
                <div class="pwa-install-body">
                    <div class="pwa-install-title">Install PwaniNet</div>
                    <div class="pwa-install-sub">Get quicker access and offline support</div>
                </div>
                <div class="pwa-install-actions">
                    <button id="pwa-install-accept" class="btn">Install</button>
                    <button id="pwa-install-dismiss" class="btn btn-light">Dismiss</button>
                </div>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            #pwa-install-banner { position: fixed; right: 16px; bottom: 20px; z-index: 10001; background: rgba(255,255,255,0.95); border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); overflow: hidden; }
            #pwa-install-banner .pwa-install-inner { display:flex; gap:12px; align-items:center; padding:10px 12px; }
            .pwa-install-body { min-width:160px }
            .pwa-install-title { font-weight:700; color:#0f172a }
            .pwa-install-sub { font-size:12px; color:#475569 }
            .pwa-install-actions .btn { margin-left:8px; padding:8px 12px; border-radius:8px; }
            .btn { background: linear-gradient(135deg,#2563eb,#1d4ed8); color:white; border:none; cursor:pointer }
            .btn-light { background:transparent; border:1px solid #e2e8f0; color:#0f172a }
        `;

        document.head.appendChild(style);
        document.body.appendChild(banner);

        const accept = document.getElementById('pwa-install-accept');
        const dismiss = document.getElementById('pwa-install-dismiss');

        accept.addEventListener('click', (ev) => {
            ev.preventDefault();
            this.showNativeInstallPrompt();
        });

        dismiss.addEventListener('click', () => {
            banner.remove();
            this.detachAutoPrompt();

            // DELAY FIX: Prevent spamming by waiting 30 minutes before showing reminder
            // This ensures users aren't annoyed by repeated install prompts
            this._dismissTimer = setTimeout(() => {
                if (!this.isInstalled()) {
                    this.showInstallReminder();
                }
            }, 1800000); // 30 minutes in milliseconds
        });

        // Auto-hide after 30s if not interacted
        setTimeout(() => { if (banner.parentNode) banner.parentNode.removeChild(banner); }, 30000);
    }

    attachAutoPromptOnFirstGesture() {
        if (!this.deferredPrompt) return;
        if (this._autoPromptListener) return; // already attached

        // Prompt on the very next user gesture (pointerdown or keydown)
        this._autoPromptListener = (ev) => {
            try {
                // Only prompt if not already shown
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
        if (!this.deferredPrompt) {
            // No native prompt available; show instructions instead
           /* setTimeout(() => {
                if (!this.showInstallInstructions) {
                    this.showInstallInstructions();
                }
            }, 1800000);*/
            return;
        }

        this.installPromptShown = true;
        const dp = this.deferredPrompt;
        dp.prompt();
        dp.userChoice.then(choice => {
            if (choice.outcome === 'accepted') { this.showInstallSuccess(); localStorage.setItem('pwaInstalled','true'); }
            else { this.showInstallReminder(); }
            this.deferredPrompt = null;
        }).catch(err => { console.warn('Install prompt failed:', err); this.deferredPrompt = null; });
    }

    showInstallInstructions() {
        // For browsers that don't support beforeinstallprompt (Safari), show clear instructions
        const id = 'pwa-install-instructions';
        if (document.getElementById(id)) return;
        const div = document.createElement('div'); div.id = id;
        div.innerHTML = `
            <div class="pwa-install-instr">
                <div><strong>Install PwaniNet</strong></div>
                <div style="font-size:13px; margin-top:6px">Tap Share → Add to Home Screen (iOS) or use Install in browser menu (Android/Desktop)</div>
                <button id="pwa-install-instr-dismiss" style="margin-top:8px;padding:6px 10px;border-radius:8px;border:none;background:#2563eb;color:#fff">Got it</button>
            </div>
        `;
        const style = document.createElement('style');
        style.textContent = `#${id}{position:fixed;left:16px;right:16px;bottom:20px;background:rgba(0,0,0,0.75);color:#fff;padding:12px;border-radius:12px;z-index:10001;text-align:center}`;
        document.head.appendChild(style);
        document.body.appendChild(div);
        document.getElementById('pwa-install-instr-dismiss').addEventListener('click', () => div.remove());
    }

    showInstallReminder() { /* small non-blocking reminder */
        const r = document.createElement('div'); r.className='pwa-install-reminder';
        r.innerHTML = '<div style="padding:8px 12px;background:#2563eb;color:#fff;border-radius:8px">Install PwaniNet for best experience</div>';
        r.style.position='fixed'; r.style.bottom='90px'; r.style.right='16px'; r.style.zIndex='10001';
        document.body.appendChild(r); setTimeout(()=>r.remove(),7000);
    }

    showInstallSuccess() { const s = document.createElement('div'); s.innerHTML='<div style="padding:10px 14px;background:#10b981;color:#fff;border-radius:10px">Installed ✓</div>'; s.style.position='fixed'; s.style.bottom='90px'; s.style.right='16px'; s.style.zIndex='10001'; document.body.appendChild(s); setTimeout(()=>s.remove(),5000); }

    forceShowNativeInstall() { if (!this.isInstalled() && this.deferredPrompt) this.showNativeInstallPrompt(); else this.showInstallInstructions(); }

    getInstallStatus() { return { isInstalled:this.isInstalled(), deferredPromptAvailable:!!this.deferredPrompt, promptShown:this.installPromptShown, userEngagement:this.userEngagement, meetsCriteria:this.meetsInstallCriteria() }; }
}

window.nativePWAInstallManager = new NativePWAInstallManager();
