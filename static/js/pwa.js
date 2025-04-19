// Check if service worker is supported
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then(registration => {
        console.log('ServiceWorker registration successful with scope: ', registration.scope);
      })
      .catch(error => {
        console.log('ServiceWorker registration failed: ', error);
      });
  });
}

// Add to home screen functionality
let deferredPrompt;
const addBtn = document.querySelector('.add-to-home');

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent Chrome 67 and earlier from automatically showing the prompt
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  // Update UI to notify the user they can add to home screen
  if (addBtn) {
    addBtn.style.display = 'block';
  }
});

// Handle add to home screen button click
if (addBtn) {
  addBtn.addEventListener('click', () => {
    // Hide our user interface that shows our A2HS button
    addBtn.style.display = 'none';
    // Show the prompt
    deferredPrompt.prompt();
    // Wait for the user to respond to the prompt
    deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted the A2HS prompt');
      } else {
        console.log('User dismissed the A2HS prompt');
      }
      deferredPrompt = null;
    });
  });
}

// iOS specific handling
// Check if the user is on iOS
const isIos = () => {
  const userAgent = window.navigator.userAgent.toLowerCase();
  return /iphone|ipad|ipod/.test(userAgent);
};

// Check if the device is in standalone mode (already installed)
const isInStandaloneMode = () => ('standalone' in window.navigator) && (window.navigator.standalone);

// Show iOS install prompt
document.addEventListener('DOMContentLoaded', () => {
  const iosPrompt = document.querySelector('.ios-prompt');
  // Show prompt only on iOS devices that aren't in standalone mode
  if (isIos() && !isInStandaloneMode() && iosPrompt) {
    iosPrompt.style.display = 'block';
  }
}); 