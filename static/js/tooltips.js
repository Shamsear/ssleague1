// Tooltip functionality with accessibility support
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initTooltips();
});

function initTooltips() {
    // Select all elements with data-tooltip attribute
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        // Add appropriate ARIA attributes
        element.setAttribute('aria-describedby', generateTooltipId());
        
        // Add additional attributes for a11y
        if (!element.getAttribute('tabindex')) {
            element.setAttribute('tabindex', '0');
        }
        
        // Create tooltip container
        createTooltipContainer(element);
        
        // Add event listeners
        setupTooltipEvents(element);
    });
}

function generateTooltipId() {
    return 'tooltip-' + Math.random().toString(36).substr(2, 9);
}

function createTooltipContainer(element) {
    // Get tooltip content
    const tooltipContent = element.getAttribute('data-tooltip');
    const position = element.getAttribute('data-tooltip-position') || 'top';
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    const tooltipId = element.getAttribute('aria-describedby');
    
    tooltip.id = tooltipId;
    tooltip.className = 'tooltip-container absolute z-50 bg-gray-900 text-white text-sm rounded-md px-3 py-2 max-w-xs opacity-0 invisible transition-opacity duration-150';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.textContent = tooltipContent;
    
    // Add position-specific classes
    switch (position) {
        case 'bottom':
            tooltip.classList.add('top-full', 'left-1/2', 'transform', '-translate-x-1/2', 'mt-1');
            break;
        case 'left':
            tooltip.classList.add('right-full', 'top-1/2', 'transform', '-translate-y-1/2', 'mr-1');
            break;
        case 'right':
            tooltip.classList.add('left-full', 'top-1/2', 'transform', '-translate-y-1/2', 'ml-1');
            break;
        case 'top':
        default:
            tooltip.classList.add('bottom-full', 'left-1/2', 'transform', '-translate-x-1/2', 'mb-1');
            break;
    }
    
    // Add tooltip arrow
    const arrow = document.createElement('div');
    arrow.className = 'tooltip-arrow absolute w-0 h-0 border-4 border-transparent';
    
    switch (position) {
        case 'bottom':
            arrow.classList.add('bottom-full', 'left-1/2', 'transform', '-translate-x-1/2', 'border-b-gray-900');
            break;
        case 'left':
            arrow.classList.add('left-full', 'top-1/2', 'transform', '-translate-y-1/2', 'border-l-gray-900');
            break;
        case 'right':
            arrow.classList.add('right-full', 'top-1/2', 'transform', '-translate-y-1/2', 'border-r-gray-900');
            break;
        case 'top':
        default:
            arrow.classList.add('top-full', 'left-1/2', 'transform', '-translate-x-1/2', 'border-t-gray-900');
            break;
    }
    
    tooltip.appendChild(arrow);
    
    // Create a relative container if needed
    if (getComputedStyle(element).position === 'static') {
        element.style.position = 'relative';
    }
    
    // Append tooltip to the element
    element.appendChild(tooltip);
}

function setupTooltipEvents(element) {
    const tooltipId = element.getAttribute('aria-describedby');
    const tooltip = document.getElementById(tooltipId);
    
    // Show tooltip on hover
    element.addEventListener('mouseenter', () => {
        showTooltip(tooltip);
    });
    
    // Hide tooltip when mouse leaves
    element.addEventListener('mouseleave', () => {
        hideTooltip(tooltip);
    });
    
    // Show tooltip on focus (for keyboard users)
    element.addEventListener('focus', () => {
        showTooltip(tooltip);
    });
    
    // Hide tooltip on blur
    element.addEventListener('blur', () => {
        hideTooltip(tooltip);
    });
    
    // Toggle tooltip on Escape key
    element.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && tooltip.classList.contains('opacity-100')) {
            hideTooltip(tooltip);
            element.blur();
        }
    });
}

function showTooltip(tooltip) {
    // Make tooltip visible
    tooltip.classList.remove('opacity-0', 'invisible');
    tooltip.classList.add('opacity-100');
    
    // Ensure tooltip stays within viewport
    adjustTooltipPosition(tooltip);
}

function hideTooltip(tooltip) {
    tooltip.classList.remove('opacity-100');
    tooltip.classList.add('opacity-0', 'invisible');
}

function adjustTooltipPosition(tooltip) {
    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Get tooltip dimensions and position
    const tooltipRect = tooltip.getBoundingClientRect();
    
    // Check if tooltip is outside viewport
    if (tooltipRect.left < 0) {
        tooltip.style.marginLeft = -tooltipRect.left + 'px';
    } else if (tooltipRect.right > viewportWidth) {
        tooltip.style.marginLeft = (viewportWidth - tooltipRect.right) + 'px';
    }
    
    if (tooltipRect.top < 0) {
        tooltip.style.marginTop = -tooltipRect.top + 'px';
    } else if (tooltipRect.bottom > viewportHeight) {
        tooltip.style.marginTop = (viewportHeight - tooltipRect.bottom) + 'px';
    }
}

// Create tooltips dynamically for elements added after page load
function createTooltip(element, content, position = 'top') {
    element.setAttribute('data-tooltip', content);
    element.setAttribute('data-tooltip-position', position);
    
    // Add appropriate ARIA attributes
    element.setAttribute('aria-describedby', generateTooltipId());
    
    // Add additional attributes for a11y
    if (!element.getAttribute('tabindex')) {
        element.setAttribute('tabindex', '0');
    }
    
    // Create tooltip container
    createTooltipContainer(element);
    
    // Add event listeners
    setupTooltipEvents(element);
}

// Export functions for use in other files
window.Tooltips = {
    createTooltip,
    initTooltips
}; 