
// Klerno Labs Enterprise PWA Service Worker
const CACHE_NAME = 'klerno-labs-v1.0.0';
const urlsToCache = [
    '/',
    '/static/css/premium.css',
    '/static/css/micro-interactions.css',
    '/static/js/micro-interactions.js',
    // Use existing SVG favicon instead of missing PNGs
    '/static/icons/favicon.svg'
];

// Install event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

// Fetch event
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            })
    );
});

// Background sync
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

function doBackgroundSync() {
    // Sync data when connection is restored
    return fetch('/api/sync')
        .then(response => response.json())
        .then(data => {
            console.log('Background sync completed:', data);
        });
}

// Push notifications
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : 'New update available!',
        // Use existing assets
        icon: '/static/icons/favicon.svg',
        badge: '/static/klerno-logo.png',
        actions: [
            { action: 'view', title: 'View' },
            { action: 'dismiss', title: 'Dismiss' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('Klerno Labs', options)
    );
});
