// Mobile detection and PWA functionality

// Check if device is mobile
function isMobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Check if app is running as PWA (standalone mode)
function isPWA() {
  return window.matchMedia('(display-mode: standalone)').matches || 
         window.navigator.standalone === true || 
         document.referrer.includes('android-app://');
}

// Check if app is running in mobile browser (not PWA)
function isMobileBrowser() {
  return isMobile() && !isPWA();
}

// Redirect mobile browser users to install page
function checkAndRedirect() {
  if (isMobileBrowser() && !window.location.pathname.includes('install.html')) {
    window.location.href = '/install.html';
    return true;
  }
  return false;
}

// Register service worker
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker registered successfully:', registration);
    } catch (error) {
      console.log('Service Worker registration failed:', error);
    }
  }
}

// PWA installation functionality
let deferredPrompt;

// Listen for beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  // Show install button if needed
  showInstallButton();
});

// Show install button
function showInstallButton() {
  const installBtn = document.getElementById('installBtn');
  if (installBtn) {
    installBtn.style.display = 'block';
    installBtn.addEventListener('click', installPWA);
  }
}

// Install PWA function
async function installPWA() {
  if (deferredPrompt) {
    // Show the install prompt
    deferredPrompt.prompt();
    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`User response to the install prompt: ${outcome}`);
    // Clear the saved prompt since it can't be used again
    deferredPrompt = null;
    
    // Hide install button
    const installBtn = document.getElementById('installBtn');
    if (installBtn) {
      installBtn.style.display = 'none';
    }
  }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  // Register service worker
  registerServiceWorker();
  
  // Check if mobile browser and redirect if needed
  if (checkAndRedirect()) {
    return; // Stop execution if redirecting
  }
  
  // Show app content only if not mobile browser
  if (!isMobileBrowser()) {
    showAppContent();
  }
});

// Show main app content
function showAppContent() {
  const appContent = document.getElementById('app-content');
  const loadingContent = document.getElementById('loading');
  
  if (appContent) {
    appContent.style.display = 'block';
  }
  
  if (loadingContent) {
    loadingContent.style.display = 'none';
  }
}

// Add install button functionality to install page
function setupInstallPage() {
  const installBtn = document.getElementById('installBtn');
  if (installBtn) {
    installBtn.addEventListener('click', () => {
      if (deferredPrompt) {
        installPWA();
      } else {
        // Show manual installation instructions
        showManualInstallInstructions();
      }
    });
  }
}

// Show manual installation instructions
function showManualInstallInstructions() {
  const instructions = document.getElementById('manual-instructions');
  if (instructions) {
    instructions.style.display = 'block';
  }
}