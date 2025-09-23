/**
 * PWA Safe Area Utilities
 * Helper functions for debugging and handling safe areas in PWA environments
 */

(function() {
    'use strict';

    // Safe area utility object
    window.SafeAreaUtils = {
        
        /**
         * Get current safe area insets
         * @returns {Object} Object with top, right, bottom, left inset values
         */
        getSafeAreaInsets: function() {
            const style = getComputedStyle(document.documentElement);
            
            return {
                top: style.getPropertyValue('--safe-area-inset-top') || '0px',
                right: style.getPropertyValue('--safe-area-inset-right') || '0px',
                bottom: style.getPropertyValue('--safe-area-inset-bottom') || '0px',
                left: style.getPropertyValue('--safe-area-inset-left') || '0px'
            };
        },
        
        /**
         * Check if device supports safe areas
         * @returns {boolean} True if safe areas are supported
         */
        supportsSafeAreas: function() {
            return CSS.supports('padding: max(0px)') && CSS.supports('padding: env(safe-area-inset-top)');
        },
        
        /**
         * Detect if app is running in standalone mode (PWA)
         * @returns {boolean} True if running as PWA
         */
        isStandalone: function() {
            return window.matchMedia && window.matchMedia('(display-mode: standalone)').matches ||
                   window.navigator.standalone === true ||
                   document.referrer.includes('android-app://');
        },
        
        /**
         * Detect if device likely has a notch or dynamic island
         * @returns {boolean} True if device likely has notch
         */
        hasNotch: function() {
            const insets = this.getSafeAreaInsets();
            return parseInt(insets.top) > 20; // More than 20px top inset likely indicates notch
        },
        
        /**
         * Add safe area CSS classes to elements
         * @param {Element|string} element - Element or selector to add classes to
         * @param {Array} sides - Array of sides to add safe area padding ('top', 'right', 'bottom', 'left')
         */
        addSafeAreaClasses: function(element, sides = ['top', 'right', 'bottom', 'left']) {
            const el = typeof element === 'string' ? document.querySelector(element) : element;
            if (!el) return;
            
            sides.forEach(side => {
                el.classList.add(`p${side[0]}-safe`);
            });
        },
        
        /**
         * Debug function to show safe area information
         * Only use during development
         */
        debug: function() {
            if (!this.supportsSafeAreas()) {
                console.log('❌ Safe areas not supported on this device/browser');
                return;
            }
            
            const insets = this.getSafeAreaInsets();
            const isStandalone = this.isStandalone();
            const hasNotch = this.hasNotch();
            
            console.group('🛡️ PWA Safe Area Debug Info');
            console.log('📱 Standalone mode:', isStandalone ? '✅ Yes' : '❌ No');
            console.log('📐 Has notch/dynamic island:', hasNotch ? '✅ Yes' : '❌ No');
            console.log('📏 Safe area insets:', insets);
            console.log('🖥️ Viewport dimensions:', {
                width: window.innerWidth,
                height: window.innerHeight
            });
            console.log('📱 User agent:', navigator.userAgent);
            console.groupEnd();
            
            // Add visual debugging if in development
            if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
                this.addVisualDebugger();
            }
        },
        
        /**
         * Add visual safe area debugger (development only)
         */
        addVisualDebugger: function() {
            // Remove existing debugger
            const existing = document.querySelector('.safe-area-debugger');
            if (existing) existing.remove();
            
            const debugger = document.createElement('div');
            debugger.className = 'safe-area-debugger';
            debugger.innerHTML = `
                <div style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: var(--safe-area-inset-top, 0px);
                    background: rgba(255, 0, 0, 0.3);
                    z-index: 9999;
                    pointer-events: none;
                    border-bottom: 1px dashed red;
                "></div>
                <div style="
                    position: fixed;
                    top: var(--safe-area-inset-top, 0px);
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-family: monospace;
                    z-index: 10000;
                    pointer-events: none;
                ">Top: ${this.getSafeAreaInsets().top}</div>
                <div style="
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: var(--safe-area-inset-bottom, 0px);
                    background: rgba(255, 0, 0, 0.3);
                    z-index: 9999;
                    pointer-events: none;
                    border-top: 1px dashed red;
                "></div>
                <div style="
                    position: fixed;
                    bottom: var(--safe-area-inset-bottom, 0px);
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-family: monospace;
                    z-index: 10000;
                    pointer-events: none;
                ">Bottom: ${this.getSafeAreaInsets().bottom}</div>
            `;
            
            document.body.appendChild(debugger);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (document.querySelector('.safe-area-debugger')) {
                    document.querySelector('.safe-area-debugger').remove();
                }
            }, 5000);
        },
        
        /**
         * Apply safe area adjustments to header
         * @param {Element|string} headerElement - Header element or selector
         */
        applyHeaderSafeArea: function(headerElement) {
            const header = typeof headerElement === 'string' ? 
                          document.querySelector(headerElement) : headerElement;
            
            if (!header) return;
            
            // Add safe area classes
            header.classList.add('mobile-header-safe');
            
            // Ensure sticky positioning works with safe areas
            if (header.classList.contains('sticky') || 
                getComputedStyle(header).position === 'sticky') {
                header.style.top = 'var(--safe-area-inset-top, 0px)';
            }
        },
        
        /**
         * Initialize safe area handling
         */
        init: function() {
            // Only run on mobile devices
            if (window.innerWidth > 768) return;
            
            document.addEventListener('DOMContentLoaded', () => {
                // Auto-apply to headers with safe area class
                const safeHeaders = document.querySelectorAll('.mobile-header-safe');
                safeHeaders.forEach(header => this.applyHeaderSafeArea(header));
                
                // Add PWA mode class to body if in standalone
                if (this.isStandalone()) {
                    document.body.classList.add('pwa-mode');
                }
                
                // Update CSS custom properties
                this.updateCSSProperties();
            });
            
            // Update on orientation change
            window.addEventListener('orientationchange', () => {
                setTimeout(() => this.updateCSSProperties(), 100);
            });
            
            // Update on resize
            let resizeTimeout;
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => this.updateCSSProperties(), 150);
            });
        },
        
        /**
         * Update CSS custom properties with current safe area values
         */
        updateCSSProperties: function() {
            const root = document.documentElement;
            const insets = this.getSafeAreaInsets();
            
            // Update custom properties for easier JavaScript access
            root.style.setProperty('--js-safe-area-inset-top', insets.top);
            root.style.setProperty('--js-safe-area-inset-right', insets.right);
            root.style.setProperty('--js-safe-area-inset-bottom', insets.bottom);
            root.style.setProperty('--js-safe-area-inset-left', insets.left);
        }
    };
    
    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => SafeAreaUtils.init());
    } else {
        SafeAreaUtils.init();
    }
    
    // Debug in development
    if (window.location.hostname === 'localhost' || 
        window.location.hostname.includes('127.0.0.1') ||
        window.location.search.includes('debug=safe-areas')) {
        
        // Add debug command to console
        console.log('🛡️ Safe Area Utils loaded. Type SafeAreaUtils.debug() to see debug info.');
        
        // Add keyboard shortcut for debugging (Ctrl/Cmd + Shift + S)
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                SafeAreaUtils.debug();
            }
        });
    }
    
})();