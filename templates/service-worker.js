/**
 * PwaniNet Service Worker
 * Minimal PWA compliance - installability only
 */

// Install event - skip waiting only
self.addEventListener('install', (event) => {
    console.log('Service Worker: Installing...');
    self.skipWaiting();
});

// Activate event - claim clients immediately and clear old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        Promise.all([
            self.clients.claim(),
            // Clear all caches to force fresh manifest fetch
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        console.log('Service Worker: Deleting cache:', cacheName);
                        return caches.delete(cacheName);
                    })
                );
            })
        ])
    );
});

// Fetch event - required for PWA installability
self.addEventListener('fetch', (event) => {
    // Pass through all requests - required for SW to be considered "controlling"
    event.respondWith(
        fetch(event.request).catch(() => {
            return new Response('Offline', { status: 503 });
        })
    );
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('Service Worker: Push event received');

    let pushData = {
        title: 'PwaniNet Notification',
        body: 'You have a new notification',
        icon: '/static/images/web-app-manifest-192x192.png',
        badge: '/static/images/favicon-96x96.png',
        vibrate: [200, 100, 200],
        requireInteraction: false,
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/static/images/favicon-96x96.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/images/favicon-96x96.png'
            }
        ],
        data: {
            url: '/notifications'
        }
    };

    if (event.data) {
        try {
            const data = event.data.json();
            pushData = {
                title: data.title || pushData.title,
                body: data.body || pushData.body,
                icon: data.icon || pushData.icon,
                badge: data.badge || pushData.badge,
                image: data.image || undefined,
                tag: data.tag || undefined,
                renotify: data.renotify !== undefined ? data.renotify : undefined,
                vibrate: data.vibrate || pushData.vibrate,
                requireInteraction: data.requireInteraction || pushData.requireInteraction,
                actions: data.actions || pushData.actions,
                data: {
                    notification_id: data.data?.notification_id,
                    url: data.data?.url || pushData.data.url,
                    notification_type: data.data?.notification_type,
                    category: data.data?.category,
                    tag: data.data?.tag || data.tag
                }
            };
        } catch (e) {
            console.error('Service Worker: Failed to parse push data:', e);
        }
    }

    event.waitUntil(
        self.registration.showNotification(pushData.title, pushData)
    );
});

// Notification click event - handle user interaction with notifications
self.addEventListener('notificationclick', (event) => {
    console.log('Service Worker: Notification clicked', event.action, event.notification);

    event.notification.close();

    // Handle action button clicks
    if (event.action === 'dismiss') {
        console.log('Service Worker: Dismiss action clicked');
        return;
    }

    // Handle view action or default click
    const urlToOpen = event.notification.data?.url || '/notifications';

    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // Check if there's already a window open
            for (const client of clientList) {
                if (client.url === new URL(urlToOpen, self.location.origin).href && 'focus' in client) {
                    return client.focus();
                }
            }

            // If no window is open, open a new one
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

console.log('Service Worker: Loaded');
