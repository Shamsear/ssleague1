#!/usr/bin/env python3
"""
Script to check push notification subscriptions in the database.
"""

from app import app
from models import PushNotificationSubscription, User

def check_subscriptions():
    with app.app_context():
        # Check total subscriptions
        total_subs = PushNotificationSubscription.query.count()
        active_subs = PushNotificationSubscription.query.filter_by(is_active=True).count()
        
        print(f"Total push notification subscriptions: {total_subs}")
        print(f"Active push notification subscriptions: {active_subs}")
        
        # Check users
        total_users = User.query.count()
        approved_users = User.query.filter_by(is_approved=True).count()
        
        print(f"Total users: {total_users}")
        print(f"Approved users: {approved_users}")
        
        # Show recent subscriptions if any
        if total_subs > 0:
            print("\nRecent subscriptions:")
            recent_subs = PushNotificationSubscription.query.order_by(
                PushNotificationSubscription.created_at.desc()
            ).limit(5).all()
            
            for sub in recent_subs:
                user = User.query.get(sub.user_id)
                username = user.username if user else "Unknown"
                status = "Active" if sub.is_active else "Inactive"
                print(f"  User: {username}, Status: {status}, Created: {sub.created_at}")
        
        return active_subs

if __name__ == "__main__":
    active_count = check_subscriptions()
    
    if active_count == 0:
        print("\n🚨 This is why you're getting 'Sent to 0 users'!")
        print("Users need to:")
        print("1. Visit your app in a supported browser")
        print("2. Allow notifications when prompted")
        print("3. Have their browser register for push notifications")