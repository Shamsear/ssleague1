/**
 * Enhanced Team Logo Interactivity for Mobile Navigation
 * Adds advanced hover effects, click interactions, and accessibility features
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        LONG_PRESS_DURATION: 800,
        RIPPLE_DURATION: 600,
        TOOLTIP_DELAY: 1000,
        ANIMATION_DURATION: 300
    };

    // State
    let longPressTimer = null;
    let isMenuActive = false;

    /**
     * Initialize team logo enhancements
     */
    function initTeamLogoEnhancements() {
        const teamAvatar = document.querySelector('.team-avatar');
        const mobileNavBar = document.querySelector('.mobile-nav-bar');
        
        if (!teamAvatar) return;

        // Add enhanced interaction listeners
        addTeamAvatarListeners(teamAvatar);
        
        // Monitor menu state changes
        monitorMenuState(mobileNavBar);
        
        // Add keyboard navigation
        addKeyboardNavigation(teamAvatar);
        
        // Add ripple effect capability
        addRippleEffect(teamAvatar);
        
        // Add performance optimizations
        optimizePerformance(teamAvatar);

        console.log('✅ Team logo enhancements initialized');
    }

    /**
     * Add event listeners to team avatar
     */
    function addTeamAvatarListeners(teamAvatar) {
        // Touch and click events
        teamAvatar.addEventListener('touchstart', handleTouchStart, { passive: true });
        teamAvatar.addEventListener('touchend', handleTouchEnd, { passive: true });
        teamAvatar.addEventListener('touchcancel', handleTouchCancel, { passive: true });
        teamAvatar.addEventListener('click', handleAvatarClick);
        
        // Mouse events for desktop testing
        teamAvatar.addEventListener('mouseenter', handleMouseEnter);
        teamAvatar.addEventListener('mouseleave', handleMouseLeave);
        teamAvatar.addEventListener('mousedown', handleMouseDown);
        teamAvatar.addEventListener('mouseup', handleMouseUp);
        
        // Focus events for accessibility
        teamAvatar.addEventListener('focus', handleFocus);
        teamAvatar.addEventListener('blur', handleBlur);
    }

    /**
     * Handle touch start (for long press detection)
     */
    function handleTouchStart(event) {
        const teamAvatar = event.currentTarget;
        
        // Add active state
        teamAvatar.classList.add('touch-active');
        
        // Start long press timer
        longPressTimer = setTimeout(() => {
            handleLongPress(teamAvatar);
        }, CONFIG.LONG_PRESS_DURATION);
        
        // Add ripple effect
        createRipple(event, teamAvatar);
    }

    /**
     * Handle touch end
     */
    function handleTouchEnd(event) {
        const teamAvatar = event.currentTarget;
        
        // Clear long press timer
        if (longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
        
        // Remove active state
        setTimeout(() => {
            teamAvatar.classList.remove('touch-active');
        }, 150);
    }

    /**
     * Handle touch cancel
     */
    function handleTouchCancel(event) {
        handleTouchEnd(event);
    }

    /**
     * Handle avatar click
     */
    function handleAvatarClick(event) {
        const teamAvatar = event.currentTarget;
        
        // Prevent default if needed
        event.preventDefault();
        
        // Add click animation
        teamAvatar.classList.add('clicked');
        setTimeout(() => {
            teamAvatar.classList.remove('clicked');
        }, CONFIG.ANIMATION_DURATION);
        
        // Show team info or navigate to team page
        showTeamInfo(teamAvatar);
    }

    /**
     * Handle long press on team avatar
     */
    function handleLongPress(teamAvatar) {
        // Add long press visual feedback
        teamAvatar.classList.add('long-pressed');
        
        // Vibrate if supported
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Show extended team options
        showTeamOptions(teamAvatar);
        
        // Remove long press state after a moment
        setTimeout(() => {
            teamAvatar.classList.remove('long-pressed');
        }, 1000);
    }

    /**
     * Mouse enter handler
     */
    function handleMouseEnter(event) {
        const teamAvatar = event.currentTarget;
        teamAvatar.classList.add('mouse-hover');
        
        // Show tooltip after delay
        setTimeout(() => {
            if (teamAvatar.classList.contains('mouse-hover')) {
                showTooltip(teamAvatar);
            }
        }, CONFIG.TOOLTIP_DELAY);
    }

    /**
     * Mouse leave handler
     */
    function handleMouseLeave(event) {
        const teamAvatar = event.currentTarget;
        teamAvatar.classList.remove('mouse-hover');
        hideTooltip();
    }

    /**
     * Mouse down handler
     */
    function handleMouseDown(event) {
        const teamAvatar = event.currentTarget;
        createRipple(event, teamAvatar);
    }

    /**
     * Mouse up handler
     */
    function handleMouseUp(event) {
        // Handle mouse up logic if needed
    }

    /**
     * Focus handler for accessibility
     */
    function handleFocus(event) {
        const teamAvatar = event.currentTarget;
        teamAvatar.classList.add('keyboard-focused');
    }

    /**
     * Blur handler for accessibility
     */
    function handleBlur(event) {
        const teamAvatar = event.currentTarget;
        teamAvatar.classList.remove('keyboard-focused');
        hideTooltip();
    }

    /**
     * Add keyboard navigation support
     */
    function addKeyboardNavigation(teamAvatar) {
        teamAvatar.addEventListener('keydown', (event) => {
            // Enter or Space key
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                teamAvatar.click();
            }
        });
    }

    /**
     * Create ripple effect
     */
    function createRipple(event, element) {
        // Remove existing ripples
        const existingRipples = element.querySelectorAll('.ripple');
        existingRipples.forEach(ripple => ripple.remove());
        
        // Create ripple element
        const ripple = document.createElement('div');
        ripple.classList.add('ripple');
        
        // Calculate ripple position and size
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = (event.clientX || event.touches?.[0]?.clientX || rect.left + rect.width / 2) - rect.left - size / 2;
        const y = (event.clientY || event.touches?.[0]?.clientY || rect.top + rect.height / 2) - rect.top - size / 2;
        
        // Set ripple styles
        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.4);
            transform: scale(0);
            animation: rippleEffect ${CONFIG.RIPPLE_DURATION}ms ease-out;
            left: ${x}px;
            top: ${y}px;
            width: ${size}px;
            height: ${size}px;
            pointer-events: none;
            z-index: 1;
        `;
        
        // Add ripple to element
        element.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.remove();
            }
        }, CONFIG.RIPPLE_DURATION);
    }

    /**
     * Add ripple effect styles
     */
    function addRippleEffect(teamAvatar) {
        // Add ripple keyframes if not already added
        if (!document.getElementById('ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'ripple-styles';
            style.textContent = `
                @keyframes rippleEffect {
                    to {
                        transform: scale(2);
                        opacity: 0;
                    }
                }
                
                .team-avatar {
                    overflow: hidden;
                }
                
                .team-avatar.touch-active {
                    transform: translateY(-1px) scale(1.02);
                }
                
                .team-avatar.clicked {
                    animation: avatarClick 0.3s ease;
                }
                
                .team-avatar.long-pressed {
                    animation: avatarLongPress 1s ease;
                }
                
                .team-avatar.keyboard-focused {
                    outline: 3px solid rgba(0, 102, 255, 0.6);
                    outline-offset: 4px;
                }
                
                @keyframes avatarClick {
                    0% { transform: scale(1); }
                    50% { transform: scale(0.95); }
                    100% { transform: scale(1); }
                }
                
                @keyframes avatarLongPress {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Monitor menu state changes
     */
    function monitorMenuState(mobileNavBar) {
        if (!mobileNavBar) return;
        
        // Use MutationObserver to watch for class changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const hasMenuActive = mobileNavBar.classList.contains('menu-active');
                    if (hasMenuActive !== isMenuActive) {
                        isMenuActive = hasMenuActive;
                        handleMenuStateChange(hasMenuActive);
                    }
                }
            });
        });
        
        observer.observe(mobileNavBar, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    /**
     * Handle menu state change
     */
    function handleMenuStateChange(isActive) {
        const teamAvatar = document.querySelector('.team-avatar');
        if (!teamAvatar) return;
        
        if (isActive) {
            teamAvatar.classList.add('menu-is-active');
            // Add enhanced styling when menu is open
            setTimeout(() => {
                teamAvatar.style.filter = 'drop-shadow(0 8px 16px rgba(0, 102, 255, 0.4))';
            }, 100);
        } else {
            teamAvatar.classList.remove('menu-is-active');
            // Remove enhanced styling when menu closes
            teamAvatar.style.filter = '';
        }
    }

    /**
     * Show team info (placeholder - customize based on your needs)
     */
    function showTeamInfo(teamAvatar) {
        const teamName = teamAvatar.getAttribute('aria-label');
        
        // For now, just log - you can integrate with your existing modal system
        console.log(`🏆 Clicked on team: ${teamName}`);
        
        // You could navigate to team dashboard, show a modal, etc.
        // Example: window.location.href = '/team/dashboard';
    }

    /**
     * Show team options on long press (placeholder)
     */
    function showTeamOptions(teamAvatar) {
        console.log('📱 Long press detected - showing team options');
        
        // You could show a context menu, quick actions, etc.
        // Example: showTeamQuickActions();
    }

    /**
     * Show tooltip
     */
    function showTooltip(teamAvatar) {
        // Remove existing tooltips
        hideTooltip();
        
        const tooltip = document.createElement('div');
        tooltip.className = 'team-avatar-tooltip';
        tooltip.textContent = teamAvatar.getAttribute('title') || teamAvatar.getAttribute('aria-label');
        
        // Position tooltip
        document.body.appendChild(tooltip);
        
        const rect = teamAvatar.getBoundingClientRect();
        tooltip.style.cssText = `
            position: fixed;
            bottom: ${window.innerHeight - rect.top + 10}px;
            left: ${rect.left + rect.width / 2}px;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        `;
        
        // Fade in
        requestAnimationFrame(() => {
            tooltip.style.opacity = '1';
        });
    }

    /**
     * Hide tooltip
     */
    function hideTooltip() {
        const tooltips = document.querySelectorAll('.team-avatar-tooltip');
        tooltips.forEach(tooltip => tooltip.remove());
    }

    /**
     * Optimize performance
     */
    function optimizePerformance(teamAvatar) {
        // Add will-change property for better performance
        teamAvatar.style.willChange = 'transform, box-shadow, filter';
        
        // Use passive listeners where possible
        const passiveOptions = { passive: true };
        
        // Optimize touch events for mobile
        if ('ontouchstart' in window) {
            teamAvatar.addEventListener('touchmove', (e) => {
                // Prevent scroll during avatar interaction
                if (teamAvatar.classList.contains('touch-active')) {
                    e.preventDefault();
                }
            }, passiveOptions);
        }
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTeamLogoEnhancements);
    } else {
        initTeamLogoEnhancements();
    }

    // Also initialize if the content is dynamically loaded
    if (window.MutationObserver) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && (
                        node.classList?.contains('team-avatar') ||
                        node.querySelector?.('.team-avatar')
                    )) {
                        initTeamLogoEnhancements();
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

})();