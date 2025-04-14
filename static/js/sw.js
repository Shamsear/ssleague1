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
  
  // Configure notification options
  const title = notificationData.title || 'South Soccers PES';
  const options = {
    body: notificationData.body || 'New notification from South Soccers PES',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    data: notificationData.data || {},
    tag: notificationData.tag || 'default',
    vibrate: [100, 50, 100], // Vibration pattern
    renotify: notificationData.renotify || false,
    actions: []
  };
  
  // Add actions based on notification type
  const notificationType = notificationData.data?.type;
  
  if (notificationType === 'round_start') {
    options.actions = [
      {
        action: 'view_round',
        title: 'View Round'
      }
    ];
  } else if (notificationType === 'bid_placed' || notificationType === 'bid_deleted') {
    options.actions = [
      {
        action: 'view_bids',
        title: 'View Bids'
      }
    ];
  } else if (notificationType === 'player_won') {
    options.actions = [
      {
        action: 'view_players',
        title: 'View Players'
      }
    ];
  } else if (notificationType === 'tiebreaker_start') {
    options.actions = [
      {
        action: 'view_tiebreaker',
        title: 'View Tiebreaker'
      }
    ];
  }
  
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
  
  // Handle action buttons
  if (event.action === 'view_round') {
    url = '/team/round';
  } else if (event.action === 'view_bids') {
    url = '/team/round';
  } else if (event.action === 'view_players') {
    url = '/team/players';
  } else if (event.action === 'view_tiebreaker' && notificationData.round_id) {
    url = `/team/tiebreaker/${notificationData.round_id}`;
  } else if (notificationData) {
    // Use URL from notification data if available
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
    } else if (notificationData.type === 'bid_placed' || notificationData.type === 'bid_deleted') {
      url = '/team/round';
    } else if (notificationData.type === 'user_approved') {
      url = '/dashboard';
    } else if (notificationData.type === 'timer_update') {
      if (notificationData.round_id && notificationData.is_tiebreaker) {
        url = `/team/tiebreaker/${notificationData.round_id}`;
      } else {
        url = '/team/round';
      }
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