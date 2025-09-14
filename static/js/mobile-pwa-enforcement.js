/**
 * Mobile PWA Enforcement Script
 * Prevents mobile browser access and forces PWA installation
 */

// Configuration
const PWA_ENFORCEMENT_CONFIG = {
    // Block mobile browsers (phones)
    blockMobile: true,
    // Block tablets (usually false for better UX)
    blockTablets: false,
    // Allow users to continue in browser after seeing modal
    allowBrowserFallback: true,
    // Show modal delay in milliseconds
    modalDelay: 500,
    // Remember user choice for session
    rememberChoice: true
};

// Mobile and PWA detection functions
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function isTablet() {
    return /iPad|Android.*Tablet|Windows.*Touch/i.test(navigator.userAgent);
}

function isStandalonePWA() {
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone === true ||
           document.referrer.includes('android-app://');
}

function isInPWAWebView() {
    // Check for PWA-specific indicators
    return window.navigator.standalone === true || 
           window.matchMedia('(display-mode: standalone)').matches ||
           window.matchMedia('(display-mode: fullscreen)').matches ||
           window.matchMedia('(display-mode: minimal-ui)').matches;
}

function getDeviceType() {
    if (isTablet()) return 'tablet';
    if (isMobileDevice()) return 'mobile';
    return 'desktop';
}

// Check if user should be blocked
function shouldBlockMobileAccess() {
    const deviceType = getDeviceType();
    
    // Allow desktop always
    if (deviceType === 'desktop') return false;
    
    // Check tablet blocking setting
    if (deviceType === 'tablet') {
        if (!PWA_ENFORCEMENT_CONFIG.blockTablets) return false;
        return !isStandalonePWA() && !isInPWAWebView();
    }
    
    // Check mobile blocking setting
    if (deviceType === 'mobile') {
        if (!PWA_ENFORCEMENT_CONFIG.blockMobile) return false;
        return !isStandalonePWA() && !isInPWAWebView();
    }
    
    return false;
}

// Ensure proper viewport for mobile display
function ensureMobileViewport() {
    let viewport = document.querySelector('meta[name="viewport"]');
    if (!viewport) {
        viewport = document.createElement('meta');
        viewport.name = 'viewport';
        document.head.appendChild(viewport);
    }
    
    // Store original viewport
    const originalViewport = viewport.content;
    viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
    
    return originalViewport;
}

// Restore original viewport
function restoreViewport(originalViewport) {
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport && originalViewport) {
        viewport.content = originalViewport;
    }
}

// Adjust modal height based on viewport
function adjustModalHeight() {
    const modal = document.getElementById('mobile-block-modal');
    const modalContent = modal?.querySelector('.bg-white');
    
    if (!modal || !modalContent) return;
    
    const viewportHeight = window.innerHeight;
    const availableHeight = viewportHeight - 32; // Account for padding
    
    // For very small screens, make adjustments
    if (viewportHeight < 600) {
        modalContent.style.maxHeight = '95vh';
        modalContent.style.padding = '12px';
        
        // Hide benefits section on very small screens
        const benefitsSection = modalContent.querySelector('.bg-blue-50');
        if (benefitsSection && viewportHeight < 500) {
            benefitsSection.style.display = 'none';
        }
        
        // Reduce instruction area height
        const instructionsArea = modalContent.querySelector('.max-h-48');
        if (instructionsArea) {
            instructionsArea.style.maxHeight = '100px';
        }
    }
    
    // Handle landscape orientation on phones
    if (window.innerHeight < 500 && window.innerWidth > window.innerHeight) {
        modal.style.alignItems = 'flex-start';
        modal.style.paddingTop = '10px';
        modalContent.style.marginTop = '0';
        modalContent.style.marginBottom = '0';
        modalContent.style.maxHeight = '98vh';
    }
}

// Create and show mobile block modal
function showMobileBlockModal() {
    // Remove any existing modal
    const existingModal = document.getElementById('mobile-block-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Ensure proper mobile viewport
    const originalViewport = ensureMobileViewport();

    // Create modal HTML
    const modalHTML = `
        <div id="mobile-block-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 overflow-y-auto">
            <div class="bg-white rounded-2xl max-w-md w-full p-4 sm:p-6 text-center shadow-2xl animate-scale-in my-4 min-h-fit max-h-[95vh] overflow-y-auto">
                <!-- App Icon -->
                <div class="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                    <svg class="w-8 h-8 sm:w-10 sm:h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M6 18h.01M18 18h.01M21 12l-9-9-9 9h3v9h12v-9h3z"/>
                    </svg>
                </div>

                <!-- Title -->
                <h2 class="text-xl sm:text-2xl font-bold text-gray-900 mb-2 sm:mb-3">Install SS League App</h2>
                
                <!-- Message -->
                <p class="text-gray-600 text-sm sm:text-base mb-4">
                    This app is designed for the best mobile experience as a Progressive Web App (PWA). 
                    Please install it on your device.
                </p>

                <!-- Benefits -->
                <div class="bg-blue-50 rounded-xl p-3 mb-4">
                    <h3 class="font-semibold text-blue-900 mb-2 text-sm sm:text-base">Why install the app?</h3>
                    <ul class="text-xs sm:text-sm text-blue-800 space-y-1">
                        <li>✓ Faster loading and better performance</li>
                        <li>✓ Push notifications for auction updates</li>
                        <li>✓ Offline access to your team data</li>
                        <li>✓ Native app-like experience</li>
                        <li>✓ Full-screen immersive interface</li>
                    </ul>
                </div>

                <!-- Installation Instructions -->
                <div class="text-left mb-4 max-h-48 overflow-y-auto border rounded-lg p-3 bg-gray-50">
                    <h3 class="font-semibold text-gray-900 mb-2 text-sm sm:text-base sticky top-0 bg-gray-50 pb-2">How to install:</h3>
                    
                    <!-- Android Instructions -->
                    <div class="mb-3 android-instructions">
                        <h4 class="font-medium text-gray-800 mb-2 flex items-center text-sm">
                            <svg class="w-3 h-3 text-green-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M17.523 15.3414c-.5511 0-1.0993.3885-1.6436.9328l-7.0527-4.1123c.0741-.2354.1259-.4708.1259-.7062s-.0518-.4708-.1259-.7062l7.0527-4.1123c.5443.5443 1.0925.9328 1.6436.9328 1.2765 0 2.3127-1.0362 2.3127-2.3127s-1.0362-2.3127-2.3127-2.3127-2.3127 1.0362-2.3127 2.3127c0 .2354.0518.4708.1259.7062l-7.0527 4.1123c-.5443-.5443-1.0925-.9328-1.6436-.9328-1.2765 0-2.3127 1.0362-2.3127 2.3127s1.0362 2.3127 2.3127 2.3127c.5511 0 1.0993-.3885 1.6436-.9328l7.0527 4.1123c-.0741.2354-.1259.4708-.1259.7062 0 1.2765 1.0362 2.3127 2.3127 2.3127s2.3127-1.0362 2.3127-2.3127-1.0362-2.3127-2.3127-2.3127z"/>
                            </svg>
                            Android (Chrome/Edge)
                        </h4>
                        <ol class="text-xs sm:text-sm text-gray-600 space-y-1 ml-5">
                            <li>1. Tap the menu (⋮) button</li>
                            <li>2. Select "Add to Home screen"</li>
                            <li>3. Tap "Install" or "Add"</li>
                        </ol>
                    </div>

                    <!-- iOS Instructions -->
                    <div class="ios-instructions">
                        <h4 class="font-medium text-gray-800 mb-2 flex items-center text-sm">
                            <svg class="w-3 h-3 text-gray-800 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                            </svg>
                            iPhone/iPad (Safari)
                        </h4>
                        <ol class="text-xs sm:text-sm text-gray-600 space-y-1 ml-5">
                            <li>1. Tap the Share button <svg class="inline w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg></li>
                            <li>2. Scroll and tap "Add to Home Screen"</li>
                            <li>3. Tap "Add" to confirm</li>
                        </ol>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="space-y-2 sm:space-y-3">
                    <button id="install-pwa-btn" class="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-2.5 sm:py-3 px-4 sm:px-6 rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 shadow-lg text-sm sm:text-base">
                        📱 Install App Now
                    </button>
                    ${PWA_ENFORCEMENT_CONFIG.allowBrowserFallback ? `
                    <button id="continue-browser-btn" class="w-full bg-gray-100 text-gray-700 py-2 sm:py-3 px-4 sm:px-6 rounded-xl font-medium hover:bg-gray-200 transition-colors text-sm sm:text-base">
                        Continue in Browser (Limited)
                    </button>
                    ` : ''}
                </div>

                <!-- Warning -->
                <p class="text-xs text-gray-500 mt-3">
                    ⚠️ Browser version has limited functionality and no push notifications
                </p>
            </div>
        </div>

        <style>
            @keyframes scale-in {
                from { 
                    opacity: 0; 
                    transform: scale(0.95); 
                }
                to { 
                    opacity: 1; 
                    transform: scale(1); 
                }
            }
            .animate-scale-in {
                animation: scale-in 0.3s ease-out;
            }
            #mobile-block-modal {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            /* Enhanced mobile viewport handling */
            @media screen and (max-height: 700px) {
                #mobile-block-modal .bg-white {
                    max-height: 90vh !important;
                    padding: 12px !important;
                }
                #mobile-block-modal h2 {
                    font-size: 1.25rem !important;
                    margin-bottom: 8px !important;
                }
                #mobile-block-modal .bg-blue-50 {
                    padding: 8px !important;
                    margin-bottom: 12px !important;
                }
                #mobile-block-modal .max-h-48 {
                    max-height: 120px !important;
                }
            }
            
            @media screen and (max-height: 600px) {
                #mobile-block-modal .bg-white {
                    max-height: 95vh !important;
                    padding: 8px !important;
                }
                #mobile-block-modal .w-16,
                #mobile-block-modal .w-20 {
                    width: 48px !important;
                    height: 48px !important;
                }
                #mobile-block-modal .bg-blue-50 {
                    display: none !important;
                }
            }
            
            /* Landscape mobile phones */
            @media screen and (max-height: 500px) and (orientation: landscape) {
                #mobile-block-modal {
                    align-items: flex-start !important;
                    padding-top: 10px !important;
                }
                #mobile-block-modal .bg-white {
                    margin-top: 0 !important;
                    margin-bottom: 0 !important;
                    max-height: 98vh !important;
                }
            }
            
            /* Custom scrollbar for mobile */
            #mobile-block-modal .overflow-y-auto::-webkit-scrollbar {
                width: 4px;
            }
            #mobile-block-modal .overflow-y-auto::-webkit-scrollbar-track {
                background: rgba(0,0,0,0.1);
                border-radius: 2px;
            }
            #mobile-block-modal .overflow-y-auto::-webkit-scrollbar-thumb {
                background: rgba(0,0,0,0.3);
                border-radius: 2px;
            }
        </style>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Store original viewport for restoration
    const modal = document.getElementById('mobile-block-modal');
    if (modal && originalViewport) {
        modal.setAttribute('data-original-viewport', originalViewport);
    }

    // Add event listeners
    setupModalEventListeners();
    
    // Adjust modal height for current viewport
    setTimeout(() => {
        adjustModalHeight();
    }, 100);
    
    // Handle orientation changes and resize
    const handleResize = () => {
        setTimeout(() => adjustModalHeight(), 300);
    };
    
    window.addEventListener('orientationchange', handleResize);
    window.addEventListener('resize', handleResize);
    
    // Store cleanup function
    modal.cleanup = () => {
        window.removeEventListener('orientationchange', handleResize);
        window.removeEventListener('resize', handleResize);
    };
}

// Setup modal event listeners
function setupModalEventListeners() {
    const installBtn = document.getElementById('install-pwa-btn');
    const continueBtn = document.getElementById('continue-browser-btn');
    const modal = document.getElementById('mobile-block-modal');

    // Install PWA button
    if (installBtn) {
        installBtn.addEventListener('click', () => {
            // Try to trigger PWA install prompt
            if (window.deferredPrompt) {
                window.deferredPrompt.prompt();
                window.deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        hideModal();
                    }
                });
            } else {
                // Show browser-specific instructions
                showInstallInstructions();
            }
        });
    }

    // Continue in browser button
    if (continueBtn && PWA_ENFORCEMENT_CONFIG.allowBrowserFallback) {
        continueBtn.addEventListener('click', () => {
            // Store user preference for this session if configured
            if (PWA_ENFORCEMENT_CONFIG.rememberChoice) {
                sessionStorage.setItem('allowMobileBrowser', 'true');
            }
            hideModal();
        });
    }
}

// Show detailed install instructions
function showInstallInstructions() {
    const userAgent = navigator.userAgent;
    let instructions = '';

    if (/iPhone|iPad|iPod/i.test(userAgent)) {
        instructions = `
            <div class="text-left">
                <h3 class="font-semibold mb-3">Install on iPhone/iPad:</h3>
                <ol class="space-y-2 text-sm">
                    <li>1. Make sure you're using Safari browser</li>
                    <li>2. Tap the Share button at the bottom</li>
                    <li>3. Scroll down and tap "Add to Home Screen"</li>
                    <li>4. Tap "Add" to install</li>
                </ol>
            </div>
        `;
    } else if (/Android/i.test(userAgent)) {
        instructions = `
            <div class="text-left">
                <h3 class="font-semibold mb-3">Install on Android:</h3>
                <ol class="space-y-2 text-sm">
                    <li>1. Open Chrome or Edge browser</li>
                    <li>2. Tap the menu button (⋮)</li>
                    <li>3. Tap "Add to Home screen" or "Install app"</li>
                    <li>4. Tap "Install" to confirm</li>
                </ol>
            </div>
        `;
    }

    // Show instructions in an alert for now (you can make this fancier)
    alert(instructions.replace(/<[^>]*>/g, '').replace(/&[^;]*;/g, ' '));
}

// Hide modal
function hideModal() {
    const modal = document.getElementById('mobile-block-modal');
    if (modal) {
        // Call cleanup function to remove event listeners
        if (typeof modal.cleanup === 'function') {
            modal.cleanup();
        }
        
        modal.style.opacity = '0';
        setTimeout(() => {
            // Restore original viewport if it was stored
            const originalViewport = modal.getAttribute('data-original-viewport');
            if (originalViewport) {
                restoreViewport(originalViewport);
            }
            modal.remove();
        }, 300);
    }
}

// Initialize mobile PWA enforcement
function initMobilePWAEnforcement() {
    // Check if user already allowed browser access this session
    if (PWA_ENFORCEMENT_CONFIG.rememberChoice) {
        const allowBrowser = sessionStorage.getItem('allowMobileBrowser') === 'true';
        if (allowBrowser) return;
    }

    // Check if access should be blocked
    if (shouldBlockMobileAccess()) {
        // Configurable delay to ensure page is loaded
        setTimeout(() => {
            showMobileBlockModal();
        }, PWA_ENFORCEMENT_CONFIG.modalDelay);
    }
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMobilePWAEnforcement);
} else {
    initMobilePWAEnforcement();
}

// Export functions for external use
window.MobilePWAEnforcement = {
    showModal: showMobileBlockModal,
    hideModal: hideModal,
    shouldBlock: shouldBlockMobileAccess,
    isMobile: isMobileDevice,
    isPWA: isStandalonePWA
};