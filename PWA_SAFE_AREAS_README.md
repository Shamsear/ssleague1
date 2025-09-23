# PWA Safe Areas Fix - Documentation

## Overview

This fix addresses the issue where your PWA header (with back button and logo) gets hidden behind phone notches, dynamic islands, and status bars.

## What's Been Added

### 1. CSS File: `static/css/pwa-safe-areas.css`
- Complete safe area inset handling for PWA environments
- Responsive design that works across different devices
- Dark mode support
- Accessibility improvements
- Utility classes for safe area spacing

### 2. JavaScript Utility: `static/js/safe-area-utils.js`
- Debug tools for development
- Automatic safe area detection and handling
- PWA mode detection
- Device notch detection

### 3. Enhanced Base Template: `templates/base.html`
- Includes the new CSS and JavaScript files
- Proper viewport configuration with `viewport-fit=cover`

## How It Works

The fix uses CSS environment variables (`env(safe-area-inset-*)`) to detect and adapt to device safe areas:

```css
.mobile-header-safe {
    padding-top: max(1rem, env(safe-area-inset-top));
    padding-left: max(1rem, env(safe-area-inset-left));
    padding-right: max(1rem, env(safe-area-inset-right));
    min-height: calc(3.5rem + env(safe-area-inset-top));
}
```

## Testing the Fix

### 1. On Desktop (Simulate)
1. Open Chrome DevTools (F12)
2. Click the device toolbar icon or press Ctrl+Shift+M
3. Select "iPhone X" or any device with a notch
4. Reload the page
5. The header should now have proper spacing

### 2. On Mobile Device
1. Add your PWA to home screen
2. Open the app from home screen (standalone mode)
3. Navigate to any page with a back button and logo
4. The header should no longer be hidden behind the notch

### 3. Debug Mode (Development Only)
1. Open browser console
2. Type `SafeAreaUtils.debug()` and press Enter
3. You'll see safe area information and visual debugging
4. Or use keyboard shortcut: Ctrl+Shift+S (or Cmd+Shift+S on Mac)

## Available CSS Classes

### Safe Area Utilities
- `.pt-safe` - Padding top with safe area
- `.pl-safe` - Padding left with safe area  
- `.pr-safe` - Padding right with safe area
- `.pb-safe` - Padding bottom with safe area
- `.p-safe` - All side padding with safe areas

### Container Classes
- `.mobile-header-safe` - Already applied to your header
- `.content-safe-area` - For main content areas
- `.container-safe` - For containers needing safe area awareness
- `.mobile-container-safe` - Mobile-specific container with safe areas

### PWA-Specific Classes
- `.pwa-mode` - Automatically added to body when in PWA mode
- `.pwa-header` - Enhanced header for PWA environments

## Browser Support

- **iOS Safari 11.1+** - Full support
- **Chrome 69+** - Full support
- **Firefox 69+** - Full support
- **Samsung Internet 10.1+** - Full support
- **Older browsers** - Graceful fallback with minimum padding

## Device Coverage

- iPhone X and newer (notch)
- iPhone 14 Pro and newer (Dynamic Island)  
- Android devices with notches/punch holes
- Devices with rounded corners
- Tablets in landscape mode

## Troubleshooting

### Header still hidden?
1. Ensure your PWA is installed and running in standalone mode
2. Check that `viewport-fit=cover` is in your meta viewport tag
3. Verify the `.mobile-header-safe` class is applied to your header
4. Run `SafeAreaUtils.debug()` in console to see current safe area values

### Visual debugging not showing?
1. Ensure you're on localhost or have `?debug=safe-areas` in URL
2. Check browser console for any JavaScript errors
3. Verify the safe-area-utils.js is loaded

### Still having issues?
1. Check browser console for errors
2. Verify all CSS and JS files are loading properly
3. Test on different devices and browsers
4. Use the debug utilities to understand current safe area values

## Performance Considerations

- CSS uses hardware-accelerated transforms
- JavaScript utilities only run on mobile devices
- Visual debugging is development-only and auto-removes
- All code includes support for reduced motion preferences

## Customization

### Adjusting Safe Area Padding
You can customize the minimum padding in the CSS file:

```css
.mobile-header-safe {
    padding-top: max(2rem, env(safe-area-inset-top)); /* Increase minimum to 2rem */
}
```

### Adding Safe Areas to Other Elements
Use the utility classes or apply the same pattern:

```css
.my-custom-element {
    padding-top: max(1rem, env(safe-area-inset-top));
}
```

### JavaScript Integration
Access safe area values in your JavaScript:

```javascript
// Get current safe area insets
const insets = SafeAreaUtils.getSafeAreaInsets();

// Check if device has notch
const hasNotch = SafeAreaUtils.hasNotch();

// Check if running as PWA
const isPWA = SafeAreaUtils.isStandalone();
```

## Implementation Notes

1. The fix is backwards compatible - older devices without safe areas will still work normally
2. Safe areas are only applied on mobile devices (width < 768px)
3. The solution works in both portrait and landscape orientations
4. Dark mode is automatically supported
5. All accessibility guidelines are maintained

## Future Maintenance

- Monitor new device releases for additional safe area requirements
- Update CSS if new safe area environment variables become available
- Test on new browser versions to ensure continued compatibility
- Consider removing debug code in production builds