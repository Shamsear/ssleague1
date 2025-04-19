const CACHE_NAME = 'ss-league-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/images/logo.png',
  '/static/images/icons/icon-192x192.png',
  '/static/images/icons/icon-512x512.png',
  '/static/js/notifications.js',
  '/static/js/pwa.js',
  '/static/offline.html',
  // Add more URLs to cache as needed
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName !== CACHE_NAME;
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

// Add message event listener to handle logout and clear cache
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'clearCacheOnLogout') {
    self.skipWaiting();
    caches.delete(CACHE_NAME);
  }
});

// Fetch event - serve from cache if available, otherwise fetch from network
self.addEventListener('fetch', event => {
  // Skip cache for logout and login routes
  if (event.request.url.includes('/logout') || event.request.url.includes('/login')) {
    return event.respondWith(fetch(event.request));
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        
        // Clone the request
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest)
          .then(response => {
            // Check if we received a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response
            const responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                // Don't cache API responses, dynamic content, or authentication-related paths
                if (!event.request.url.includes('/api/') && 
                    !event.request.url.includes('?') &&
                    !event.request.url.includes('/login') &&
                    !event.request.url.includes('/logout')) {
                  cache.put(event.request, responseToCache);
                }
              });
              
            return response;
          })
          .catch(error => {
            // If the request fails (offline), serve the offline page for HTML requests
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match('/static/offline.html');
            }
            
            // For non-HTML requests that fail, just return the error
            throw error;
          });
      })
  );
}); 