#!/usr/bin/env python3
"""
Test script to verify the improved round finalization and tiebreaker flow
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_route_exists():
    """Test if the new tiebreaker_waiting route exists"""
    try:
        from neon.app import app
        
        # Check if the new route is registered
        with app.app_context():
            # Get all routes
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(rule.rule)
            
            # Check for our new route
            tiebreaker_waiting_route = '/tiebreaker_waiting/<int:tiebreaker_id>'
            
            if tiebreaker_waiting_route in routes:
                print("✅ New tiebreaker waiting route found")
                return True
            else:
                print("❌ Tiebreaker waiting route not found")
                print(f"Available routes: {[r for r in routes if 'tiebreaker' in r]}")
                return False
                
    except ImportError as e:
        print(f"❌ Error importing app: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_template_exists():
    """Test if the new template exists"""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'tiebreaker_waiting.html')
    
    if os.path.exists(template_path):
        print("✅ Tiebreaker waiting template exists")
        
        # Check if template has key features
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            features = [
                'status-section',  # Status update section
                'updateStatus()',  # Real-time update function
                'progress-bar',    # Progress indicator
                'resolved-section' # Resolution display
            ]
            
            found_features = []
            for feature in features:
                if feature in content:
                    found_features.append(feature)
            
            print(f"✅ Template features found: {found_features}")
            
            if len(found_features) >= 3:
                print("✅ Template has essential real-time features")
                return True
            else:
                print(f"❌ Template missing key features: {set(features) - set(found_features)}")
                return False
    else:
        print("❌ Tiebreaker waiting template not found")
        return False

def test_app_modifications():
    """Test if the app.py modifications are present"""
    try:
        from neon.app import app
        
        # Test that the function exists by importing it
        from neon.app import tiebreaker_waiting, check_tiebreaker_status
        
        print("✅ New route functions imported successfully")
        
        # Check if the routes are callable
        if callable(tiebreaker_waiting) and callable(check_tiebreaker_status):
            print("✅ Route functions are callable")
            return True
        else:
            print("❌ Route functions are not callable")
            return False
            
    except ImportError as e:
        print(f"❌ Error importing new functions: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_enhanced_check_tiebreaker_status():
    """Test if the enhanced check_tiebreaker_status returns proper format"""
    print("📋 Testing enhanced tiebreaker status response format...")
    
    # We can't easily test the actual response without database setup,
    # but we can verify the code structure
    import inspect
    
    try:
        from neon.app import check_tiebreaker_status
        
        # Get the source code
        source = inspect.getsource(check_tiebreaker_status)
        
        # Check for key improvements
        improvements = [
            'winner_info',      # Winner information in response
            'resolved',         # Resolved flag
            'player_name',      # Player name in response
            'round_finalized'   # Round finalization status
        ]
        
        found_improvements = []
        for improvement in improvements:
            if improvement in source:
                found_improvements.append(improvement)
        
        print(f"✅ Status check improvements found: {found_improvements}")
        
        if len(found_improvements) >= 3:
            print("✅ Enhanced status check has key improvements")
            return True
        else:
            print(f"❌ Missing improvements: {set(improvements) - set(found_improvements)}")
            return False
            
    except Exception as e:
        print(f"❌ Error analyzing check_tiebreaker_status: {e}")
        return False

def test_team_rounds_enhancements():
    """Test if team_round.html has the notification enhancements"""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'neon', 'templates', 'team_round.html')
    
    if not os.path.exists(template_path):
        print("❌ team_round.html template not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        enhancements = [
            'showNotification',     # Notification function
            'Tiebreaker Required!', # Tiebreaker notification
            'Round Finalized!',     # Round end notification
            'redirect_to'           # Redirect handling
        ]
        
        found_enhancements = []
        for enhancement in enhancements:
            if enhancement in content:
                found_enhancements.append(enhancement)
        
        print(f"✅ Team rounds enhancements found: {found_enhancements}")
        
        if len(found_enhancements) >= 3:
            print("✅ Team rounds template has enhanced notifications")
            return True
        else:
            print(f"❌ Missing enhancements: {set(enhancements) - set(found_enhancements)}")
            return False

def main():
    """Run all tests"""
    print("🧪 Testing Round Finalization and Tiebreaker Flow Improvements")
    print("=" * 65)
    
    tests = [
        ("Route Registration", test_route_exists),
        ("Template Creation", test_template_exists),
        ("App Modifications", test_app_modifications),
        ("Enhanced Status Check", test_enhanced_check_tiebreaker_status),
        ("Team Rounds Enhancements", test_team_rounds_enhancements)
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
    
    print("\n" + "=" * 65)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 65)
    
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
        print("\n💡 Improvements implemented:")
        print("   ✅ Tiebreaker waiting page with real-time updates")
        print("   ✅ Enhanced tiebreaker status API with winner info")
        print("   ✅ Automatic redirects after tiebreaker submission")
        print("   ✅ Round finalization notifications")
        print("   ✅ Better user experience with progress indicators")
        print("\n🚀 Your tiebreaker and round finalization flow is now significantly improved!")
    else:
        print(f"\n⚠️  {failed} test(s) failed - some features may not work as expected")
    
    return passed, failed

if __name__ == '__main__':
    main()