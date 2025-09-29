// Klerno Labs Service Worker - Advanced PWA with Caching
const CACHE_NAME = 'klerno-labs-v1.0.0';
const RUNTIME_CACHE = 'klerno-runtime-v1.0.0';

// Critical resources to cache on install
const CACHE_URLS = [
    '/',
    '/static/css/design-system.css',
    '/static/css/performance-utils.css',
    '/static/js/main.js',
    '/static/klerno-logo.png',
    '/static/klerno-wordmark.png',
    '/static/favicon.ico',
    '/offline.html'  // Offline fallback page
];

// Network-first URLs (API endpoints)
const NETWORK_FIRST_URLS = [
    '/api/',
    '/auth/',
    '/admin/',
    '/healthz'
];

// Cache-first URLs (static assets)
const CACHE_FIRST_URLS = [
    '/static/',
    'https://fonts.googleapis.com/',
    'https://cdn.jsdelivr.net/'
];

// Install event - cache critical resources
self.addEventListener('install', event => {
    console.log('🔧 Service Worker: Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('📦 Service Worker: Caching critical resources');
                return cache.addAll(CACHE_URLS);
            })
            .then(() => {
                console.log('✅ Service Worker: Installation complete');
                return self.skipWaiting(); // Activate immediately
            })
            .catch(error => {
                console.error('❌ Service Worker: Installation failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker: Activating...');

    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
                            console.log('🗑️ Service Worker: Deleting old cache', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('✅ Service Worker: Activation complete');
                return self.clients.claim(); // Take control immediately
            })
    );
});

// Fetch event - intelligent caching strategy
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome-extension and other non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }

    event.respondWith(handleFetch(request));
});

async function handleFetch(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    try {
        // Strategy 1: Network First (API and dynamic content)
        if (NETWORK_FIRST_URLS.some(pattern => pathname.startsWith(pattern))) {
            return await networkFirst(request);
        }

        // Strategy 2: Cache First (Static assets)
        if (CACHE_FIRST_URLS.some(pattern => pathname.startsWith(pattern) || url.origin !== location.origin)) {
            return await cacheFirst(request);
        }

        // Strategy 3: Stale While Revalidate (HTML pages)
        if (request.headers.get('Accept').includes('text/html')) {
            return await staleWhileRevalidate(request);
        }

        // Default: Network with cache fallback
        return await networkWithCacheFallback(request);

    } catch (error) {
        console.error('Service Worker: Fetch error', error);
        return await handleFetchError(request);
    }
}

// Network First Strategy - For API calls
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        // Fallback to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/offline.html');
        }

        throw error;
    }
}

// Cache First Strategy - For static assets
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Cache first failed for', request.url);
        throw error;
    }
}

// Stale While Revalidate - For HTML pages
async function staleWhileRevalidate(request) {
    const cache = await caches.open(RUNTIME_CACHE);
    const cachedResponse = await cache.match(request);

    // Start network request in background
    const networkResponsePromise = fetch(request).then(response => {
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    }).catch(() => {
        // Network failed, but we might have cache
    });

    // Return cached version immediately if available
    if (cachedResponse) {
        return cachedResponse;
    }

    // Wait for network if no cache
    return networkResponsePromise;
}

// Network with Cache Fallback - Default strategy
async function networkWithCacheFallback(request) {
    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        throw error;
    }
}

// Handle fetch errors
async function handleFetchError(request) {
    // For navigation requests, show offline page
    if (request.mode === 'navigate') {
        const offlinePage = await caches.match('/offline.html');
        if (offlinePage) {
            return offlinePage;
        }
    }

    // For other requests, return a generic error response
    return new Response(
        JSON.stringify({ error: 'Network unavailable', offline: true }),
        {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' }
        }
    );
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('🔄 Service Worker: Background sync triggered', event.tag);

    if (event.tag === 'background-sync') {
        event.waitUntil(handleBackgroundSync());
    }
});

async function handleBackgroundSync() {
    // Handle offline actions when back online
    try {
        // Send any pending analytics or user actions
        console.log('🔄 Service Worker: Processing background sync');

        // You can implement actual background sync logic here
        // For example, sending cached form submissions, analytics, etc.

    } catch (error) {
        console.error('Service Worker: Background sync failed', error);
    }
}

// Push notifications
self.addEventListener('push', event => {
    const options = {
        body: event.data ? event.data.text() : 'New update available',
        icon: '/static/klerno-logo.png',
        badge: '/static/klerno-logo.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: '1'
        },
        actions: [
            {
                action: 'explore',
                title: 'View Dashboard',
                icon: '/static/klerno-logo.png'
            },
            {
                action: 'close',
                title: 'Close notification',
                icon: '/static/klerno-logo.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('Klerno Labs', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/dashboard')
        );
    }
});

// Message handling from main thread
self.addEventListener('message', event => {
    console.log('Service Worker: Received message', event.data);

    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});

// Performance monitoring
self.addEventListener('fetch', event => {
    // Track fetch performance
    const startTime = performance.now();

    event.respondWith(
        handleFetch(event.request).then(response => {
            const duration = performance.now() - startTime;

            // Log slow requests
            if (duration > 1000) {
                console.warn(`Slow request: ${event.request.url} took ${duration}ms`);
            }

            return response;
        })
    );
});

console.log('🚀 Klerno Labs Service Worker loaded successfully');
