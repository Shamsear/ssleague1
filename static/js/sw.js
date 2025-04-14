// Service Worker for Football Auction App

self.addEventListener('install', function(event) {
  console.log('Service Worker installing.');
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  console.log('Service Worker activated.');
  return self.clients.claim();
});

// Listen for push notification events
self.addEventListener('push', function(event) {
  console.log('Push message received:', event);
  
  let notificationData = {};
  
  if (event.data) {
    notificationData = event.data.json();
  }
  
  // Since this is a closed auction, we prioritize only important notifications
  // We don't need outbid notifications as players can't see others' bids
  
  const title = notificationData.title || 'South Soccers PES';
  const options = {
    body: notificationData.body || 'New notification from South Soccers PES',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    data: notificationData.data || {},
    tag: notificationData.tag || 'default',
    vibrate: [100, 50, 100], // Vibration pattern
    renotify: notificationData.renotify || false
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