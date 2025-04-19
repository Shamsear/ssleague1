// Check if the browser supports service workers and push notifications
function arePushNotificationsSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window;
}

// Check if running as a PWA
function isRunningAsPWA() {
  return window.navigator.standalone || 
         window.matchMedia('(display-mode: standalone)').matches;
}

// Listen for messages from the service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', function(event) {
    console.log('Message from service worker:', event.data);
    
    // Handle resubscription requests
    if (event.data && event.data.type === 'resubscribe') {
      console.log('Resubscription requested');
      subscribeToPushNotifications();
    }
  });
}

// Register the service worker
async function registerServiceWorker() {
  try {
    const registration = await navigator.serviceWorker.register('/static/js/sw.js', {
      scope: '/'
    });
    console.log('Service Worker registered with scope:', registration.scope);
    return registration;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    return null;
  }
}

// Request notification permission
async function requestNotificationPermission() {
  try {
    document.getElementById('notification-status').innerText = 'Requesting permission...';
    document.getElementById('notification-status').className = 'text-yellow-500';
    
    const permission = await Notification.requestPermission();
    console.log('Notification permission:', permission);
    
    if (permission === 'granted') {
      localStorage.setItem('notificationPermission', 'granted');
      document.getElementById('notification-status').innerText = 'Notifications enabled';
      document.getElementById('notification-status').className = 'text-green-500';
      document.getElementById('enable-notifications').classList.add('hidden');
      document.getElementById('disable-notifications').classList.remove('hidden');
      
      // Subscribe
      await subscribeToPushNotifications();
    } else if (permission === 'denied') {
      localStorage.setItem('notificationPermission', 'denied');
      document.getElementById('notification-status').innerText = 'Notifications blocked';
      document.getElementById('notification-status').className = 'text-red-500';
      document.getElementById('notification-info').innerText = 'Please enable notifications in your browser settings';
    } else {
      // default is "default" which means dismissed without making a choice
      localStorage.setItem('notificationPermission', 'default');
      document.getElementById('notification-status').innerText = 'Notifications not enabled';
      document.getElementById('notification-status').className = 'text-gray-500';
    }
  } catch (error) {
    console.error('Error requesting notification permission:', error);
    document.getElementById('notification-status').innerText = 'Error requesting permission';
    document.getElementById('notification-status').className = 'text-red-500';
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

// Check subscription status
async function checkSubscriptionStatus() {
  try {
    if (!arePushNotificationsSupported()) {
      return false;
    }
    
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    return !!subscription;
  } catch (error) {
    console.error('Error checking subscription status:', error);
    return false;
  }
}

// Subscribe to push notifications
async function subscribeToPushNotifications() {
  try {
    // Check if already subscribed
    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      console.log('Already subscribed to push notifications');
      // Save subscription to localStorage for iOS persistence
      try {
        localStorage.setItem('pushSubscription', JSON.stringify(subscription.toJSON()));
        localStorage.setItem('notificationPermission', 'granted');
      } catch (e) {
        console.warn('Could not save subscription to localStorage:', e);
      }
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
    
    // Save to localStorage for iOS persistence
    try {
      localStorage.setItem('pushSubscription', JSON.stringify(subscription.toJSON()));
      localStorage.setItem('notificationPermission', 'granted');
    } catch (e) {
      console.warn('Could not save subscription to localStorage:', e);
    }
    
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
    
    document.getElementById('notification-status').innerText = 'Notifications enabled for this device';
    document.getElementById('notification-status').className = 'text-green-500';
    document.getElementById('enable-notifications').classList.add('hidden');
    document.getElementById('disable-notifications').classList.remove('hidden');
    
    // Test notification if on development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      setTimeout(async () => {
        await fetch('/api/test-notification', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      }, 3000);
    }
    
    // Request background sync if supported
    if ('SyncManager' in window) {
      try {
        await registration.sync.register('sync-subscription');
      } catch (err) {
        console.log('Background sync not supported:', err);
      }
    }
    
    return subscription;
  } catch (error) {
    console.error('Error subscribing to push notifications:', error);
    document.getElementById('notification-status').innerText = 'Error enabling notifications: ' + error.message;
    document.getElementById('notification-status').className = 'text-red-500';
    return null;
  }
}

// Unsubscribe from push notifications
async function unsubscribeFromPushNotifications() {
  try {
    document.getElementById('notification-status').innerText = 'Disabling notifications...';
    document.getElementById('notification-status').className = 'text-yellow-500';
    
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
      
      // Clear localStorage entries
      try {
        localStorage.removeItem('pushSubscription');
        localStorage.setItem('notificationPermission', 'default');
      } catch (e) {
        console.warn('Could not update localStorage:', e);
      }
      
      // Update UI
      document.getElementById('notification-status').innerText = 'Notifications disabled';
      document.getElementById('notification-status').className = 'text-gray-500';
      document.getElementById('enable-notifications').classList.remove('hidden');
      document.getElementById('disable-notifications').classList.add('hidden');
      
      return true;
    } else {
      console.log('No subscription found to unsubscribe from');
      document.getElementById('notification-status').innerText = 'No active subscription found';
      document.getElementById('notification-status').className = 'text-gray-500';
      document.getElementById('enable-notifications').classList.remove('hidden');
      document.getElementById('disable-notifications').classList.add('hidden');
      return false;
    }
  } catch (error) {
    console.error('Error unsubscribing from push notifications:', error);
    document.getElementById('notification-status').innerText = 'Error disabling notifications';
    document.getElementById('notification-status').className = 'text-red-500';
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

// Display browser-specific notification instructions
function displayBrowserInstructions() {
  const ua = navigator.userAgent;
  let instructions = '';
  
  if (/iPad|iPhone|iPod/.test(ua)) {
    if (!isRunningAsPWA()) {
      instructions = 'To receive notifications on iOS, you must add this site to your home screen and open it from there.';
      
      // Add detailed iOS installation guide if not already shown
      setTimeout(() => {
        if (!document.getElementById('ios-install-guide')) {
          const container = document.getElementById('notification-container');
          if (container) {
            const iosGuide = document.createElement('div');
            iosGuide.id = 'ios-install-guide';
            iosGuide.className = 'mt-3 p-3 bg-blue-50 text-xs rounded-xl border border-blue-100 w-full';
            iosGuide.innerHTML = `
              <p class="font-medium mb-1">How to install on iOS:</p>
              <ol class="list-decimal pl-5 space-y-1">
                <li>Tap the share icon at the bottom of Safari</li>
                <li>Scroll down and tap "Add to Home Screen"</li>
                <li>Tap "Add" in the top right</li>
                <li>Close Safari completely (swipe up from bottom)</li>
                <li>Open the app from your home screen</li>
              </ol>
              <p class="mt-2 italic text-blue-600">This is required for notifications to work on iOS.</p>
            `;
            container.parentNode.insertBefore(iosGuide, container.nextSibling);
          }
        }
      }, 500);
    } else {
      instructions = 'Notifications will work when this app is closed. You launched it correctly from the home screen.';
    }
  } else if (/android/i.test(ua)) {
    if (/chrome/i.test(ua)) {
      instructions = 'For reliable notifications on Android, please keep Chrome running in the background.';
    } else if (/firefox/i.test(ua)) {
      instructions = 'Make sure Firefox is allowed to run in the background in your device settings.';
    }
  } else if (/Windows/.test(ua)) {
    instructions = 'Allow notifications in your browser settings to receive updates even when the site is closed.';
  }
  
  if (instructions) {
    const infoElement = document.getElementById('notification-info');
    if (infoElement) {
      infoElement.innerText = instructions;
    }
  }
}

// Initialize notifications
async function initNotifications() {
  if (!arePushNotificationsSupported()) {
    console.log('Push notifications are not supported by this browser');
    
    const container = document.getElementById('notification-container');
    if (container) {
      container.classList.add('hidden');
    }
    return;
  }
  
  // Set checking status
  const statusElement = document.getElementById('notification-status');
  if (statusElement) {
    statusElement.innerText = 'Checking notification status...';
    statusElement.className = 'text-gray-500';
  }
  
  displayBrowserInstructions();
  
  // First check localStorage for persisted state
  const savedPermission = localStorage.getItem('notificationPermission');
  const savedSubscription = localStorage.getItem('pushSubscription');
  
  // Register service worker
  const registration = await registerServiceWorker();
  if (!registration) {
    if (statusElement) {
      statusElement.innerText = 'Service worker failed to register';
      statusElement.className = 'text-red-500';
    }
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
  } else {
    // Default state - show enable button
    document.getElementById('notification-status').innerText = 'Notifications not enabled';
    document.getElementById('notification-status').className = 'text-gray-500';
    document.getElementById('enable-notifications').classList.remove('hidden');
    document.getElementById('disable-notifications').classList.add('hidden');
    
    // Special case for iOS PWA with saved permission
    if (savedPermission === 'granted' && isRunningAsPWA()) {
      document.getElementById('notification-status').innerText = 'Tap Enable to restore notifications';
      document.getElementById('notification-status').className = 'text-yellow-500';
    }
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