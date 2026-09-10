/**
 * PwaniNet Service Worker
 * Handles offline support, caching, and push notifications
 * Version: 1.2.0 - Updated offline page design and caching
 */

'use strict';
let CACHE_VERSION = '1.3.1';
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
    '/offline-media/',
    '/static/css/bootstrap.min.css',
    '/static/css/bootstrap-icons.css',
    '/static/css/custom.css',
    '/static/css/fonts.css',
    '/static/css/profile.css',
    '/static/css/comments.css',
    '/static/css/people-modal.css',
    '/static/notifications/css/notifications.css',
    '/static/css/downloads/offline_media_viewer.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/images/favicon.ico',
    '/static/images/favicon-96x96.png',
    '/static/images/favicon.svg',
    '/static/images/apple-touch-icon.png',
    '/static/images/web-app-manifest-192x192.png',
    '/static/images/web-app-manifest-192x192-rounded.png',
    '/static/images/web-app-manifest-512x512.png',
    '/static/images/pwaninetmonochrome.png',
    '/static/images/browserconfig.xml',
    '/static/js/messaging/offline-cache.js',
    '/static/js/messaging/network-status.js',
    '/static/js/messaging/sync-manager.js',
    '/static/js/messaging/offline-ui.js',
    '/static/js/messaging/offline-integration.js',
    '/static/js/native-pwa-install.js',
    '/static/js/downloads/download_storage.js',
    '/static/js/downloads/download_queue.js',
    '/static/js/downloads/download_manager.js',
    '/static/js/downloads/download_ui.js',
    '/static/js/downloads/offline_media_viewer.js'
];

// Page shells to cache for offline access
const PAGE_SHELLS = [
    '/',
    '/offline-media/',
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
                console.log('Service Worker: Core assets cached, activating immediately');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('Service Worker: Failed to cache core assets:', error);
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches and take control
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
                console.log('Service Worker: Activated and claiming clients');
                return self.clients.claim();
            })
            .then(() => {
                return self.clients.matchAll({ type: 'window' }).then((clients) => {
                    clients.forEach((client) => {
                        client.postMessage({
                            type: 'NEW_VERSION_ACTIVATED',
                            version: CACHE_VERSION,
                            build: CACHE_BUILD
                        });
                    });
                });
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
        badge: '/static/images/pwaninetmonochrome.png',
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
            url: '/notifications/'
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
                image: data.image || undefined,
                tag: data.tag || undefined,
                renotify: data.renotify !== undefined ? data.renotify : undefined,
                vibrate: data.vibrate || pushData.vibrate,
                requireInteraction: data.requireInteraction || pushData.requireInteraction,
                actions: data.actions || pushData.actions,
                data: {
                    notification_id: data.data?.notification_id,
                    url: data.data?.url || pushData.data.url,
                    destination_url: data.data?.destination_url,
                    notification_type: data.data?.notification_type,
                    category: data.data?.category,
                    tag: data.data?.tag || data.tag
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
    const urlToOpen = event.notification.data?.url || event.notification.data?.destination_url || '/notifications/';
    const notificationId = event.notification.data?.notification_id;

    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // Check if there's already a window open with this exact url
            for (const client of clientList) {
                if (client.url === new URL(urlToOpen, self.location.origin).href && 'focus' in client) {
                    return client.focus();
                }
            }

            // If an app window is already open, focus it and navigate to the target
            for (const client of clientList) {
                if ('focus' in client) {
                    client.focus();
                    if ('navigate' in client) {
                        return client.navigate(urlToOpen);
                    }
                    return;
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
        // Handle virtual offline media stream with range support (HTTP 206)
        if (url.pathname.startsWith('/offline-media-stream/')) {
            return await handleOfflineMediaStreamRequest(request);
        }

        // Dedicated handler for Offline Media Hub (/offline-media/) - supports HTMX partials & full page offline
        if (url.pathname === '/offline-media/') {
            return await handleOfflineMediaRequest(request);
        }

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

async function handleOfflineMediaRequest(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Network failed for /offline-media/, serving offline cache:', error);
        
        // 1. Try matching the exact request (cached partial if HTMX, or cached full document)
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // 2. Try matching the pre-cached page shell '/offline-media/'
        const cachedShell = await caches.match('/offline-media/');
        if (cachedShell) {
            return cachedShell;
        }

        return await getOfflinePage();
    }
}

async function handleNavigationRequest(request) {
    const url = new URL(request.url);

    // Explicit request to view cached pages (from offline screen action button)
    const isExplicitCacheView = url.searchParams.has('view_cache') || url.searchParams.has('cached');
    if (isExplicitCacheView) {
        const cleanUrl = new URL(request.url);
        cleanUrl.searchParams.delete('view_cache');
        cleanUrl.searchParams.delete('cached');
        const cleanReq = new Request(cleanUrl.toString(), {
            headers: request.headers,
            mode: request.mode,
            credentials: request.credentials
        });

        const cached = (await caches.match(cleanReq)) || (await caches.match(request)) || (await caches.match('/'));
        if (cached) {
            return cached;
        }
    }

    try {
        // Try network first directly
        const networkResponse = await fetch(request);
        
        // Cache successful responses ONLY if NOT an HTMX request
        const isHtmx = request.headers.get('HX-Request') === 'true';
        if (networkResponse && networkResponse.ok && !isHtmx) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Network failed for navigation request:', error);
        
        // When navigating to /offline-media/, always serve the offline media viewer shell if cached
        if (url.pathname === '/offline-media/' || url.pathname.startsWith('/offline-media/')) {
            const cachedMedia = (await caches.match('/offline-media/')) || (await caches.match(request));
            if (cachedMedia) {
                return cachedMedia;
            }
        }
        
        // When offline, present the offline screen with options to view cached pages or downloaded media
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
            return await getOfflineAsset(request);
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

async function handleOfflineMediaStreamRequest(request) {
    const url = new URL(request.url);
    const id = url.pathname.replace('/offline-media-stream/', '').split('?')[0];
    
    return new Promise((resolve) => {
        const req = indexedDB.open('pwaninet_downloads_v1', 1);
        req.onerror = () => resolve(new Response('Database error', { status: 500 }));
        req.onsuccess = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains('blobs')) {
                resolve(new Response('Store not found', { status: 404 }));
                return;
            }
            const tx = db.transaction(['blobs'], 'readonly');
            const store = tx.objectStore('blobs');
            const getReq = store.get(id);

            getReq.onerror = () => resolve(new Response('File read error', { status: 500 }));
            getReq.onsuccess = () => {
                const record = getReq.result;
                if (!record || !record.blob) {
                    resolve(new Response('Media not found offline', { status: 404 }));
                    return;
                }

                const blob = record.blob;
                const rangeHeader = request.headers.get('Range');
                const contentType = blob.type || 'video/mp4';

                if (rangeHeader) {
                    const match = rangeHeader.match(/bytes=(\d+)-(\d+)?/);
                    if (match) {
                        const start = parseInt(match[1], 10);
                        const end = match[2] ? parseInt(match[2], 10) : blob.size - 1;
                        const chunk = blob.slice(start, end + 1);

                        resolve(new Response(chunk, {
                            status: 206,
                            statusText: 'Partial Content',
                            headers: {
                                'Content-Range': `bytes ${start}-${end}/${blob.size}`,
                                'Accept-Ranges': 'bytes',
                                'Content-Length': String(chunk.size),
                                'Content-Type': contentType
                            }
                        }));
                        return;
                    }
                }

                resolve(new Response(blob, {
                    status: 200,
                    headers: {
                        'Accept-Ranges': 'bytes',
                        'Content-Length': String(blob.size),
                        'Content-Type': contentType
                    }
                }));
            };
        };
    });
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
        
        // Cache successful responses ONLY if not an HTMX request
        const isHtmx = request.headers.get('HX-Request') === 'true';
        if (networkResponse.ok && !isHtmx) {
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

    // Return cached offline media viewer response
    if (url.pathname === '/offline-media/') {
        const cached = (await caches.match(request)) || (await caches.match('/offline-media/'));
        if (cached) return cached;
    }
    
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
    // Always try to get the actual offline.html from cache first
    const offlineResponse = await caches.match('/offline.html');
    if (offlineResponse) {
        return offlineResponse;
    }
    
    // Try to fetch and cache the offline page from network
    try {
        const response = await fetch('/offline.html');
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put('/offline.html', response.clone());
            return response;
        }
    } catch (error) {
        console.log('Failed to fetch offline.html from network');
    }
    
    // Minimal fallback if offline.html is not available
    return new Response(`
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PwaniNet - Offline</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f8fafc;
                    color: #0f172a;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 20px;
                }
                .offline-container { max-width: 400px; animation: fadeInUp 0.8s ease; }
                .offline-title { font-size: 28px; font-weight: 700; margin-bottom: 16px; }
                .offline-message { font-size: 16px; color: #64748b; margin-bottom: 32px; line-height: 1.6; }
                .retry-button {
                    background: #2563eb;
                    color: white;
                    padding: 16px 24px;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    border: none;
                    text-decoration: none;
                    display: inline-block;
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(30px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <h1 class="offline-title">YOU ARE OFFLINE</h1>
                <p class="offline-message">WE WILL RECONNECT WHEN YOU HAVE INTERNET ACCESS</p>
                <button class="retry-button" onclick="window.location.reload()">Retry</button>
            </div>
            <script>
                function attemptReload() {
                    fetch('/api/health/', { mode: 'no-cors', cache: 'no-store' })
                        .then(() => window.location.reload())
                        .catch(() => {});
                }
                window.addEventListener('online', attemptReload);
                setInterval(() => { if (navigator.onLine) attemptReload(); }, 5000);
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
        return new Response('/* CSS asset unavailable offline */', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
    
    if (url.pathname.includes('.js')) {
        return new Response('/* JavaScript asset unavailable offline */', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
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
