// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        console.log('Service Worker registered with scope:', registration.scope);
      })
      .catch((error) => {
        console.error('Service Worker registration failed:', error);
      });
  });
}

// Smooth scrolling for internal links
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      const targetElement = document.querySelector(targetId);
      
      if (targetElement) {
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        
        // Update URL hash without jumping
        history.pushState(null, null, targetId);
      }
    });
  });
});

// Add to home screen functionality - Disabled
// let deferredPrompt;
// const addBtn = document.createElement('button');
// addBtn.style.display = 'none';

// window.addEventListener('beforeinstallprompt', (e) => {
//   // Prevent Chrome 67 and earlier from automatically showing the prompt
//   e.preventDefault();
//   // Stash the event so it can be triggered later
//   deferredPrompt = e;
//   // Update UI to notify the user they can add to home screen
//   showInstallPromotion();
// });

// function showInstallPromotion() {
//   // Create a notification that shows at the top of the page
//   const container = document.createElement('div');
//   container.id = 'pwa-install-banner';
//   container.classList.add('fixed', 'top-0', 'left-0', 'right-0', 'z-50', 'p-4', 'bg-primary', 'text-white', 'flex', 'justify-between', 'items-center');
//   
//   const message = document.createElement('div');
//   message.textContent = 'Install this app on your device for offline use';
//   
//   const btnContainer = document.createElement('div');
//   
//   const installBtn = document.createElement('button');
//   installBtn.textContent = 'Install';
//   installBtn.classList.add('px-4', 'py-2', 'bg-white', 'text-primary', 'rounded', 'mr-2');
//   installBtn.onclick = installPWA;
//   
//   const closeBtn = document.createElement('button');
//   closeBtn.textContent = 'Not now';
//   closeBtn.classList.add('px-4', 'py-2', 'bg-transparent', 'text-white', 'border', 'border-white', 'rounded');
//   closeBtn.onclick = () => {
//     document.getElementById('pwa-install-banner').remove();
//   };
//   
//   btnContainer.appendChild(installBtn);
//   btnContainer.appendChild(closeBtn);
//   
//   container.appendChild(message);
//   container.appendChild(btnContainer);
//   
//   // Add the banner only if it doesn't already exist
//   if (!document.getElementById('pwa-install-banner')) {
//     document.body.prepend(container);
//   }
// }

// function installPWA() {
//   if (!deferredPrompt) {
//     return;
//   }
//   // Show the install prompt
//   deferredPrompt.prompt();
//   
//   // Wait for the user to respond to the prompt
//   deferredPrompt.userChoice.then((choiceResult) => {
//     if (choiceResult.outcome === 'accepted') {
//       console.log('User accepted the install prompt');
//     } else {
//       console.log('User dismissed the install prompt');
//     }
//     deferredPrompt = null;
//     
//     // Hide the install banner
//     const banner = document.getElementById('pwa-install-banner');
//     if (banner) {
//       banner.remove();
//     }
//   });
// } 