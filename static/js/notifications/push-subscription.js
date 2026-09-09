/**
 * Push Notification Subscription Manager
 * Handles Web Push API subscription for PwaniNet
 */

class PushSubscriptionManager {
    constructor() {
        this.vapidPublicKey = null;
        this.subscription = null;
        this.isSubscribed = false;
    }

    /**
     * Check if running in a native application container (Capacitor / Android wrapper)
     */
    isNative() {
        return (
            (typeof window.Capacitor !== 'undefined' &&
             typeof window.Capacitor.isNativePlatform === 'function' &&
             window.Capacitor.isNativePlatform()) ||
            document.documentElement.classList.contains('is-capacitor') ||
            document.documentElement.classList.contains('is-native-app') ||
            typeof window.AndroidBridge !== 'undefined' ||
            typeof window.PwaninetBridge !== 'undefined' ||
            (typeof window.isNativeAppContainer === 'function' && window.isNativeAppContainer())
        );
    }

    /**
     * Wait briefly for native bridge injection if running inside native app container
     */
    async waitForNativeBridge() {
        if (!this.isNative()) return;
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.PushNotifications) {
            return;
        }
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 25));
            if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.PushNotifications) {
                break;
            }
        }
    }

    /**
     * Check if push notifications are supported
     */
    isSupported() {
        if (this.isNative()) {
            const hasCapacitorPush = typeof window.Capacitor !== 'undefined' &&
                window.Capacitor.Plugins &&
                !!window.Capacitor.Plugins.PushNotifications;
            const bridge = window.AndroidBridge || window.PwaninetBridge;
            const isPushReady = bridge && typeof bridge.isPushNotificationsAvailable === 'function'
                ? bridge.isPushNotificationsAvailable()
                : true;
            return hasCapacitorPush || isPushReady;
        }

        const hasServiceWorker = 'serviceWorker' in navigator;
        const hasPushManager = 'PushManager' in window;
        const hasNotification = 'Notification' in window;
        
        console.log('Push support check:', {
            hasServiceWorker,
            hasPushManager,
            hasNotification,
            serviceWorkerInNavigator: 'serviceWorker' in navigator,
            pushManagerInWindow: 'PushManager' in window,
            notificationInWindow: 'Notification' in window
        });
        
        return hasServiceWorker && hasPushManager && hasNotification;
    }

    /**
     * Check if permission is granted
     */
    hasPermission() {
        return Notification.permission === 'granted';
    }

    /**
     * Check if permission is denied
     */
    isPermissionDenied() {
        return Notification.permission === 'denied';
    }

    /**
     * Request notification permission
     */
    async requestPermission() {
        if (!this.isSupported()) {
            throw new Error('Push notifications are not supported in this browser');
        }

        if (this.isPermissionDenied()) {
            throw new Error('Notification permission was previously denied. Please enable it in browser settings.');
        }

        try {
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                return false;
            }
            return true;
        } catch (err) {
            if (err.name === 'NotAllowedError') {
                console.warn('Push notification permission dismissed or not allowed:', err);
                return false;
            }
            throw err;
        }
    }

    /**
     * Get VAPID public key from server
     */
    async getVapidPublicKey() {
        if (this.vapidPublicKey) {
            return this.vapidPublicKey;
        }

        try {
            const response = await fetch('/notifications/api/push/vapid-public-key/');
            if (!response.ok) {
                throw new Error('Failed to get VAPID public key');
            }

            const data = await response.json();
            this.vapidPublicKey = data.public_key;
            return this.vapidPublicKey;
        } catch (error) {
            console.error('Error fetching VAPID public key:', error);
            throw error;
        }
    }

    /**
     * Convert base64 string to Uint8Array
     */
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }

    /**
     * Get service worker registration
     */
    async getServiceWorkerRegistration() {
        if (!('serviceWorker' in navigator)) {
            throw new Error('Service workers not supported in this browser.');
        }
        let registration = await navigator.serviceWorker.getRegistration();
        if (!registration) {
            try {
                registration = await navigator.serviceWorker.register('/service-worker.js');
            } catch (e) {
                console.warn('Auto service worker register attempt failed:', e);
            }
        }
        const readyReg = await navigator.serviceWorker.ready;
        return readyReg || registration;
    }

    /**
     * Subscribe to push notifications
     */
    async subscribe() {
        console.log('Starting push subscription process...');

        if (this.isNative()) {
            await this.waitForNativeBridge();
            if (!this.isSupported()) {
                throw new Error('Push notifications are not supported on this device');
            }

            const PushNotifications = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.PushNotifications;
            if (!PushNotifications) {
                throw new Error('Push notification plugin not available on this device');
            }

            let permStatus = await PushNotifications.checkPermissions();
            if (permStatus.receive === 'prompt' || permStatus.receive === 'prompt-with-rationale') {
                permStatus = await PushNotifications.requestPermissions();
            }

            if (permStatus.receive !== 'granted') {
                console.warn('Native push notification permission was not granted.');
                return null;
            }

            if (typeof window.initNativePush === 'function') {
                await window.initNativePush(true);
            }

            localStorage.setItem('pwaninet_push_subscribed', 'true');
            this.isSubscribed = true;
            return true;
        }

        if (!this.isSupported()) {
            throw new Error('Push notifications are not supported in this browser');
        }

        console.log('Push supported, checking permission...');

        if (!this.hasPermission()) {
            console.log('Requesting permission...');
            const granted = await this.requestPermission();
            if (!granted) {
                console.warn('Push notification permission was not granted.');
                return null;
            }
        }

        try {
            // Get VAPID public key
            console.log('Getting VAPID public key...');
            const vapidPublicKey = await this.getVapidPublicKey();
            console.log('VAPID public key received:', vapidPublicKey.substring(0, 20) + '...');
            const convertedVapidKey = this.urlBase64ToUint8Array(vapidPublicKey);

            // Get service worker registration
            console.log('Getting service worker registration...');
            const registration = await this.getServiceWorkerRegistration();

            // Subscribe to push
            console.log('Subscribing to push manager...');
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedVapidKey
            });

            console.log('Push subscription created:', subscription);
            this.subscription = subscription;
            this.isSubscribed = true;

            // Send subscription to server
            console.log('Sending subscription to server...');
            await this.sendSubscriptionToServer(subscription);

            localStorage.setItem('pwaninet_push_subscribed', 'true');
            console.log('Push subscription successful');
            return subscription;
        } catch (error) {
            console.error('Push subscription failed:', error);
            throw error;
        }
    }

    /**
     * Send subscription to server
     */
    async sendSubscriptionToServer(subscription) {
        const subscriptionJson = subscription.toJSON();
        const csrfToken = this.getCsrfToken();
        const isStandalone = typeof window.isStandalonePWA === 'function' ? window.isStandalonePWA() : false;

        console.log('Sending subscription to server:', {
            endpoint: subscriptionJson.endpoint,
            hasKeys: !!subscriptionJson.keys,
            csrfToken: csrfToken ? 'present' : 'missing'
        });

        try {
            const response = await fetch('/notifications/api/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    token_type: 'VAPID',
                    platform: isStandalone ? 'PWA' : 'WEB',
                    endpoint: subscriptionJson.endpoint,
                    keys: {
                        p256dh: subscriptionJson.keys.p256dh,
                        auth: subscriptionJson.keys.auth
                    },
                    p256dh: subscriptionJson.keys.p256dh,
                    auth: subscriptionJson.keys.auth,
                    user_agent: navigator.userAgent
                })
            });

            console.log('Server response status:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error response:', errorText);
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('Subscription saved to server:', data);
            return data;
        } catch (error) {
            console.error('Error sending subscription to server:', error);
            throw error;
        }
    }

    /**
     * Unsubscribe from push notifications
     */
    async unsubscribe() {
        if (this.isNative()) {
            const fcmToken = localStorage.getItem('pwaninet_fcm_token') || localStorage.getItem('pwaninet_pending_fcm_token');
            const csrfToken = this.getCsrfToken();
            try {
                if (fcmToken) {
                    await fetch('/api/push/unsubscribe/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ fcm_token: fcmToken })
                    });
                }
            } catch (err) {
                console.warn('Failed to unsubscribe FCM token on server:', err);
            }
            localStorage.removeItem('pwaninet_push_subscribed');
            this.isSubscribed = false;
            console.log('Native push unsubscription successful');
            return true;
        }

        if (!this.isSubscribed || !this.subscription) {
            try {
                const registration = await this.getServiceWorkerRegistration();
                const sub = await registration.pushManager.getSubscription();
                if (sub) {
                    this.subscription = sub;
                    this.isSubscribed = true;
                }
            } catch (_) {}
        }

        if (!this.subscription) {
            console.log('No active subscription to unsubscribe');
            localStorage.removeItem('pwaninet_push_subscribed');
            this.isSubscribed = false;
            return true;
        }

        try {
            // Unsubscribe from push service
            await this.subscription.unsubscribe();

            // Send unsubscribe request to server
            await this.sendUnsubscribeToServer(this.subscription);

            this.subscription = null;
            this.isSubscribed = false;
            localStorage.removeItem('pwaninet_push_subscribed');

            console.log('Push unsubscription successful');
            return true;
        } catch (error) {
            console.error('Push unsubscription failed:', error);
            throw error;
        }
    }

    /**
     * Send unsubscribe request to server
     */
    async sendUnsubscribeToServer(subscription) {
        try {
            const response = await fetch('/notifications/api/push/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send unsubscribe to server');
            }

            console.log('Unsubscription saved to server');
            return true;
        } catch (error) {
            console.error('Error sending unsubscribe to server:', error);
            throw error;
        }
    }

    /**
     * Get current subscription status
     */
    async getSubscriptionStatus() {
        if (this.isNative()) {
            await this.waitForNativeBridge();
            if (!this.isSupported()) {
                return { supported: false, subscribed: false, isNative: true };
            }

            const PushNotifications = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.PushNotifications;
            if (!PushNotifications) {
                const isSubscribed = localStorage.getItem('pwaninet_push_subscribed') === 'true';
                return {
                    supported: true,
                    subscribed: isSubscribed,
                    permission: isSubscribed ? 'granted' : 'default',
                    isNative: true
                };
            }

            try {
                const permStatus = await PushNotifications.checkPermissions();
                const isGranted = permStatus.receive === 'granted';
                const isDenied = permStatus.receive === 'denied';
                const isSubscribed = isGranted && localStorage.getItem('pwaninet_push_subscribed') === 'true';

                return {
                    supported: true,
                    subscribed: isSubscribed,
                    permission: isGranted ? 'granted' : (isDenied ? 'denied' : 'default'),
                    isNative: true
                };
            } catch (err) {
                console.warn('[PUSH-SUBSCRIPTION] Error checking native permissions:', err);
                const isSubscribed = localStorage.getItem('pwaninet_push_subscribed') === 'true';
                return {
                    supported: true,
                    subscribed: isSubscribed,
                    permission: isSubscribed ? 'granted' : 'default',
                    isNative: true
                };
            }
        }

        if (!this.isSupported()) {
            return { supported: false, subscribed: false, isNative: false };
        }

        try {
            const registration = await this.getServiceWorkerRegistration();
            const subscription = await registration.pushManager.getSubscription();
            
            this.subscription = subscription;
            this.isSubscribed = !!subscription;

            return {
                supported: true,
                subscribed: this.isSubscribed,
                permission: Notification.permission,
                isNative: false
            };
        } catch (error) {
            console.error('Error getting subscription status:', error);
            return { supported: true, subscribed: false, error: error.message, isNative: false };
        }
    }

    /**
     * Get CSRF token from meta tags, hx-headers, forms, or cookies
     */
    getCsrfToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag && metaTag.getAttribute('content')) {
            return metaTag.getAttribute('content');
        }
        const hxHeaders = document.body && document.body.getAttribute('hx-headers');
        if (hxHeaders) {
            try {
                const parsed = JSON.parse(hxHeaders);
                if (parsed['X-CSRFToken']) return parsed['X-CSRFToken'];
            } catch (_) {}
        }
        const inputTag = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (inputTag && inputTag.value) {
            return inputTag.value;
        }
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    /**
     * Auto-sync existing PushManager subscription with the backend.
     * Guarantees that whether running on Web or installed PWA, the server
     * always has the current active subscription mapped to the logged-in user.
     */
    async syncActiveSubscription() {
        if (!this.isSupported() || !this.hasPermission()) {
            return null;
        }

        try {
            const registration = await this.getServiceWorkerRegistration();
            if (!registration || !registration.pushManager) return null;

            const subscription = await registration.pushManager.getSubscription();
            if (!subscription) return null;

            this.subscription = subscription;
            this.isSubscribed = true;
            return await this.sendSubscriptionToServer(subscription);
        } catch (err) {
            console.warn('[PUSH-SUBSCRIPTION] Auto-sync subscription skipped:', err);
            return null;
        }
    }
}

// Export for use in other modules
window.PushSubscriptionManager = PushSubscriptionManager;

// Automatically sync subscription on boot if permission is already granted
(function() {
    function autoSync() {
        // Skip in native capacitor app (native push handled by native-app.js)
        if (typeof isNativeAppContainer === 'function' && isNativeAppContainer()) return;
        if (typeof window.Capacitor !== 'undefined' && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform()) return;

        if ('Notification' in window && Notification.permission === 'granted' && 'serviceWorker' in navigator) {
            const manager = new PushSubscriptionManager();
            manager.syncActiveSubscription().catch(() => {});
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoSync);
    } else {
        autoSync();
    }
})();

