#!/usr/bin/env python3
"""
Test Script for Telegram Deep Linking Integration

This script tests the Telegram deep linking functionality to ensure
everything is working correctly.
"""

from app import app
from models import db, User, TelegramUser
from telegram_service import get_telegram_bot
import json

def test_deep_link_generation():
    """Test deep link generation for a user"""
    print("🧪 Testing Deep Link Generation")
    print("=" * 50)
    
    with app.app_context():
        # Get telegram bot service
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            print("❌ Telegram bot service not available")
            print("   Make sure TELEGRAM_BOT_TOKEN is configured")
            return False
        
        # Find a test user (or create one)
        test_user = User.query.first()
        if not test_user:
            print("❌ No users found in database")
            print("   Create a user first to test deep linking")
            return False
        
        print(f"✅ Found test user: {test_user.username} (ID: {test_user.id})")
        
        # Test token generation
        token = telegram_bot.generate_link_token(test_user.id, test_user.username)
        if not token:
            print("❌ Failed to generate link token")
            return False
        
        print(f"✅ Generated secure token: {token[:20]}...")
        
        # Test token validation
        validation_result = telegram_bot.validate_link_token(token)
        if not validation_result.get('valid'):
            print(f"❌ Token validation failed: {validation_result.get('error')}")
            return False
        
        print("✅ Token validation passed")
        print(f"   User ID: {validation_result['user_id']}")
        print(f"   Username: {validation_result['username']}")
        print(f"   Expires: {validation_result['expires_at']}")
        
        # Test deep link generation
        deep_link = telegram_bot.generate_deep_link(test_user.id, test_user.username)
        if not deep_link:
            print("❌ Failed to generate deep link")
            return False
        
        print(f"✅ Generated deep link: {deep_link}")
        
        # Test API endpoint
        with app.test_client() as client:
            # Simulate user login for API test
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user.id)
                sess['_fresh'] = True
            
            response = client.get(f'/profile/telegram/link/{test_user.id}')
            if response.status_code == 200:
                data = response.get_json()
                if data and data.get('deep_link'):
                    print("✅ API endpoint working correctly")
                    print(f"   API deep link: {data['deep_link'][:50]}...")
                else:
                    print("❌ API returned invalid response")
                    print(f"   Response: {data}")
                    return False
            else:
                print(f"❌ API endpoint failed with status {response.status_code}")
                return False
        
        print("\n🎉 All deep linking tests passed!")
        return True

def test_telegram_status():
    """Test Telegram integration status"""
    print("\n📊 Testing Telegram Integration Status")
    print("=" * 50)
    
    with app.app_context():
        # Check bot configuration
        telegram_bot = get_telegram_bot()
        if telegram_bot:
            print("✅ Telegram bot service initialized")
            
            # Test bot token verification
            if telegram_bot.verify_bot_token():
                print("✅ Bot token is valid")
            else:
                print("⚠️  Bot token verification failed (check internet connection)")
        else:
            print("❌ Telegram bot service not available")
            return False
        
        # Check user linkings
        linked_users = TelegramUser.query.count()
        total_users = User.query.count()
        
        print(f"📈 Statistics:")
        print(f"   Total users: {total_users}")
        print(f"   Linked to Telegram: {linked_users}")
        print(f"   Link percentage: {(linked_users/total_users*100) if total_users > 0 else 0:.1f}%")
        
        # Show recent linkings
        recent_links = TelegramUser.query.order_by(TelegramUser.created_at.desc()).limit(5).all()
        if recent_links:
            print(f"\n🔗 Recent Telegram linkings:")
            for link in recent_links:
                status = "✅ Active" if link.is_active else "❌ Inactive"
                print(f"   {link.user.username} → @{link.telegram_username or 'Unknown'} ({status})")
        
        return True

def test_button_functionality():
    """Test button creation functionality"""
    print("\n🎛️  Testing Button Functionality")
    print("=" * 50)
    
    with app.app_context():
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            return False
        
        # Test main menu buttons
        main_menu = telegram_bot.create_main_menu_buttons()
        print("✅ Main menu buttons created")
        print(f"   Buttons: {len(main_menu['inline_keyboard'])} rows")
        
        # Test notification settings buttons
        notif_buttons = telegram_bot.create_notification_settings_buttons()
        print("✅ Notification settings buttons created")
        print(f"   Buttons: {len(notif_buttons['inline_keyboard'])} rows")
        
        # Test yes/no buttons
        yn_buttons = telegram_bot.create_yes_no_buttons("test_action")
        print("✅ Yes/No buttons created")
        print(f"   Buttons: {len(yn_buttons['inline_keyboard'][0])} buttons")
        
        # Test pagination buttons
        page_buttons = telegram_bot.create_navigation_buttons(2, 5, "test_page")
        print("✅ Pagination buttons created")
        print(f"   Buttons: {len(page_buttons['inline_keyboard'][0])} buttons")
        
        return True

def main():
    """Run all tests"""
    print("🚀 Telegram Deep Linking Integration Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Deep link generation
        if not test_deep_link_generation():
            print("\n❌ Deep link generation tests failed")
            return
        
        # Test 2: Integration status
        if not test_telegram_status():
            print("\n❌ Integration status tests failed")
            return
        
        # Test 3: Button functionality
        if not test_button_functionality():
            print("\n❌ Button functionality tests failed")
            return
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Your Telegram deep linking integration is working perfectly!")
        print("\n📋 Next Steps:")
        print("1. Update your profile template to use the new deep linking")
        print("2. Test the integration in your browser")
        print("3. Configure TELEGRAM_BOT_USERNAME in your environment")
        print("4. Set up webhook if not already configured")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()