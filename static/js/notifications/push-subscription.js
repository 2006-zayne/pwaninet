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
     * Check if push notifications are supported
     */
    isSupported() {
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

        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            throw new Error('Notification permission denied');
        }

        return true;
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
        const registration = await navigator.serviceWorker.getRegistration();
        if (!registration) {
            console.error('Service worker not registered');
            throw new Error('Service worker not registered. Please refresh the page.');
        }
        console.log('Service worker registration found:', registration);
        return registration;
    }

    /**
     * Subscribe to push notifications
     */
    async subscribe() {
        console.log('Starting push subscription process...');

        if (!this.isSupported()) {
            throw new Error('Push notifications are not supported in this browser');
        }

        console.log('Push supported, checking permission...');

        if (!this.hasPermission()) {
            console.log('Requesting permission...');
            await this.requestPermission();
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
                    endpoint: subscriptionJson.endpoint,
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
        if (!this.isSubscribed || !this.subscription) {
            console.log('No active subscription to unsubscribe');
            return true;
        }

        try {
            // Unsubscribe from push service
            await this.subscription.unsubscribe();

            // Send unsubscribe request to server
            await this.sendUnsubscribeToServer(this.subscription);

            this.subscription = null;
            this.isSubscribed = false;

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
        if (!this.isSupported()) {
            return { supported: false, subscribed: false };
        }

        try {
            const registration = await this.getServiceWorkerRegistration();
            const subscription = await registration.pushManager.getSubscription();
            
            this.subscription = subscription;
            this.isSubscribed = !!subscription;

            return {
                supported: true,
                subscribed: this.isSubscribed,
                permission: Notification.permission
            };
        } catch (error) {
            console.error('Error getting subscription status:', error);
            return { supported: true, subscribed: false, error: error.message };
        }
    }

    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
}

// Export for use in other modules
window.PushSubscriptionManager = PushSubscriptionManager;
