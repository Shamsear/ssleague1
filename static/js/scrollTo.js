/**
 * ScrollTo utility
 * Provides smooth scrolling to elements with support for headers and offsets
 */

// Global scroll helper function that can be used throughout the application
window.scrollToElement = function(selector, offset = 0, behavior = 'smooth') {
  const element = document.querySelector(selector);
  if (!element) return;
  
  const elementPosition = element.getBoundingClientRect().top;
  const offsetPosition = elementPosition + window.pageYOffset - offset;
  
  window.scrollTo({
    top: offsetPosition,
    behavior: behavior
  });
};

// Handle scroll-to data attributes
document.addEventListener('DOMContentLoaded', () => {
  // Find all elements with data-scroll-to attribute
  document.querySelectorAll('[data-scroll-to]').forEach(element => {
    element.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetSelector = this.getAttribute('data-scroll-to');
      const offset = parseInt(this.getAttribute('data-scroll-offset') || '0', 10);
      
      // Use the scroll helper
      window.scrollToElement(targetSelector, offset);
      
      // Update URL if there's an ID
      if (targetSelector.startsWith('#')) {
        history.pushState(null, null, targetSelector);
      }
    });
  });
  
  // Handle URL hash on page load
  if (window.location.hash) {
    // Wait a bit to ensure page is fully loaded
    setTimeout(() => {
      window.scrollToElement(window.location.hash, 100);
    }, 300);
  }
  
  // Add smooth scrolling to back-to-top buttons
  document.querySelectorAll('.back-to-top, [data-action="back-to-top"]').forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  });
}); 