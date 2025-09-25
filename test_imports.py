#!/usr/bin/env python3

"""
Test script to verify all imports are working correctly
"""

def test_admin_routes_import():
    """Test if admin_routes can be imported without errors"""
    try:
        from admin_routes import admin_bp
        print("✅ admin_routes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing admin_routes: {e}")
        return False

def test_access_control_import():
    """Test if access_control can be imported"""
    try:
        from access_control import require_admin, require_super_admin, AccessControl
        print("✅ access_control imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing access_control: {e}")
        return False

def test_models_import():
    """Test if models can be imported"""
    try:
        from models import User, Team, Season
        print("✅ models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        return False

def test_app_import():
    """Test if app can be imported"""
    try:
        import app
        print("✅ app imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing app: {e}")
        return False

def main():
    print("🧪 TESTING APPLICATION IMPORTS")
    print("=" * 50)
    
    tests = [
        ("Access Control", test_access_control_import),
        ("Models", test_models_import), 
        ("Admin Routes", test_admin_routes_import),
        ("Main App", test_app_import)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        success = test_func()
        results.append((test_name, success))
    
    print(f"\n" + "=" * 50)
    print("📊 RESULTS:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL IMPORTS SUCCESSFUL! The application should start properly.")
    else:
        print("❌ SOME IMPORTS FAILED. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    main()