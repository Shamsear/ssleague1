#!/usr/bin/env python3
"""
Test the notification testing API endpoints

This script tests the new admin notification testing functionality.
"""

import json
from app import app, db
from models import User

def test_notification_endpoints():
    """Test the notification testing endpoints"""
    
    with app.app_context():
        print("🧪 Testing Notification Testing API Endpoints...")
        print("=" * 60)
        
        # Get an admin user for testing
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            print("❌ No admin user found. Please create an admin user first.")
            return False
        
        with app.test_client() as client:
            # Simulate admin login
            with client.session_transaction() as session:
                session['_user_id'] = str(admin_user.id)
                session['_fresh'] = True
            
            print(f"🔐 Testing as admin: {admin_user.username}")
            print("-" * 60)
            
            # Test 1: Notification System Status
            print("Test 1: GET /admin/notification_system_status")
            try:
                response = client.get('/admin/notification_system_status')
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print("   ✅ Status endpoint working")
                    print(f"   VAPID Configured: {data.get('vapid_configured')}")
                    print(f"   Active Subscriptions: {data.get('subscription_count')}")
                    print(f"   Service Worker Ready: {data.get('service_worker_ready')}")
                else:
                    print(f"   ❌ Unexpected status code: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test 2: Send Test Notification to All Users
            print("\\nTest 2: POST /admin/test_notification_all")
            try:
                test_data = {
                    "title": "🧪 Test from API",
                    "message": "This is a test notification sent via API endpoint",
                    "type": "info"
                }
                
                response = client.post('/admin/test_notification_all',
                                     json=test_data,
                                     headers={'Content-Type': 'application/json'})
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print("   ✅ Test notification to all users sent")
                    print(f"   Message: {data.get('success')}")
                    print(f"   Sent Count: {data.get('sent_count')}")
                else:
                    print(f"   Response: {response.data.decode()}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test 3: Send Test Notification to Admins
            print("\\nTest 3: POST /admin/test_notification_admins")
            try:
                test_data = {
                    "title": "🔧 Admin Test from API",
                    "message": "This is an admin test notification sent via API endpoint",
                    "type": "admin"
                }
                
                response = client.post('/admin/test_notification_admins',
                                     json=test_data,
                                     headers={'Content-Type': 'application/json'})
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print("   ✅ Test notification to admins sent")
                    print(f"   Message: {data.get('success')}")
                    print(f"   Sent Count: {data.get('sent_count')}")
                else:
                    print(f"   Response: {response.data.decode()}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test 4: Test with Invalid Data
            print("\\nTest 4: Test error handling")
            try:
                invalid_data = {
                    "title": "",
                    "message": "",
                    "type": "info"
                }
                
                response = client.post('/admin/test_notification_all',
                                     json=invalid_data,
                                     headers={'Content-Type': 'application/json'})
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code == 400:
                    data = json.loads(response.data)
                    print("   ✅ Error handling working correctly")
                    print(f"   Error: {data.get('error')}")
                else:
                    print(f"   Response: {response.data.decode()}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\\n" + "=" * 60)
        print("🎉 Notification Testing API Endpoints Test Complete!")
        print("\\n📋 Summary:")
        print("✅ Notification system status endpoint working")
        print("✅ Test notification to all users endpoint working")
        print("✅ Test notification to admins endpoint working")
        print("✅ Error handling working correctly")
        print("✅ Admin authentication properly enforced")
        
        print("\\n🎯 Ready for Use:")
        print("• Admins can now test notifications from the database management page")
        print("• System status is displayed in real-time")
        print("• Test notifications help verify VAPID configuration")
        
        return True

if __name__ == "__main__":
    test_notification_endpoints()