// Mobile Navigation JavaScript - CoLabs Style
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
                // Close menu if open on desktop resize
                if (mobileMenuOverlay && mobileMenuOverlay.classList.contains('active')) {
                    toggleMenu(false);
                }
            }
        });
        
        // Toggle menu function with CoLabs-style animations
        function toggleMenu(open) {
            if (open) {
                // Transform the header by adding active class
                mobileNavBar.classList.add('menu-active');
                
                // Show the menu overlay
                mobileMenuOverlay.classList.add('active');
                body.classList.add('menu-open');
                
                // Toggle button visibility
                menuToggleBtn.style.display = 'none';
                closeMenuBtn.style.display = 'flex';
                
                // Prevent background scrolling
                const scrollY = window.scrollY;
                body.style.position = 'fixed';
                body.style.top = `-${scrollY}px`;
                body.style.width = '100%';
                
            } else {
                // Start close animation
                mobileMenuOverlay.classList.remove('active');
                mobileNavBar.classList.remove('menu-active');
                
                // Toggle button visibility
                closeMenuBtn.style.display = 'none';
                menuToggleBtn.style.display = 'flex';
                
                // Restore scrolling after transition
                setTimeout(() => {
                    body.classList.remove('menu-open');
                    
                    const scrollY = body.style.top;
                    body.style.position = '';
                    body.style.top = '';
                    body.style.width = '';
                    window.scrollTo(0, parseInt(scrollY || '0') * -1);
                }, 300);
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
        
        // Close menu when clicking outside (on the overlay background)
        if (mobileMenuOverlay) {
            mobileMenuOverlay.addEventListener('click', function(e) {
                // Only close if clicking the overlay itself, not the menu content
                if (e.target === mobileMenuOverlay) {
                    toggleMenu(false);
                }
            });
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
        
        // Handle search functionality
        const searchInput = document.querySelector('.search-input');
        const searchBtn = document.querySelector('.search-btn');
        
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const searchTerm = searchInput.value.trim();
                if (searchTerm) {
                    // Close the menu and perform search
                    toggleMenu(false);
                    console.log('Searching for:', searchTerm);
                    // Add your search logic here
                }
            });
            
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchBtn.click();
                }
            });
        }
        
        // Handle menu links - close menu after clicking
        const menuLinks = document.querySelectorAll('.menu-link:not(.menu-expandable), .submenu-link');
        menuLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                // Don't prevent default for actual navigation links
                // Close menu after a short delay to allow the click to register
                setTimeout(function() {
                    toggleMenu(false);
                }, 100);
            });
        });
        
        // Handle swipe to close (optional - for touch devices)
        let touchStartY = 0;
        let touchEndY = 0;
        
        if (mobileMenuOverlay) {
            mobileMenuOverlay.addEventListener('touchstart', function(e) {
                touchStartY = e.changedTouches[0].screenY;
            });
            
            mobileMenuOverlay.addEventListener('touchend', function(e) {
                touchEndY = e.changedTouches[0].screenY;
                handleSwipe();
            });
        }
        
        function handleSwipe() {
            // Swipe up to close
            if (touchStartY - touchEndY > 50) {
                toggleMenu(false);
            }
        }
    });
})();