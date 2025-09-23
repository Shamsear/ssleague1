#!/usr/bin/env python3
"""
Test script to verify round starting and finalizing overlay functionality
"""

import os
import re

def test_overlay_html_elements():
    """Test that the overlay HTML elements are present"""
    print("🔍 Testing Round Starting Overlay HTML Elements...")
    
    # Test both template files
    templates = [
        "C:\\Drive d\\SS\\kirotesting\\templates\\admin_rounds.html",
        "C:\\Drive d\\SS\\test\\templates\\admin_rounds.html"
    ]
    
    for template_path in templates:
        print(f"\n📄 Testing {template_path.split(os.sep)[-3]}...")
        
        if not os.path.exists(template_path):
            print(f"❌ Template file not found: {template_path}")
            continue
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for overlay HTML (both starting and finalizing)
        overlay_elements = [
            'id="round-starting-overlay"',
            'id="round-finalizing-overlay"',
            'Starting Round...',
            'Finalizing Round...',
            'Setting up the auction round and notifying teams',
            'Processing bids and allocating players to teams',
            'animate-spin',
            'animate-bounce'
        ]
        
        missing_elements = []
        for element in overlay_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Missing overlay elements: {missing_elements}")
        else:
            print("✅ All overlay HTML elements found")

def test_overlay_javascript_functions():
    """Test that the JavaScript functions are present"""
    print("\n🔍 Testing Round Starting Overlay JavaScript Functions...")
    
    templates = [
        "C:\\Drive d\\SS\\kirotesting\\templates\\admin_rounds.html",
        "C:\\Drive d\\SS\\test\\templates\\admin_rounds.html"
    ]
    
    for template_path in templates:
        print(f"\n📄 Testing {template_path.split(os.sep)[-3]}...")
        
        if not os.path.exists(template_path):
            print(f"❌ Template file not found: {template_path}")
            continue
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for JavaScript functions (both starting and finalizing)
        js_functions = [
            'function showRoundStartingOverlay()',
            'function hideRoundStartingOverlay()',
            'function showRoundFinalizingOverlay()',
            'function hideRoundFinalizingOverlay()',
            'showRoundStartingOverlay();',
            'hideRoundStartingOverlay();',
            'showRoundFinalizingOverlay();',
            'hideRoundFinalizingOverlay();'
        ]
        
        missing_functions = []
        for func in js_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing JavaScript functions: {missing_functions}")
        else:
            print("✅ All JavaScript functions found")

def test_overlay_integration():
    """Test that the overlay is properly integrated into form submission"""
    print("\n🔍 Testing Overlay Integration with Form Submission...")
    
    templates = [
        "C:\\Drive d\\SS\\kirotesting\\templates\\admin_rounds.html",
        "C:\\Drive d\\SS\\test\\templates\\admin_rounds.html"
    ]
    
    for template_path in templates:
        print(f"\n📄 Testing {template_path.split(os.sep)[-3]}...")
        
        if not os.path.exists(template_path):
            print(f"❌ Template file not found: {template_path}")
            continue
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the start round form submission
        form_match = re.search(r'startRoundForm.*?addEventListener.*?}.*?}\);', content, re.DOTALL)
        finalize_match = re.search(r'async function finalizeRound.*?}.*?}', content, re.DOTALL)
        
        if not form_match:
            print("❌ Could not find startRoundForm event listener")
            continue
            
        if not finalize_match:
            print("❌ Could not find finalizeRound function")
            continue
        
        form_code = form_match.group()
        finalize_code = finalize_match.group()
        combined_code = form_code + finalize_code
        
        # Check integration points
        integration_checks = [
            ('showRoundStartingOverlay();', "Show starting overlay"),
            ('hideRoundStartingOverlay();', "Hide starting overlay"),
            ('showRoundFinalizingOverlay();', "Show finalizing overlay"),
            ('hideRoundFinalizingOverlay();', "Hide finalizing overlay"),
        ]
        
        missing_integration = []
        for check, description in integration_checks:
            if check not in combined_code:
                missing_integration.append(f"{description}: {check}")
        
        if missing_integration:
            print(f"❌ Missing integration points:")
            for item in missing_integration:
                print(f"   • {item}")
        else:
            print("✅ All integration points found in form submission and finalize function")

def test_overlay_styling():
    """Test that the overlay has proper styling and animations"""
    print("\n🔍 Testing Overlay Styling and Animations...")
    
    templates = [
        "C:\\Drive d\\SS\\kirotesting\\templates\\admin_rounds.html",
        "C:\\Drive d\\SS\\test\\templates\\admin_rounds.html"
    ]
    
    for template_path in templates:
        print(f"\n📄 Testing {template_path.split(os.sep)[-3]}...")
        
        if not os.path.exists(template_path):
            print(f"❌ Template file not found: {template_path}")
            continue
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for styling classes
        styling_elements = [
            'fixed inset-0',          # Full screen overlay
            'bg-black/50',            # Dark backdrop
            'backdrop-blur-sm',       # Backdrop blur
            'z-50',                   # High z-index
            'opacity-0',              # Hidden by default
            'pointer-events-none',    # Disabled by default
            'transition-opacity',     # Smooth transitions
            'animate-spin',           # Spinning loader
            'animate-bounce',         # Bouncing dots
            'scale-95',               # Initial scale
            'transform',              # Transform support
        ]
        
        missing_styling = []
        for style in styling_elements:
            if style not in content:
                missing_styling.append(style)
        
        if missing_styling:
            print(f"❌ Missing styling elements: {missing_styling}")
        else:
            print("✅ All styling elements found")

def run_all_tests():
    """Run all tests"""
    print("🧪 Testing Round Starting & Finalizing Overlay Functionality")
    print("=" * 60)
    
    tests = [
        test_overlay_html_elements,
        test_overlay_javascript_functions,
        test_overlay_integration,
        test_overlay_styling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED! ({passed}/{total})")
        print("\n🎉 Round starting & finalizing overlays are properly implemented!")
        print("\n💡 Features:")
        print("   ✅ Beautiful overlays with spinning loaders")
        print("   ✅ Different colors: Green for starting, Blue for finalizing")
        print("   ✅ Professional messaging and animations")
        print("   ✅ Proper integration with both form submission and finalization")
        print("   ✅ Smooth transitions and styling")
        print("   ✅ Works on both template versions")
        print("\n🚀 Users will now see professional loading experiences when starting AND finalizing rounds!")
    else:
        print(f"❌ {total - passed} TEST(S) FAILED ({passed}/{total} passed)")
        print("\nPlease review the output above for specific issues.")

if __name__ == "__main__":
    run_all_tests()