/**
 * PwaniNet Service Worker
 * Handles offline support, caching, and push notifications
 * Version: 1.1.0 - Updated with enhanced push notifications
 */

'use strict';
let CACHE_VERSION = '1.1.0';
let CACHE_BUILD = '2';
let CACHE_NAME = `pwaninet-v${CACHE_VERSION}-build${CACHE_BUILD}`;
let OFFLINE_CACHE_NAME = `pwaninet-offline-v${CACHE_VERSION}-build${CACHE_BUILD}`;

// Service worker version metadata
const SW_VERSION = {
    version: CACHE_VERSION,
    build: CACHE_BUILD,
    buildDate: new Date().toISOString(),
    cacheName: CACHE_NAME,
    environment: 'development'
};

// Set version from message (called during registration)
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SET_VERSION') {
        CACHE_VERSION = event.data.version;
        CACHE_BUILD = event.data.build;
        CACHE_NAME = `pwaninet-v${CACHE_VERSION}-build${CACHE_BUILD}`;
        OFFLINE_CACHE_NAME = `pwaninet-offline-v${CACHE_VERSION}-build${CACHE_BUILD}`;
        SW_VERSION.version = CACHE_VERSION;
        SW_VERSION.build = CACHE_BUILD;
        SW_VERSION.cacheName = CACHE_NAME;
        SW_VERSION.environment = event.data.environment || 'development';
        SW_VERSION.buildDate = event.data.buildDate || new Date().toISOString();
        console.log('Service Worker: Version set to', CACHE_VERSION, 'build', CACHE_BUILD);
    }
});

// Core assets to cache for offline functionality
const CORE_ASSETS = [
    '/',
    '/offline.html',
    '/static/css/bootstrap.min.css',
    '/static/css/bootstrap-icons.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/images/favicon.ico',
    '/static/images/favicon-96x96.png',
    '/static/images/favicon.svg',
    '/static/images/apple-touch-icon.png',
    '/static/images/web-app-manifest-192x192.png',
    '/static/images/web-app-manifest-512x512.png',
    '/static/images/browserconfig.xml',
    '/static/js/messaging/offline-cache.js',
    '/static/js/messaging/network-status.js',
    '/static/js/messaging/sync-manager.js',
    '/static/js/messaging/offline-ui.js',
    '/static/js/messaging/offline-integration.js',
    '/static/js/native-pwa-install.js',
    '/static/js/splash-screen.js'
];

// Page shells to cache for offline access
const PAGE_SHELLS = [
    '/',
    '/messaging/',
    '/posts/',
    '/users/profile/'
];

// Install event - cache core assets
self.addEventListener('install', (event) => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Service Worker: Caching core assets');
                return cache.addAll(CORE_ASSETS);
            })
            .then(() => {
                console.log('Service Worker: Core assets cached');
                // DO NOT call skipWaiting() - wait for user approval
                // The service worker will remain in 'waiting' state
            })
            .catch((error) => {
                console.error('Service Worker: Failed to cache core assets:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE_NAME) {
                            console.log('Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker: Activated');
                // DO NOT call clients.claim() - wait for user approval
                // The service worker will not claim clients until explicitly told
            })
    );
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('Service Worker: Push event received');

    let pushData = {
        title: 'PwaniNet Notification',
        body: 'You have a new notification',
        icon: '/static/images/web-app-manifest-192x192-rounded.png',
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
            console.log('Service Worker: Received push data:', JSON.stringify(data, null, 2));
            pushData = {
                title: data.title || pushData.title,
                body: data.body || pushData.body,
                icon: data.icon || pushData.icon,
                badge: data.badge || pushData.badge,
                vibrate: data.vibrate || pushData.vibrate,
                requireInteraction: data.requireInteraction || pushData.requireInteraction,
                actions: data.actions || pushData.actions,
                data: {
                    notification_id: data.data?.notification_id,
                    url: data.data?.url || pushData.data.url,
                    notification_type: data.data?.notification_type,
                    category: data.data?.category
                }
            };
            console.log('Service Worker: Final push data to display:', JSON.stringify(pushData, null, 2));
        } catch (e) {
            console.error('Service Worker: Failed to parse push data:', e);
        }
    } else {
        console.log('Service Worker: No data in push event, using default');
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
    const notificationId = event.notification.data?.notification_id;

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

// Fetch event - intercept requests and provide offline support
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests and external resources
    if (request.method !== 'GET' || url.origin !== self.location.origin) {
        return;
    }
    
    event.respondWith(handleRequest(request));
});

async function handleRequest(request) {
    const url = new URL(request.url);
    
    try {
        // Try network first for navigation requests
        if (isNavigationRequest(request)) {
            return await handleNavigationRequest(request);
        }
        
        // Try cache first for static assets
        if (isStaticAsset(request)) {
            return await handleStaticAssetRequest(request);
        }
        
        // Try network with cache fallback for API requests
        if (isApiRequest(request)) {
            return await handleApiRequest(request);
        }
        
        // Default: network first with cache fallback
        return await networkFirst(request);
        
    } catch (error) {
        console.error('Service Worker: Request handling failed:', error);
        return await getOfflineResponse(request);
    }
}

async function handleNavigationRequest(request) {
    try {
        // Try to fetch a small resource
        const response = await fetch('/static/images/favicon.ico', {
            method: 'HEAD',
            cache: 'no-cache'
        });
        
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache for navigation');
        
        // Try cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for navigation requests
        return await getOfflinePage();
    }
}

async function handleStaticAssetRequest(request) {
    const url = new URL(request.url);
    
    // For CSS files, use network first to ensure latest styles
    if (url.pathname.includes('.css')) {
        try {
            const networkResponse = await fetch(request);
            if (networkResponse.ok) {
                const cache = await caches.open(CACHE_NAME);
                cache.put(request, networkResponse.clone());
                return networkResponse;
            }
        } catch (error) {
            console.log('Service Worker: Network failed for CSS, trying cache');
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }
        }
    }
    
    // For video files, use network first to ensure latest content
    if (url.pathname.includes('.mp4') || url.pathname.includes('.webm') || url.pathname.includes('.mov')) {
        try {
            const networkResponse = await fetch(request);
            if (networkResponse.ok) {
                const cache = await caches.open(CACHE_NAME);
                cache.put(request, networkResponse.clone());
                return networkResponse;
            }
        } catch (error) {
            console.log('Service Worker: Network failed for video, trying cache');
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }
        }
    }
    
    // For profile images, use cache first with background refresh
    if (url.pathname.includes('profile_pics') || url.pathname.includes('profile-pic')) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            // Return cached version immediately
            // Then fetch fresh version in background
            fetch(request).then(networkResponse => {
                if (networkResponse.ok) {
                    const cache = caches.open(CACHE_NAME);
                    cache.then(c => c.put(request, networkResponse));
                }
            }).catch(() => {});
            return cachedResponse;
        }
    }
    
    // Cache first for other static assets
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        // Try network
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Network failed for static asset:', request.url);
        
        // Return offline asset if available
        return await getOfflineAsset(request);
    }
}

async function handleApiRequest(request) {
    try {
        // Try network first for API requests
        const networkResponse = await fetch(request);
        
        // Cache successful GET requests
        if (networkResponse.ok && request.method === 'GET') {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: API request failed, trying cache');
        
        // Try cache for GET requests
        if (request.method === 'GET') {
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }
        }
        
        // Return offline response for API requests
        return await getOfflineApiResponse(request);
    }
}

async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache');
        
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        throw error;
    }
}

async function getOfflineResponse(request) {
    const url = new URL(request.url);
    
    // Return offline page for navigation requests
    if (isNavigationRequest(request)) {
        return await getOfflinePage();
    }
    
    // Return offline asset for static assets
    if (isStaticAsset(request)) {
        return await getOfflineAsset(request);
    }
    
    // Return offline API response
    if (isApiRequest(request)) {
        return await getOfflineApiResponse(request);
    }
    
    // Default offline response
    return new Response('Offline', {
        status: 503,
        statusText: 'Service Unavailable'
    });
}

async function getOfflinePage() {
    const offlineResponse = await caches.match('/offline.html');
    if (offlineResponse) {
        return offlineResponse;
    }
    
    // Try to fetch and cache the offline page
    try {
        const response = await fetch('/offline.html');
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put('/offline.html', response.clone());
            return response;
        }
    } catch (error) {
        console.log('Failed to fetch offline.html, using fallback');
    }
    
    // Create basic offline page if not cached
    return new Response(`
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PwaniNet - Offline</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 20px;
                }
                
                .offline-container {
                    max-width: 400px;
                    animation: fadeInUp 0.6s ease;
                }
                
                .offline-icon {
                    font-size: 80px;
                    margin-bottom: 20px;
                    opacity: 0.8;
                }
                
                .offline-title {
                    font-size: 28px;
                    font-weight: 600;
                    margin-bottom: 12px;
                }
                
                .offline-message {
                    font-size: 16px;
                    opacity: 0.9;
                    margin-bottom: 24px;
                    line-height: 1.5;
                }
                
                .offline-status {
                    font-size: 14px;
                    opacity: 0.7;
                    margin-bottom: 32px;
                }
                
                .retry-button {
                    background: rgba(255, 255, 255, 0.2);
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 25px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-block;
                }
                
                .retry-button:hover {
                    background: rgba(255, 255, 255, 0.3);
                    border-color: rgba(255, 255, 255, 0.5);
                    transform: translateY(-2px);
                }
                
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 0.8; }
                    50% { opacity: 0.4; }
                }
                
                .connecting {
                    animation: pulse 2s ease-in-out infinite;
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon connecting">📱</div>
                <h1 class="offline-title">You're offline</h1>
                <p class="offline-message">PwaniNet is unavailable right now.</p>
                <p class="offline-status">We'll reconnect automatically...</p>
                <button class="retry-button" onclick="window.location.reload()">Try Again</button>
            </div>
            
            <script>
                // Auto-retry connection
                let retryCount = 0;
                const maxRetries = 10;
                
                function checkConnection() {
                    if (navigator.onLine) {
                        window.location.reload();
                    } else if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(checkConnection, 3000);
                    }
                }
                
                // Start checking after 3 seconds
                setTimeout(checkConnection, 3000);
                
                // Listen for online events
                window.addEventListener('online', () => {
                    window.location.reload();
                });
            </script>
        </body>
        </html>
    `, {
        status: 200,
        statusText: 'OK',
        headers: {
            'Content-Type': 'text/html'
        }
    });
}

async function getOfflineAsset(request) {
    // Return placeholder for missing assets
    const url = new URL(request.url);
    
    if (url.pathname.includes('.css')) {
        return new Response('/* Offline */', {
            status: 200,
            headers: { 'Content-Type': 'text/css' }
        });
    }
    
    if (url.pathname.includes('.js')) {
        return new Response('// Offline', {
            status: 200,
            headers: { 'Content-Type': 'application/javascript' }
        });
    }
    
    if (url.pathname.includes('.png') || url.pathname.includes('.jpg') || url.pathname.includes('.ico')) {
        // Return 1x1 transparent pixel
        return new Response('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', {
            status: 200,
            headers: { 'Content-Type': 'image/png' }
        });
    }
    
    return new Response('Offline', { status: 503 });
}

async function getOfflineApiResponse(request) {
    return new Response(JSON.stringify({
        error: 'offline',
        message: 'You are currently offline. Please check your internet connection.',
        timestamp: new Date().toISOString()
    }), {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {
            'Content-Type': 'application/json'
        }
    });
}

// Helper functions
function isNavigationRequest(request) {
    return request.mode === 'navigate' || 
           (request.destination === 'document' && request.method === 'GET');
}

function isStaticAsset(request) {
    const url = new URL(request.url);
    return url.pathname.includes('/static/') || 
           url.pathname.includes('/media/') ||
           url.pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/);
}

function isApiRequest(request) {
    const url = new URL(request.url);
    return url.pathname.includes('/api/') || 
           url.pathname.includes('/v1/') ||
           url.pathname.startsWith('/messaging/');
}

    // Message handling for cache management and version detection
self.addEventListener('message', (event) => {
    const { type, payload } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            // User has approved the update - activate immediately
            console.log('Service Worker: SKIP_WAITING received, activating...');
            self.skipWaiting();
            // After skipWaiting, the service worker will activate and we should claim clients
            self.clients.claim();
            break;

        case 'ACTIVATE_UPDATE':
            // Alternative message name for activation
            console.log('Service Worker: ACTIVATE_UPDATE received, activating...');
            self.skipWaiting();
            self.clients.claim();
            break;
            
        case 'GET_CACHE_INFO':
            getCacheInfo().then(info => {
                event.ports[0].postMessage({ type: 'CACHE_INFO', payload: info });
            });
            break;
            
        case 'CLEAR_CACHE':
            clearCache().then(() => {
                event.ports[0].postMessage({ type: 'CACHE_CLEARED' });
            });
            break;
            
        case 'CACHE_PAGE':
            cachePage(payload.url).then(success => {
                event.ports[0].postMessage({ type: 'PAGE_CACHED', payload: { success } });
            });
            break;
            
        case 'GET_VERSION':
            event.ports[0].postMessage({ type: 'VERSION_INFO', payload: SW_VERSION });
            break;
            
        case 'CHECK_UPDATE_STATUS':
            event.ports[0].postMessage({ 
                type: 'UPDATE_STATUS', 
                payload: { updateAvailable: false } 
            });
            break;
            
        case 'ACTIVATE_UPDATE':
            self.skipWaiting();
            break;
    }
});

async function getCacheInfo() {
    const cache = await caches.open(CACHE_NAME);
    const keys = await cache.keys();
    
    return {
        cacheName: CACHE_NAME,
        itemCount: keys.length,
        urls: keys.map(request => request.url)
    };
}

async function clearCache() {
    await caches.delete(CACHE_NAME);
    await caches.delete(OFFLINE_CACHE_NAME);
}

async function cachePage(url) {
    try {
        const cache = await caches.open(CACHE_NAME);
        const response = await fetch(url);
        if (response.ok) {
            await cache.put(url, response);
            return true;
        }
    } catch (error) {
        console.error('Failed to cache page:', error);
    }
    return false;
}

// Background sync for offline messaging
self.addEventListener('sync', (event) => {
    if (event.tag === 'messaging-sync') {
        event.waitUntil(syncOfflineMessages());
    }
});

async function syncOfflineMessages() {
    try {
        // This would integrate with the offline messaging system
        console.log('Service Worker: Syncing offline messages...');
        
        // Get outbox messages from IndexedDB and try to send them
        // Implementation depends on the offline messaging system
        
    } catch (error) {
        console.error('Service Worker: Sync failed:', error);
    }
}

console.log('Service Worker: Loaded');
