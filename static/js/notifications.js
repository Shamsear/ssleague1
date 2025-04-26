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

// Notification Center functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Notification Center
    initNotificationCenter();

    // Check for notification permissions and request if needed
    checkNotificationPermission();
});

// Initialize Notification Center
function initNotificationCenter() {
    const notificationTrigger = document.getElementById('notification-trigger');
    const notificationCenter = document.getElementById('notification-center');
    const closeNotificationsBtn = document.getElementById('close-notifications');
    const markAllReadBtn = document.getElementById('mark-all-read');
    const notificationTabs = document.querySelectorAll('.notification-tab');

    if (!notificationTrigger || !notificationCenter) return;

    // Toggle notification center
    notificationTrigger.addEventListener('click', function() {
        const isExpanded = notificationTrigger.getAttribute('aria-expanded') === 'true';
        
        if (isExpanded) {
            closeNotificationCenter();
        } else {
            openNotificationCenter();
        }
    });

    // Close notification center
    closeNotificationsBtn.addEventListener('click', closeNotificationCenter);

    // Mark all notifications as read
    markAllReadBtn.addEventListener('click', function() {
        markAllNotificationsAsRead();
    });

    // Tab switching
    notificationTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            switchNotificationTab(tabId);
        });
    });

    // Close notification center when clicking outside
    document.addEventListener('click', function(event) {
        if (notificationCenter.classList.contains('translate-x-0') && 
            !notificationCenter.contains(event.target) && 
            !notificationTrigger.contains(event.target)) {
            closeNotificationCenter();
        }
    });

    // Keyboard accessibility
    notificationCenter.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeNotificationCenter();
        }
    });

    // Load notifications on init
    loadNotifications();
}

// Open notification center
function openNotificationCenter() {
    const notificationTrigger = document.getElementById('notification-trigger');
    const notificationCenter = document.getElementById('notification-center');
    
    notificationCenter.classList.remove('translate-x-full', 'opacity-0');
    notificationCenter.classList.add('translate-x-0', 'opacity-100');
    notificationTrigger.setAttribute('aria-expanded', 'true');
    
    // Reset unread count
    updateUnreadCount(0);
    
    // Set focus to the notification center for accessibility
    setTimeout(() => {
        notificationCenter.querySelector('#notification-title').focus();
    }, 100);
}

// Close notification center
function closeNotificationCenter() {
    const notificationTrigger = document.getElementById('notification-trigger');
    const notificationCenter = document.getElementById('notification-center');
    
    notificationCenter.classList.remove('translate-x-0', 'opacity-100');
    notificationCenter.classList.add('translate-x-full', 'opacity-0');
    notificationTrigger.setAttribute('aria-expanded', 'false');
    
    // Return focus to the trigger for accessibility
    notificationTrigger.focus();
}

// Switch between notification tabs
function switchNotificationTab(tabId) {
    const tabs = document.querySelectorAll('.notification-tab');
    const panels = document.querySelectorAll('.notification-panel');
    
    // Update tab states
    tabs.forEach(tab => {
        if (tab.dataset.tab === tabId) {
            tab.classList.add('text-primary', 'border-b-2', 'border-primary');
            tab.classList.remove('text-gray-600');
            tab.setAttribute('aria-selected', 'true');
        } else {
            tab.classList.remove('text-primary', 'border-b-2', 'border-primary');
            tab.classList.add('text-gray-600');
            tab.setAttribute('aria-selected', 'false');
        }
    });
    
    // Show the selected panel
    panels.forEach(panel => {
        if (panel.id === `tab-${tabId}`) {
            panel.classList.remove('hidden');
        } else {
            panel.classList.add('hidden');
        }
    });
}

// Mark all notifications as read
function markAllNotificationsAsRead() {
    const notifications = document.querySelectorAll('.notification-item[data-read="false"]');
    
    notifications.forEach(notification => {
        notification.setAttribute('data-read', 'true');
        notification.querySelector('.mark-read').setAttribute('aria-label', 'Marked as read');
        notification.classList.add('bg-gray-50');
    });
    
    // Update storage
    saveNotificationsToStorage();
    
    // Update unread count
    updateUnreadCount(0);
    
    // Announce for screen readers
    announceToScreenReader('All notifications marked as read');
}

// Create a new notification
function createNotification(data) {
    const template = document.getElementById('notification-template');
    if (!template) return null;
    
    const clone = document.importNode(template.content, true);
    const notification = clone.querySelector('.notification-item');
    
    // Set notification data attributes
    notification.setAttribute('data-id', data.id);
    notification.setAttribute('data-read', data.read ? 'true' : 'false');
    notification.setAttribute('data-important', data.important ? 'true' : 'false');
    
    // Set notification content
    notification.querySelector('.notification-title').textContent = data.title;
    notification.querySelector('.notification-message').textContent = data.message;
    notification.querySelector('.notification-time').textContent = formatNotificationTime(data.time);
    
    // Set appropriate icon based on notification type
    const iconContainer = notification.querySelector('.notification-icon');
    iconContainer.innerHTML = getNotificationTypeIcon(data.type);
    
    // Set color based on notification type
    applyNotificationStyling(notification, data.type);
    
    // Setup event listeners
    setupNotificationEventListeners(notification);
    
    return notification;
}

// Get icon based on notification type
function getNotificationTypeIcon(type) {
    switch (type) {
        case 'alert':
            return '<div class="p-1 rounded-full bg-red-100"><svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg></div>';
        case 'auction':
            return '<div class="p-1 rounded-full bg-blue-100"><svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"></path></svg></div>';
        case 'bid':
            return '<div class="p-1 rounded-full bg-green-100"><svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>';
        case 'tiebreaker':
            return '<div class="p-1 rounded-full bg-yellow-100"><svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg></div>';
        case 'info':
        default:
            return '<div class="p-1 rounded-full bg-gray-100"><svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>';
    }
}

// Apply styling based on notification type
function applyNotificationStyling(notification, type) {
    // Add specific styling based on type
    switch (type) {
        case 'alert':
            notification.classList.add('border-l-4', 'border-red-500');
            break;
        case 'auction':
            notification.classList.add('border-l-4', 'border-blue-500');
            break;
        case 'bid':
            notification.classList.add('border-l-4', 'border-green-500');
            break;
        case 'tiebreaker':
            notification.classList.add('border-l-4', 'border-yellow-500');
            break;
        case 'info':
        default:
            // No additional styling
            break;
    }
    
    // Styling for unread notifications
    if (notification.getAttribute('data-read') === 'false') {
        notification.classList.add('bg-blue-50');
    }
    
    // Styling for important notifications
    if (notification.getAttribute('data-important') === 'true') {
        const starButton = notification.querySelector('.toggle-important svg');
        starButton.classList.add('text-yellow-500', 'fill-current');
    }
}

// Setup event listeners for a notification
function setupNotificationEventListeners(notification) {
    const markReadBtn = notification.querySelector('.mark-read');
    const toggleImportantBtn = notification.querySelector('.toggle-important');
    const deleteBtn = notification.querySelector('.delete-notification');
    
    // Mark as read
    markReadBtn.addEventListener('click', function() {
        const isRead = notification.getAttribute('data-read') === 'true';
        
        if (!isRead) {
            notification.setAttribute('data-read', 'true');
            notification.classList.add('bg-gray-50');
            notification.classList.remove('bg-blue-50');
            this.setAttribute('aria-label', 'Marked as read');
            
            // Update storage and count
            saveNotificationsToStorage();
            updateUnreadCount();
        }
    });
    
    // Toggle important
    toggleImportantBtn.addEventListener('click', function() {
        const isImportant = notification.getAttribute('data-important') === 'true';
        const starIcon = this.querySelector('svg');
        
        notification.setAttribute('data-important', !isImportant ? 'true' : 'false');
        
        if (!isImportant) {
            starIcon.classList.add('text-yellow-500', 'fill-current');
            this.setAttribute('aria-label', 'Mark as not important');
        } else {
            starIcon.classList.remove('text-yellow-500', 'fill-current');
            this.setAttribute('aria-label', 'Mark as important');
        }
        
        // Update storage
        saveNotificationsToStorage();
    });
    
    // Delete notification
    deleteBtn.addEventListener('click', function() {
        notification.classList.add('animate-fade-out');
        
        setTimeout(() => {
            notification.remove();
            
            // Update storage and count
            saveNotificationsToStorage();
            updateUnreadCount();
            
            // Check if we need to show the empty state
            checkForEmptyNotificationLists();
        }, 300);
    });
}

// Format notification time (e.g., "2 hours ago")
function formatNotificationTime(timestamp) {
    const now = new Date();
    const notificationTime = new Date(timestamp);
    const diffInMs = now - notificationTime;
    const diffInSecs = Math.floor(diffInMs / 1000);
    const diffInMins = Math.floor(diffInSecs / 60);
    const diffInHours = Math.floor(diffInMins / 60);
    const diffInDays = Math.floor(diffInHours / 24);
    
    if (diffInSecs < 60) {
        return 'Just now';
    } else if (diffInMins < 60) {
        return `${diffInMins} minute${diffInMins > 1 ? 's' : ''} ago`;
    } else if (diffInHours < 24) {
        return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 7) {
        return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    } else {
        // Format as MM/DD/YYYY
        return notificationTime.toLocaleDateString();
    }
}

// Check if there are no notifications and show empty state
function checkForEmptyNotificationLists() {
    const allList = document.getElementById('all-notifications-list');
    const unreadList = document.getElementById('unread-notifications-list');
    const importantList = document.getElementById('important-notifications-list');
    
    const allItems = allList.querySelectorAll('.notification-item');
    if (allItems.length === 0) {
        allList.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No notifications yet</p></div>';
    }
    
    const unreadItems = unreadList.querySelectorAll('.notification-item');
    if (unreadItems.length === 0) {
        unreadList.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No unread notifications</p></div>';
    }
    
    const importantItems = importantList.querySelectorAll('.notification-item');
    if (importantItems.length === 0) {
        importantList.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No important notifications</p></div>';
    }
}

// Update unread notification count
function updateUnreadCount() {
    const notificationItems = document.querySelectorAll('.notification-item');
    const countBadge = document.getElementById('notification-count');
    
    let unreadCount = 0;
    
    notificationItems.forEach(item => {
        if (item.getAttribute('data-read') === 'false') {
            unreadCount++;
        }
    });
    
    if (unreadCount > 0) {
        countBadge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        countBadge.classList.remove('hidden');
        countBadge.setAttribute('aria-label', `${unreadCount} unread notifications`);
    } else {
        countBadge.classList.add('hidden');
    }
    
    return unreadCount;
}

// Save notifications to localStorage
function saveNotificationsToStorage() {
    const notificationItems = document.querySelectorAll('.notification-item');
    const notifications = [];
    
    notificationItems.forEach(item => {
        const id = item.getAttribute('data-id');
        const title = item.querySelector('.notification-title').textContent;
        const message = item.querySelector('.notification-message').textContent;
        const timeText = item.querySelector('.notification-time').textContent;
        const read = item.getAttribute('data-read') === 'true';
        const important = item.getAttribute('data-important') === 'true';
        const type = getNotificationTypeFromIcon(item.querySelector('.notification-icon').innerHTML);
        
        notifications.push({
            id,
            title,
            message,
            time: new Date().toISOString(), // Store actual timestamp
            timeText, // Store formatted time for display
            read,
            important,
            type
        });
    });
    
    localStorage.setItem('notifications', JSON.stringify(notifications));
}

// Determine notification type from icon HTML
function getNotificationTypeFromIcon(iconHtml) {
    if (iconHtml.includes('text-red-500')) return 'alert';
    if (iconHtml.includes('text-blue-500')) return 'auction';
    if (iconHtml.includes('text-green-500')) return 'bid';
    if (iconHtml.includes('text-yellow-500')) return 'tiebreaker';
    return 'info';
}

// Load notifications from localStorage
function loadNotifications() {
    const allList = document.getElementById('all-notifications-list');
    const unreadList = document.getElementById('unread-notifications-list');
    const importantList = document.getElementById('important-notifications-list');
    
    // Clear existing notifications
    allList.innerHTML = '';
    unreadList.innerHTML = '';
    importantList.innerHTML = '';
    
    // Get notifications from storage
    let notifications = localStorage.getItem('notifications');
    
    if (notifications) {
        notifications = JSON.parse(notifications);
        
        if (notifications.length > 0) {
            notifications.forEach(notificationData => {
                const notification = createNotification(notificationData);
                
                if (notification) {
                    // Add to All notifications
                    allList.appendChild(notification.cloneNode(true));
                    
                    // Add to Unread if needed
                    if (notificationData.read === false) {
                        unreadList.appendChild(notification.cloneNode(true));
                    }
                    
                    // Add to Important if needed
                    if (notificationData.important === true) {
                        importantList.appendChild(notification.cloneNode(true));
                    }
                }
            });
            
            // Setup event listeners for all notifications
            document.querySelectorAll('.notification-item').forEach(item => {
                setupNotificationEventListeners(item);
            });
            
            // Update unread count
            updateUnreadCount();
        }
    }
    
    // Check if we need to show empty states
    checkForEmptyNotificationLists();
}

// Add a new notification
function addNotification(title, message, type = 'info', important = false) {
    const id = 'notification-' + Date.now();
    const time = new Date().toISOString();
    
    const notificationData = {
        id,
        title,
        message,
        time,
        read: false,
        important,
        type
    };
    
    // Create the notification
    const notification = createNotification(notificationData);
    
    if (notification) {
        // Add to appropriate lists
        const allList = document.getElementById('all-notifications-list');
        const unreadList = document.getElementById('unread-notifications-list');
        const importantList = document.getElementById('important-notifications-list');
        
        // Remove empty state if present
        if (allList.querySelector('.text-center')) {
            allList.innerHTML = '';
        }
        
        if (unreadList.querySelector('.text-center')) {
            unreadList.innerHTML = '';
        }
        
        if (important && importantList.querySelector('.text-center')) {
            importantList.innerHTML = '';
        }
        
        // Insert at the beginning of each list
        allList.insertBefore(notification.cloneNode(true), allList.firstChild);
        unreadList.insertBefore(notification.cloneNode(true), unreadList.firstChild);
        
        if (important) {
            importantList.insertBefore(notification.cloneNode(true), importantList.firstChild);
        }
        
        // Setup event listeners
        document.querySelectorAll('.notification-item[data-id="' + id + '"]').forEach(item => {
            setupNotificationEventListeners(item);
        });
        
        // Update storage and count
        saveNotificationsToStorage();
        updateUnreadCount();
        
        // Flash notification badge
        flashNotificationBadge();
        
        // Show browser notification if applicable
        showBrowserNotification(title, message, type);
        
        // Announce for screen readers
        announceToScreenReader('New notification: ' + title);
        
        return id;
    }
    
    return null;
}

// Flash the notification badge to draw attention
function flashNotificationBadge() {
    const badge = document.getElementById('notification-count');
    
    if (badge && !badge.classList.contains('hidden')) {
        badge.classList.add('animate-ping');
        
        setTimeout(() => {
            badge.classList.remove('animate-ping');
        }, 1000);
    }
}

// Check notification permission and request if needed
function checkNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            // We need to ask for permission
            document.getElementById('notification-trigger').addEventListener('click', function() {
                Notification.requestPermission();
            }, { once: true });
        }
    }
}

// Show a browser notification
function showBrowserNotification(title, message, type) {
    if ('Notification' in window && Notification.permission === 'granted') {
        // Determine icon based on notification type
        let icon = '/static/images/icons/icon-192x192.png';
        
        switch (type) {
            case 'alert':
                icon = '/static/images/notifications/alert-icon.png';
                break;
            case 'auction':
                icon = '/static/images/notifications/auction-icon.png';
                break;
            case 'bid':
                icon = '/static/images/notifications/bid-icon.png';
                break;
            case 'tiebreaker':
                icon = '/static/images/notifications/tiebreaker-icon.png';
                break;
        }
        
        const notification = new Notification(title, {
            body: message,
            icon: icon,
            tag: 'football-auction-notification',
            vibrate: [100, 50, 100]
        });
        
        notification.onclick = function() {
            window.focus();
            openNotificationCenter();
            this.close();
        };
    }
}

// Announce message to screen readers
function announceToScreenReader(message) {
    // Check if we already have an announcer
    let announcer = document.getElementById('screen-reader-announcer');
    
    if (!announcer) {
        // Create announcer if it doesn't exist
        announcer = document.createElement('div');
        announcer.id = 'screen-reader-announcer';
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.classList.add('sr-only');
        document.body.appendChild(announcer);
    }
    
    // Set the message
    announcer.textContent = message;
    
    // Clear after a short delay
    setTimeout(() => {
        announcer.textContent = '';
    }, 3000);
}

// Add CSS for notification animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-out {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    .animate-fade-out {
        animation: fade-out 0.3s ease-out forwards;
    }
    
    @keyframes ping {
        0% { transform: scale(1); opacity: 1; }
        75%, 100% { transform: scale(1.5); opacity: 0; }
    }
    
    .animate-ping {
        animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;
    }
    
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
    }
`;
document.head.appendChild(style);

// Export functions for use in other files
window.NotificationCenter = {
    addNotification,
    openNotificationCenter,
    closeNotificationCenter
}; 