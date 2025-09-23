#!/usr/bin/env python3
"""
Test script to verify admin rounds page no longer shows refreshing indicators
"""

import os
import sys

def test_admin_rounds_template():
    """Test that admin rounds template has removed auto-refresh elements"""
    print("🔍 Testing admin_rounds.html for removed auto-refresh elements...")
    
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'admin_rounds.html')
    
    if not os.path.exists(template_path):
        print("❌ admin_rounds.html template not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that auto-refresh elements have been removed
    removed_elements = [
        'createRefreshIndicator',       # Auto-refresh indicator creation
        'showRefreshIndicator',         # Show refresh indicator function
        'hideRefreshIndicator',         # Hide refresh indicator function
        'toggleAutoRefresh',            # Auto-refresh toggle function
        'startAutoRefresh',             # Auto-refresh starter function
        'autoRefreshEnabled',           # Auto-refresh flag
        'refreshInterval',              # Refresh interval variable
        'refreshTimer',                 # Refresh timer variable
        'Refreshing...',                # Loading text
        'Refreshing page data...',      # Page refresh loading text
        'refresh-indicator',            # Refresh indicator element
        'Auto-refresh enabled',         # Auto-refresh messages
        'Auto-refresh disabled',        # Auto-refresh messages
    ]
    
    found_elements = []
    for element in removed_elements:
        if element in content:
            found_elements.append(element)
    
    if found_elements:
        print(f"❌ Found auto-refresh elements that should be removed: {found_elements}")
        return False
    else:
        print("✅ All auto-refresh elements have been successfully removed")
    
    # Check that essential admin functionality is still present
    essential_elements = [
        'Start Round',                  # Round creation
        'finalizeRound',               # Round finalization
        'updateRoundTimer',            # Timer updates
        'initializeTimers',            # Timer initialization
        'formatTime',                  # Time formatting
        'showLoading',                 # Loading overlay for actions
        'hideLoading',                 # Hide loading overlay
    ]
    
    missing_elements = []
    for element in essential_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing essential elements: {missing_elements}")
        return False
    else:
        print("✅ All essential admin functionality is still present")
    
    return True

def test_timer_functionality_preserved():
    """Test that timer functionality is still present but not auto-refreshing"""
    print("🔍 Testing that timer functionality is preserved...")
    
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'admin_rounds.html')
    
    if not os.path.exists(template_path):
        print("❌ admin_rounds.html template not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Timer functions should still exist
    timer_elements = [
        'initTimer(',                   # Timer initialization
        'checkStatus',                  # Status checking
        'formatTime(',                  # Time formatting
        'timer-remaining-',             # Timer display elements
    ]
    
    found_timer_elements = []
    for element in timer_elements:
        if element in content:
            found_timer_elements.append(element)
    
    print(f"✅ Timer elements found: {found_timer_elements}")
    
    if len(found_timer_elements) >= 3:
        print("✅ Timer functionality is preserved")
        return True
    else:
        print("❌ Timer functionality may be missing")
        return False

def test_manual_actions_preserved():
    """Test that manual admin actions are still available"""
    print("🔍 Testing that manual admin actions are preserved...")
    
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'admin_rounds.html')
    
    if not os.path.exists(template_path):
        print("❌ admin_rounds.html template not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Manual action functions should still exist
    manual_actions = [
        'startRoundForm',               # Start round form
        'finalizeRound(',               # Finalize round button
        'updateRoundTimer(',            # Update timer button
        'deleteRound(',                 # Delete round button
        'forcePageRefresh',             # Manual refresh when needed
    ]
    
    found_actions = []
    for action in manual_actions:
        if action in content:
            found_actions.append(action)
    
    print(f"✅ Manual actions found: {found_actions}")
    
    if len(found_actions) >= 4:
        print("✅ Manual admin actions are preserved")
        return True
    else:
        print("❌ Some manual admin actions may be missing")
        return False

def test_dom_content_loaded_simplified():
    """Test that DOMContentLoaded is simplified without auto-refresh"""
    print("🔍 Testing that DOMContentLoaded is simplified...")
    
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'admin_rounds.html')
    
    if not os.path.exists(template_path):
        print("❌ admin_rounds.html template not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that DOMContentLoaded is simplified
    dom_loaded_section = content[content.find("document.addEventListener('DOMContentLoaded'"):]
    
    # Should NOT contain auto-refresh setup
    auto_refresh_setup = [
        'createRefreshIndicator',
        'startAutoRefresh',
        'forcePageRefresh().then',
        'refreshInterval',
        'visibilitychange',
    ]
    
    found_auto_refresh = []
    for setup in auto_refresh_setup:
        if setup in dom_loaded_section:
            found_auto_refresh.append(setup)
    
    if found_auto_refresh:
        print(f"❌ Found auto-refresh setup in DOMContentLoaded: {found_auto_refresh}")
        return False
    else:
        print("✅ DOMContentLoaded is simplified without auto-refresh setup")
    
    # Should contain basic initialization
    basic_init = [
        'hideLoading',
        'initializeTimers',
        'adjustForMobile',
    ]
    
    found_basic_init = []
    for init in basic_init:
        if init in dom_loaded_section:
            found_basic_init.append(init)
    
    if len(found_basic_init) >= 2:
        print("✅ Basic initialization is still present")
        return True
    else:
        print("❌ Basic initialization may be missing")
        return False

def main():
    """Run all tests for admin no auto-refresh"""
    print("🧪 Testing Admin Rounds - No Auto-Refresh")
    print("=" * 50)
    
    tests = [
        ("Auto-Refresh Elements Removed", test_admin_rounds_template),
        ("Timer Functionality Preserved", test_timer_functionality_preserved),
        ("Manual Actions Preserved", test_manual_actions_preserved),
        ("DOMContentLoaded Simplified", test_dom_content_loaded_simplified),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n💡 Admin rounds page improvements:")
        print("   ✅ Removed auto-refresh loading indicators")
        print("   ✅ Removed constant 'Refreshing...' messages")
        print("   ✅ Simplified page initialization")
        print("   ✅ Preserved essential admin functionality")
        print("   ✅ Kept manual refresh capabilities when needed")
        print("\n🚀 Admin experience is now cleaner and less distracting!")
    else:
        print(f"\n⚠️  {failed} test(s) failed - some functionality may not be working correctly")
    
    return passed, failed

if __name__ == '__main__':
    main()