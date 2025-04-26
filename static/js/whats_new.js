// What's New Feature
document.addEventListener('DOMContentLoaded', function() {
    initWhatsNew();
});

function initWhatsNew() {
    const modal = document.getElementById('whats-new-modal');
    
    // If modal doesn't exist, return
    if (!modal) return;
    
    const backdrop = document.getElementById('whats-new-backdrop');
    const closeBtn = document.getElementById('close-whats-new');
    const dismissBtn = document.getElementById('dismiss-whats-new');
    const dontShowCheckbox = document.getElementById('dont-show-again');
    
    // Current version
    const currentVersion = '2.0.0';  // Update this with each release
    
    // Check if we should show what's new modal
    checkShouldShowWhatsNew(currentVersion).then(shouldShow => {
        if (shouldShow) {
            openWhatsNewModal();
        }
    });
    
    // Event listeners
    if (backdrop) {
        backdrop.addEventListener('click', closeWhatsNewModal);
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeWhatsNewModal);
    }
    
    if (dismissBtn) {
        dismissBtn.addEventListener('click', function() {
            // Check if "don't show again" is checked
            const dontShowAgain = dontShowCheckbox && dontShowCheckbox.checked;
            
            // Save preference in localStorage if needed
            if (dontShowAgain) {
                localStorage.setItem('whats_new_dismissed_version', currentVersion);
            }
            
            closeWhatsNewModal();
        });
    }
    
    // Keyboard accessibility
    modal.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeWhatsNewModal();
        }
    });
    
    // Trap focus within modal for accessibility
    setupFocusTrap(modal);
}

// Check if we should show the What's New modal
async function checkShouldShowWhatsNew(currentVersion) {
    // Get the last dismissed version from localStorage
    const lastDismissedVersion = localStorage.getItem('whats_new_dismissed_version');
    
    // Get the last seen version from localStorage
    const lastSeenVersion = localStorage.getItem('whats_new_last_seen_version');
    
    // If user has dismissed this version, don't show
    if (lastDismissedVersion === currentVersion) {
        return false;
    }
    
    // If user hasn't seen this version yet, show
    if (lastSeenVersion !== currentVersion) {
        // Update the last seen version
        localStorage.setItem('whats_new_last_seen_version', currentVersion);
        return true;
    }
    
    return false;
}

// Open the What's New modal
function openWhatsNewModal() {
    const modal = document.getElementById('whats-new-modal');
    if (!modal) return;
    
    // Show modal with animation
    modal.classList.remove('invisible', 'opacity-0');
    modal.setAttribute('aria-hidden', 'false');
    
    // Animate modal content
    const modalContent = modal.querySelector('.relative');
    modalContent.classList.remove('translate-y-8');
    
    // Prevent body scrolling
    document.body.classList.add('overflow-hidden');
    
    // Focus first interactive element for accessibility
    setTimeout(() => {
        const firstFocusable = getFocusableElements(modal)[0];
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }, 100);
    
    // Announce to screen readers
    announceToScreenReader('What\'s new dialog opened');
}

// Close the What's New modal
function closeWhatsNewModal() {
    const modal = document.getElementById('whats-new-modal');
    if (!modal) return;
    
    // Hide modal with animation
    modal.classList.add('opacity-0');
    
    // Animate modal content
    const modalContent = modal.querySelector('.relative');
    modalContent.classList.add('translate-y-8');
    
    // After animation completes, hide modal completely
    setTimeout(() => {
        modal.classList.add('invisible');
        modal.setAttribute('aria-hidden', 'true');
        
        // Allow body scrolling again
        document.body.classList.remove('overflow-hidden');
    }, 300);
    
    // Announce to screen readers
    announceToScreenReader('What\'s new dialog closed');
}

// Setup focus trap within modal for accessibility
function setupFocusTrap(modal) {
    modal.addEventListener('keydown', function(e) {
        if (e.key !== 'Tab') return;
        
        const focusableElements = getFocusableElements(modal);
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        // If shift+tab and on first element, move to last element
        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } 
        // If tab and on last element, move to first element
        else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    });
}

// Get all focusable elements within a container
function getFocusableElements(container) {
    return Array.from(
        container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
    ).filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null);
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
        announcer.className = 'sr-only';
        document.body.appendChild(announcer);
    }
    
    // Set the message
    announcer.textContent = message;
    
    // Clear after a short delay
    setTimeout(() => {
        announcer.textContent = '';
    }, 3000);
}

// Function to manually trigger the What's New modal
function showWhatsNew() {
    openWhatsNewModal();
}

// Export functions for use in other files
window.WhatsNew = {
    show: showWhatsNew
}; 