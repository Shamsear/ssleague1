// Service Worker for Football Auction App

const CACHE_NAME = 'ss-auction-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/images/logo.png',
  '/static/js/notifications.js',
  '/dashboard'
];

// Install event - cache important assets
self.addEventListener('install', function(event) {
  console.log('Service Worker installing.');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching app assets');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  console.log('Service Worker activated.');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.filter(cacheName => {
            return cacheName !== CACHE_NAME;
          }).map(cacheName => {
            return caches.delete(cacheName);
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', function(event) {
  // Only cache GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip non-HTTP(S) requests
  if (!event.request.url.startsWith('http')) return;
  
  // Skip API calls
  if (event.request.url.includes('/api/')) return;
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) return response;
        
        // Otherwise, fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache if not a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response since it can only be consumed once
            let responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
              
            return response;
          })
          .catch(() => {
            // If both cache and network fail, show offline page
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
          });
      })
  );
});

// Listen for push notification events
self.addEventListener('push', function(event) {
  console.log('Push message received:', event);
  
  let notificationData = {};
  
  if (event.data) {
    notificationData = event.data.json();
  }
  
  // Since this is a closed auction, we prioritize only important notifications
  
  const title = notificationData.title || 'South Soccers PES';
  const options = {
    body: notificationData.body || 'New notification from South Soccers PES',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    data: notificationData.data || {},
    tag: notificationData.tag || 'default',
    vibrate: [100, 50, 100], // Vibration pattern for mobile devices
    renotify: notificationData.renotify || false,
    requireInteraction: true, // Keep notification visible until user interacts with it
    actions: [
      {
        action: 'view',
        title: 'View Now'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Handle notification click event
self.addEventListener('notificationclick', function(event) {
  console.log('Notification clicked:', event.notification.tag);
  
  event.notification.close();
  
  // Custom actions based on notification data
  const notificationData = event.notification.data;
  let url = '/';
  
  if (notificationData) {
    if (notificationData.url) {
      url = notificationData.url;
    } else if (notificationData.type === 'round_start') {
      url = '/team/round';
    } else if (notificationData.type === 'tiebreaker_start') {
      url = `/team/tiebreaker/${notificationData.round_id}`;
    } else if (notificationData.type === 'round_end') {
      url = '/dashboard';
    } else if (notificationData.type === 'player_won') {
      url = '/team/players';
    }
  }
  
  event.waitUntil(
    clients.matchAll({type: 'window'}).then(function(clientList) {
      // If a window client already exists, focus it
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise, open a new window
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
}); 