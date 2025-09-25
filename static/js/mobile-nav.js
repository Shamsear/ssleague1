// Mobile Navigation JavaScript
(function() {
    'use strict';
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        // Check if mobile nav exists on page
        const mobileNav = document.getElementById('mobileNav');
        if (!mobileNav) return;
        
        // Elements
        const menuToggleBtn = document.getElementById('menuToggleBtn');
        const closeMenuBtn = document.getElementById('closeMenuBtn');
        const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
        const mobileNavBar = document.getElementById('mobileNavBar');
        const expandableButtons = document.querySelectorAll('.menu-expandable');
        const body = document.body;
        
        // Add class to body when mobile nav is present (only on mobile)
        if (window.innerWidth <= 768) {
            body.classList.add('has-mobile-nav');
        }
        
        // Handle resize events
        window.addEventListener('resize', function() {
            if (window.innerWidth <= 768) {
                body.classList.add('has-mobile-nav');
            } else {
                body.classList.remove('has-mobile-nav');
            }
        });
        
        // Toggle menu function with animations
        function toggleMenu(open) {
            if (open) {
                // Add active class to trigger animations
                mobileMenuOverlay.classList.add('active');
                body.classList.add('menu-open');
                menuToggleBtn.classList.add('active');
                
                // Add menu-active class to navbar for centered button styling
                if (mobileNavBar) {
                    mobileNavBar.classList.add('menu-active');
                }
                
                // Show close button, hide menu button
                if (closeMenuBtn) {
                    closeMenuBtn.style.display = 'flex';
                }
                if (menuToggleBtn) {
                    menuToggleBtn.style.display = 'none';
                }
                
                // Prevent background scrolling
                const scrollY = window.scrollY;
                body.style.position = 'fixed';
                body.style.top = `-${scrollY}px`;
                body.style.width = '100%';
                
                // Request animation frame for smooth opening
                requestAnimationFrame(() => {
                    // Reset animations for instant appearance
                    const menuItems = mobileMenuOverlay.querySelectorAll('.menu-item, .welcome-section');
                    menuItems.forEach((item, index) => {
                        item.style.animation = 'none';
                        item.offsetHeight; // Trigger reflow
                        item.style.animation = '';
                    });
                });
                
            } else {
                // Start close animation
                mobileMenuOverlay.classList.add('closing');
                menuToggleBtn.classList.remove('active');
                
                // Remove menu-active class from navbar
                if (mobileNavBar) {
                    mobileNavBar.classList.remove('menu-active');
                }
                
                // Show menu button, hide close button
                if (menuToggleBtn) {
                    menuToggleBtn.style.display = 'flex';
                }
                if (closeMenuBtn) {
                    closeMenuBtn.style.display = 'none';
                }
                
                // Wait for animation to complete - FASTER
                setTimeout(() => {
                    mobileMenuOverlay.classList.remove('active', 'closing');
                    body.classList.remove('menu-open');
                    
                    // Restore scrolling
                    const scrollY = body.style.top;
                    body.style.position = '';
                    body.style.top = '';
                    body.style.width = '';
                    window.scrollTo(0, parseInt(scrollY || '0') * -1);
                }, 200); // Faster animation completion
            }
        }
        
        // Open menu
        if (menuToggleBtn) {
            menuToggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                toggleMenu(true);
            });
        }
        
        // Close menu
        if (closeMenuBtn) {
            closeMenuBtn.addEventListener('click', function(e) {
                e.preventDefault();
                toggleMenu(false);
            });
        }
        
        // Close menu when clicking outside (on the dark overlay)
        if (mobileMenuOverlay) {
            mobileMenuOverlay.addEventListener('click', function(e) {
                // Only close if clicking the overlay itself, not the menu container
                if (e.target === mobileMenuOverlay || e.target.classList.contains('menu-overlay-bg')) {
                    toggleMenu(false);
                }
            });
            
            // Prevent menu from closing when scrolling or touching menu content
            const menuContainer = mobileMenuOverlay.querySelector('.menu-container');
            if (menuContainer) {
                menuContainer.addEventListener('click', function(e) {
                    // Prevent clicks inside menu container from bubbling up to overlay
                    e.stopPropagation();
                });
                
                menuContainer.addEventListener('touchstart', function(e) {
                    // Prevent touch events inside menu container from bubbling up
                    e.stopPropagation();
                });
                
                menuContainer.addEventListener('touchmove', function(e) {
                    // Allow scrolling within menu container
                    e.stopPropagation();
                });
                
                menuContainer.addEventListener('touchend', function(e) {
                    // Prevent touch end events from bubbling up to overlay
                    e.stopPropagation();
                });
            }
        }
        
        // Handle expandable menu items
        expandableButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const menuItem = button.closest('.menu-item');
                const menuType = button.getAttribute('data-menu');
                const submenu = document.getElementById(menuType + '-submenu');
                
                if (!menuItem || !submenu) return;
                
                // Toggle current item
                const isExpanded = menuItem.classList.contains('expanded');
                
                // Close all other expanded items
                document.querySelectorAll('.menu-item.expanded').forEach(function(item) {
                    if (item !== menuItem) {
                        item.classList.remove('expanded');
                        const otherSubmenu = item.querySelector('.submenu');
                        if (otherSubmenu) {
                            otherSubmenu.classList.remove('active');
                        }
                    }
                });
                
                // Toggle current item
                if (isExpanded) {
                    menuItem.classList.remove('expanded');
                    submenu.classList.remove('active');
                } else {
                    menuItem.classList.add('expanded');
                    submenu.classList.add('active');
                }
            });
        });
        
        // Handle escape key to close menu
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && mobileMenuOverlay && mobileMenuOverlay.classList.contains('active')) {
                toggleMenu(false);
            }
        });
        
        // Handle swipe to close (optional - for touch devices)
        let touchStartX = 0;
        let touchEndX = 0;
        let touchStartY = 0;
        let touchEndY = 0;
        
        // Only apply swipe detection to the overlay area, not the menu content
        if (mobileMenuOverlay) {
            mobileMenuOverlay.addEventListener('touchstart', function(e) {
                // Only handle touches on the overlay itself, not menu content
                if (e.target === mobileMenuOverlay || e.target.classList.contains('menu-overlay-bg')) {
                    touchStartX = e.changedTouches[0].screenX;
                    touchStartY = e.changedTouches[0].screenY;
                }
            }, { passive: true });
            
            mobileMenuOverlay.addEventListener('touchend', function(e) {
                // Only handle touches on the overlay itself, not menu content
                if (e.target === mobileMenuOverlay || e.target.classList.contains('menu-overlay-bg')) {
                    touchEndX = e.changedTouches[0].screenX;
                    touchEndY = e.changedTouches[0].screenY;
                    handleSwipe();
                }
            }, { passive: true });
        }
        
        function handleSwipe() {
            const deltaX = touchEndX - touchStartX;
            const deltaY = Math.abs(touchEndY - touchStartY);
            
            // Only trigger swipe if:
            // 1. Horizontal swipe is significant (> 50px)
            // 2. Vertical movement is minimal (< 30px) - this prevents interference with scrolling
            // 3. Swipe is to the right (closing gesture)
            if (deltaX > 50 && deltaY < 30) {
                toggleMenu(false);
            }
        }
        
        // Handle search functionality
        const searchInput = document.querySelector('.search-input');
        const searchBtn = document.querySelector('.search-btn');
        
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const searchTerm = searchInput.value.trim();
                if (searchTerm) {
                    // Implement search functionality
                    // For now, just close the menu and redirect to search
                    toggleMenu(false);
                    // You can add actual search logic here
                    console.log('Searching for:', searchTerm);
                }
            });
            
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchBtn.click();
                }
            });
        }
        
        // Prevent menu from opening on desktop resize
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                if (window.innerWidth > 768 && mobileMenuOverlay && mobileMenuOverlay.classList.contains('active')) {
                    toggleMenu(false);
                }
            }, 250);
        });
        
        // Add smooth scroll behavior for menu links
        const menuLinks = document.querySelectorAll('.menu-link:not(.menu-expandable), .submenu-link');
        menuLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                // Close menu after clicking a link
                setTimeout(function() {
                    toggleMenu(false);
                }, 100);
            });
        });
    });
})();