// Check if the browser supports service workers and push notifications
function arePushNotificationsSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window;
}

// Register the service worker
async function registerServiceWorker() {
  try {
    const registration = await navigator.serviceWorker.register('/static/js/sw.js');
    console.log('Service Worker registered with scope:', registration.scope);
    return registration;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    return null;
  }
}

// Request permission for notifications
async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      console.log('Notification permission granted');
      document.getElementById('notification-status').innerText = 'Notifications enabled';
      document.getElementById('notification-status').className = 'text-green-500';
      document.getElementById('enable-notifications').classList.add('hidden');
      document.getElementById('disable-notifications').classList.remove('hidden');
      return true;
    } else {
      console.log('Notification permission denied');
      document.getElementById('notification-status').innerText = 'Notifications disabled';
      document.getElementById('notification-status').className = 'text-red-500';
      document.getElementById('enable-notifications').classList.remove('hidden');
      document.getElementById('disable-notifications').classList.add('hidden');
      return false;
    }
  } catch (error) {
    console.error('Error requesting notification permission:', error);
    return false;
  }
}

// Get the public VAPID key from the server
async function getPublicVapidKey() {
  try {
    const response = await fetch('/api/vapid-public-key');
    const data = await response.json();
    return data.publicKey;
  } catch (error) {
    console.error('Error fetching VAPID key:', error);
    return null;
  }
}

// Subscribe to push notifications
async function subscribeToPushNotifications() {
  try {
    // Check if already subscribed
    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      return subscription;
    }
    
    // Get the public VAPID key
    const publicKey = await getPublicVapidKey();
    if (!publicKey) {
      throw new Error('Unable to get VAPID public key');
    }
    
    // Convert the public key to a Uint8Array
    const key = urlBase64ToUint8Array(publicKey);
    
    // Subscribe the user
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: key
    });
    
    console.log('User subscribed to push notifications');
    
    // Send the subscription to the server
    await fetch('/api/subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        subscription: subscription,
        user_id: getUserId()
      })
    });
    
    return subscription;
  } catch (error) {
    console.error('Error subscribing to push notifications:', error);
    return null;
  }
}

// Unsubscribe from push notifications
async function unsubscribeFromPushNotifications() {
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      // Send the unsubscribe request to the server
      await fetch('/api/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subscription: subscription,
          user_id: getUserId()
        })
      });
      
      // Unsubscribe on the browser
      await subscription.unsubscribe();
      console.log('User unsubscribed from push notifications');
      
      document.getElementById('notification-status').innerText = 'Notifications disabled';
      document.getElementById('notification-status').className = 'text-red-500';
      document.getElementById('enable-notifications').classList.remove('hidden');
      document.getElementById('disable-notifications').classList.add('hidden');
      
      return true;
    }
    return false;
  } catch (error) {
    console.error('Error unsubscribing from push notifications:', error);
    return false;
  }
}

// Get the current user ID from the page
function getUserId() {
  const userIdElement = document.getElementById('user-id');
  return userIdElement ? userIdElement.value : null;
}

// Helper function to convert base64 string to Uint8Array
// Needed for the applicationServerKey property
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Initialize notifications
async function initNotifications() {
  if (!arePushNotificationsSupported()) {
    console.log('Push notifications are not supported by this browser');
    document.getElementById('notification-container').classList.add('hidden');
    return;
  }
  
  // Register service worker
  const registration = await registerServiceWorker();
  if (!registration) {
    return;
  }
  
  // Check current permission status
  if (Notification.permission === 'granted') {
    document.getElementById('notification-status').innerText = 'Notifications enabled';
    document.getElementById('notification-status').className = 'text-green-500';
    document.getElementById('enable-notifications').classList.add('hidden');
    document.getElementById('disable-notifications').classList.remove('hidden');
    
    // Re-subscribe if needed
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      await subscribeToPushNotifications();
    }
  } else if (Notification.permission === 'denied') {
    document.getElementById('notification-status').innerText = 'Notifications blocked';
    document.getElementById('notification-status').className = 'text-red-500';
    document.getElementById('notification-info').innerText = 'Please enable notifications in your browser settings';
  }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
  // Only proceed if the notification container exists
  const notificationContainer = document.getElementById('notification-container');
  if (!notificationContainer) {
    return;
  }
  
  initNotifications();
  
  // Enable notifications button
  const enableBtn = document.getElementById('enable-notifications');
  if (enableBtn) {
    enableBtn.addEventListener('click', async function() {
      const permissionGranted = await requestNotificationPermission();
      if (permissionGranted) {
        await subscribeToPushNotifications();
      }
    });
  }
  
  // Disable notifications button
  const disableBtn = document.getElementById('disable-notifications');
  if (disableBtn) {
    disableBtn.addEventListener('click', async function() {
      await unsubscribeFromPushNotifications();
    });
  }
}); 