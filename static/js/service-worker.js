const CACHE_NAME = 'ss-league-v2';
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

// Function to check if a URL should be cached
function shouldCache(url) {
  // Never cache authentication or authenticated routes
  const nonCacheableRoutes = [
    '/logout', 
    '/login',
    '/dashboard',
    '/admin/',
    '/team_',
    '/player',
    '/players',
    '/teams',
    '/round',
    '/bid'
  ];
  
  // Check if URL contains any of the non-cacheable routes
  for (const route of nonCacheableRoutes) {
    if (url.includes(route)) {
      return false;
    }
  }
  
  // Don't cache API responses or dynamic content
  if (url.includes('/api/') || url.includes('?')) {
    return false;
  }
  
  return true;
}

// Install event - cache assets
self.addEventListener('install', event => {
  // Force new service worker to activate immediately
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  // Take control of all clients immediately
  event.waitUntil(clients.claim());
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName !== CACHE_NAME;
        }).map(cacheName => {
          console.log('Deleting old cache:', cacheName);
          return caches.delete(cacheName);
        })
      );
    })
  );
});

// Add message event listener to handle logout and clear cache
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'clearCacheOnLogout') {
    console.log('Clearing all caches due to logout');
    
    // Clear all caches, not just the named one
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          console.log('Clearing cache:', cacheName);
          return caches.delete(cacheName);
        })
      );
    });
  }
});

// Fetch event - serve from cache if available, otherwise fetch from network
self.addEventListener('fetch', event => {
  // Always bypass cache for authentication-related routes
  if (!shouldCache(event.request.url)) {
    console.log('Bypassing cache for:', event.request.url);
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
            
            // Only cache if it's a cacheable URL
            if (shouldCache(event.request.url)) {
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseToCache);
                });
            }
            
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