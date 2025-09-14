#!/usr/bin/env python3
"""
Complete Pre-Deployment Testing Suite for PWA Notifications

This script runs comprehensive tests to ensure everything works before deployment.
"""

import json
import os
import time
from app import app, db
from models import User, Team, Player, Round, PushNotificationSubscription
from notification_service import notification_service

def run_comprehensive_tests():
    """Run complete test suite before deployment"""
    
    print("🧪 Comprehensive Pre-Deployment Testing Suite")
    print("=" * 70)
    
    test_results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    def log_test(name, passed, message=""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if message:
            print(f"    {message}")
        
        test_results['tests'].append({
            'name': name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            test_results['passed'] += 1
        else:
            test_results['failed'] += 1
    
    with app.app_context():
        print("🔍 Testing Infrastructure Components...")
        print("-" * 50)
        
        # Test 1: Database Connection
        try:
            user_count = User.query.count()
            log_test("Database Connection", True, f"Connected, {user_count} users found")
        except Exception as e:
            log_test("Database Connection", False, f"Error: {str(e)}")
        
        # Test 2: VAPID Configuration
        vapid_ok = bool(
            notification_service.vapid_private_key and 
            notification_service.vapid_public_key
        )
        log_test("VAPID Keys Configuration", vapid_ok, 
                "Keys properly set" if vapid_ok else "Keys missing - set environment variables")
        
        # Test 3: Database Models
        try:
            subscription_count = PushNotificationSubscription.query.count()
            log_test("PushNotificationSubscription Model", True, 
                    f"Model working, {subscription_count} subscriptions")
        except Exception as e:
            log_test("PushNotificationSubscription Model", False, f"Error: {str(e)}")
        
        # Test 4: Notification Service Methods
        try:
            # Test method exists and callable
            assert hasattr(notification_service, 'send_notification_to_all_teams')
            assert callable(notification_service.send_notification_to_all_teams)
            log_test("Notification Service Methods", True, "All methods accessible")
        except Exception as e:
            log_test("Notification Service Methods", False, f"Error: {str(e)}")
        
        print("\n🔧 Testing API Endpoints...")
        print("-" * 50)
        
        # Get admin user for testing
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            log_test("Admin User Available", False, "No admin user found")
            print("\n❌ Cannot continue API tests without admin user")
            return test_results
        
        log_test("Admin User Available", True, f"Testing as: {admin_user.username}")
        
        with app.test_client() as client:
            # Simulate admin login
            with client.session_transaction() as session:
                session['_user_id'] = str(admin_user.id)
                session['_fresh'] = True
            
            # Test 5: VAPID Public Key Endpoint
            try:
                response = client.get('/api/vapid-public-key')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    has_key = 'publicKey' in data and data['publicKey']
                    log_test("VAPID Public Key API", has_key, 
                            f"Status: {response.status_code}, Key length: {len(data.get('publicKey', ''))}")
                else:
                    log_test("VAPID Public Key API", False, f"Status: {response.status_code}")
            except Exception as e:
                log_test("VAPID Public Key API", False, f"Error: {str(e)}")
            
            # Test 6: Subscribe API
            try:
                test_subscription = {
                    "subscription": {
                        "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
                        "keys": {
                            "p256dh": "test_p256dh_key_" + str(int(time.time())),
                            "auth": "test_auth_key_" + str(int(time.time()))
                        }
                    }
                }
                response = client.post('/api/subscribe', json=test_subscription,
                                     headers={'Content-Type': 'application/json'})
                success = response.status_code == 200
                log_test("Subscribe API", success, f"Status: {response.status_code}")
            except Exception as e:
                log_test("Subscribe API", False, f"Error: {str(e)}")
            
            # Test 7: System Status API
            try:
                response = client.get('/admin/notification_system_status')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    log_test("System Status API", True, 
                            f"VAPID: {data.get('vapid_configured')}, "
                            f"Subscriptions: {data.get('subscription_count')}")
                else:
                    log_test("System Status API", False, f"Status: {response.status_code}")
            except Exception as e:
                log_test("System Status API", False, f"Error: {str(e)}")
            
            # Test 8: Test Notification API
            try:
                test_data = {
                    "title": "🧪 Pre-Deploy Test",
                    "message": "Testing notification system before deployment",
                    "type": "info"
                }
                response = client.post('/admin/test_notification_all', json=test_data,
                                     headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    data = json.loads(response.data)
                    log_test("Test Notification API", True, 
                            f"Sent to {data.get('sent_count', 0)} users")
                else:
                    log_test("Test Notification API", False, f"Status: {response.status_code}")
            except Exception as e:
                log_test("Test Notification API", False, f"Error: {str(e)}")
        
        print("\n📱 Testing PWA Components...")
        print("-" * 50)
        
        # Test 9: Service Worker File
        try:
            sw_path = os.path.join(app.static_folder, 'js', 'sw.js')
            if os.path.exists(sw_path):
                with open(sw_path, 'r', encoding='utf-8') as f:
                    sw_content = f.read()
                has_push_handler = 'addEventListener(\'push\'' in sw_content
                has_click_handler = 'addEventListener(\'notificationclick\'' in sw_content
                log_test("Service Worker Push Handlers", 
                        has_push_handler and has_click_handler,
                        f"Push: {has_push_handler}, Click: {has_click_handler}")
            else:
                log_test("Service Worker File", False, "sw.js not found")
        except Exception as e:
            log_test("Service Worker File", False, f"Error: {str(e)}")
        
        # Test 10: Manifest File  
        try:
            manifest_path = os.path.join(app.static_folder, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                has_name = 'name' in manifest
                has_icons = 'icons' in manifest and len(manifest['icons']) > 0
                log_test("PWA Manifest", has_name and has_icons,
                        f"Name: {manifest.get('name', 'Missing')}, Icons: {len(manifest.get('icons', []))}")
            else:
                log_test("PWA Manifest", False, "manifest.json not found")
        except Exception as e:
            log_test("PWA Manifest", False, f"Error: {str(e)}")
        
        # Test 11: Notifications.js File
        try:
            notif_path = os.path.join(app.static_folder, 'js', 'notifications.js')
            if os.path.exists(notif_path):
                with open(notif_path, 'r', encoding='utf-8') as f:
                    notif_content = f.read()
                has_subscription = 'subscribeToPushNotifications' in notif_content
                has_permission = 'requestNotificationPermission' in notif_content
                log_test("Notifications.js", has_subscription and has_permission,
                        f"Subscription: {has_subscription}, Permission: {has_permission}")
            else:
                log_test("Notifications.js File", False, "notifications.js not found")
        except Exception as e:
            log_test("Notifications.js File", False, f"Error: {str(e)}")
        
        print("\n🎯 Testing Activity Triggers...")
        print("-" * 50)
        
        # Test 12: Auction Notification Trigger
        try:
            # Simulate auction start (won't actually send without subscriptions)
            sent = notification_service.send_notification_to_all_teams(
                "🧪 Test Auction Started",
                "Testing auction notification trigger",
                'auction'
            )
            log_test("Auction Notification Trigger", True, f"Triggered successfully")
        except Exception as e:
            log_test("Auction Notification Trigger", False, f"Error: {str(e)}")
        
        # Test 13: Admin Notification Trigger
        try:
            sent = notification_service.send_notification_to_admins(
                "🧪 Test Admin Notification",
                "Testing admin notification trigger",
                'admin'
            )
            log_test("Admin Notification Trigger", True, f"Triggered successfully")
        except Exception as e:
            log_test("Admin Notification Trigger", False, f"Error: {str(e)}")
    
    # Print Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"✅ PASSED: {test_results['passed']} tests")
    print(f"❌ FAILED: {test_results['failed']} tests")
    print(f"📝 TOTAL:  {len(test_results['tests'])} tests")
    
    if test_results['failed'] == 0:
        print("\n🎉 ALL TESTS PASSED! Ready for deployment! 🚀")
        print("\n✅ Deployment Checklist:")
        print("   1. Set VAPID environment variables in production")
        print("   2. Ensure HTTPS is enabled")
        print("   3. Deploy your application")
        print("   4. Test notifications in production environment")
        print("   5. Verify PWA installation works")
    else:
        print(f"\n⚠️  {test_results['failed']} test(s) failed. Review and fix before deployment.")
        print("\n❌ Failed Tests:")
        for test in test_results['tests']:
            if not test['passed']:
                print(f"   • {test['name']}: {test['message']}")
    
    return test_results

if __name__ == "__main__":
    run_comprehensive_tests()