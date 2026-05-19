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

console.log('Service Worker: Loaded');
