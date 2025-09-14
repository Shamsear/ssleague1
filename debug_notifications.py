#!/usr/bin/env python3
"""
Debug script to check notification system status
"""

import os
from app import app
from models import PushNotificationSubscription, User
from notification_service import notification_service

def debug_notifications():
    print("🔍 Notification System Debug Report")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    vapid_private = os.environ.get('VAPID_PRIVATE_KEY')
    vapid_public = os.environ.get('VAPID_PUBLIC_KEY')
    vapid_claims = os.environ.get('VAPID_CLAIMS_SUB')
    
    print(f"VAPID_PRIVATE_KEY: {'✅ Set' if vapid_private else '❌ Missing'}")
    print(f"VAPID_PUBLIC_KEY: {'✅ Set' if vapid_public else '❌ Missing'}")
    print(f"VAPID_CLAIMS_SUB: {vapid_claims if vapid_claims else '❌ Missing'}")
    
    if vapid_public:
        print(f"Public Key (first 50 chars): {vapid_public[:50]}...")
    
    # Check notification service
    print(f"\nNotification Service Status:")
    print(f"Service initialized: {'✅ Yes' if notification_service else '❌ No'}")
    print(f"VAPID keys in service: {'✅ Yes' if notification_service.vapid_private_key and notification_service.vapid_public_key else '❌ No'}")
    
    with app.app_context():
        # Check database subscriptions
        print(f"\n📊 Database Status:")
        total_subs = PushNotificationSubscription.query.count()
        active_subs = PushNotificationSubscription.query.filter_by(is_active=True).count()
        total_users = User.query.count()
        
        print(f"Total subscriptions: {total_subs}")
        print(f"Active subscriptions: {active_subs}")
        print(f"Total users: {total_users}")
        
        # Show recent subscriptions
        if total_subs > 0:
            print(f"\n📝 Recent Subscriptions:")
            recent_subs = PushNotificationSubscription.query.order_by(
                PushNotificationSubscription.created_at.desc()
            ).limit(3).all()
            
            for sub in recent_subs:
                user = User.query.get(sub.user_id)
                status = "🟢 Active" if sub.is_active else "🔴 Inactive"
                print(f"  {status} - User: {user.username if user else 'Unknown'} - Created: {sub.created_at}")
        else:
            print(f"\n📝 No subscriptions found in database")
            
    print(f"\n🎯 Next Steps:")
    if not vapid_private or not vapid_public:
        print("1. ❌ Set VAPID environment variables")
    else:
        print("1. ✅ VAPID keys are configured")
        
    if active_subs == 0:
        print("2. ❌ Users need to subscribe via browser")
        print("   - Enable notifications in browser settings")
        print("   - Visit notification settings page")
        print("   - Click 'Enable Push Notifications' button")
    else:
        print(f"2. ✅ {active_subs} user(s) subscribed")
        
    print("\n🌐 Browser Requirements:")
    print("- Notifications must be 'Allowed' in browser settings")
    print("- Service worker must register successfully")
    print("- HTTPS required for production (localhost is OK for testing)")

if __name__ == "__main__":
    debug_notifications()