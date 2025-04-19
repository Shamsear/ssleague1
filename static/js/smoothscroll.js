/**
 * Smooth Scroll polyfill
 * This helps provide smooth scrolling for older browsers
 */

// Polyfill for Element.scrollIntoView() method with smooth behavior
if (!('scrollBehavior' in document.documentElement.style)) {
  const __scrollTo = function(element, top) {
    // Get the document scrolling element
    const scrollingElement = document.scrollingElement || document.documentElement;
    
    // Get the current scroll position
    const startY = scrollingElement.scrollTop;
    const targetY = top;
    const distance = targetY - startY;
    const duration = 500; // Duration in ms
    let startTime = null;
    
    // Animate the scrolling
    const step = function(currentTime) {
      if (!startTime) {
        startTime = currentTime;
      }
      
      // Calculate how far to scroll
      const progress = Math.min(1, (currentTime - startTime) / duration);
      const easeInOutCubic = progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;
        
      // Scroll to the calculated position
      scrollingElement.scrollTop = startY + distance * easeInOutCubic;
      
      // Continue animation if we're not done
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    
    // Start the animation
    window.requestAnimationFrame(step);
  };
  
  // Override the original scrollIntoView method
  Element.prototype._scrollIntoView = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(options) {
    if (!options || typeof options !== 'object' || options.behavior !== 'smooth') {
      return this._scrollIntoView.apply(this, arguments);
    }
    
    // Calculate the element's position relative to the document
    const rect = this.getBoundingClientRect();
    const offsetTop = rect.top + window.pageYOffset;
    
    // Calculate final scroll position based on 'block' option
    const top = options.block === 'center'
      ? offsetTop - (window.innerHeight / 2) + (rect.height / 2)
      : options.block === 'end'
        ? offsetTop + rect.height - window.innerHeight
        : offsetTop;
        
    __scrollTo(this, top);
  };
  
  // Add smooth scrolling for internal links
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
          e.preventDefault();
          targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  });
} 