#!/usr/bin/env python3
"""
Local testing script for PWA notifications

This script runs the Flask app locally with HTTPS (required for push notifications)
and provides comprehensive testing instructions.
"""

import os
import sys
from app import app

def run_local_server():
    """Run the Flask app locally with HTTPS for testing PWA notifications"""
    
    print("🚀 Starting Local PWA Notification Test Server...")
    print("=" * 60)
    
    # Ensure VAPID keys are set
    if not os.environ.get('VAPID_PRIVATE_KEY'):
        print("❌ VAPID_PRIVATE_KEY not set!")
        print("Run these commands first:")
        print('$env:VAPID_PRIVATE_KEY = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JR0hBZ0VBTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEJHMHdhd0lCQVFRZ1BleGZsUjhXTExBMWJvby8KNUxiQ20xbmNnUkxrTnFDbVEyL0NXdVJqTForaFJBTkNBQVN0Q2NWMEdiTS9mWkVoaDRxeXg5UjJkTHpyS1NRQQo4Mllrc2FNbWxSL3lOd3dLeERDdzBXU0ZjTEM2VEtsb0k4SnowMndHemhiVVU2bWxWTUR3MDR5SQotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg=="')
        print('$env:VAPID_PUBLIC_KEY = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFclFuRmRCbXpQMzJSSVllS3NzZlVkblM4NnlrawpBUE5tSkxHakpwVWY4amNNQ3NRd3NORmtoWEN3dWt5cGFDUENjOU5zQnM0VzFGT3BwVlRBOE5PTWlBPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="')
        print('$env:VAPID_CLAIMS_SUB = "mailto:admin@ssleague.com"')
        return
    
    print("✅ VAPID keys detected")
    print(f"✅ Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")
    
    print("\n🌐 Server Information:")
    print("   URL: http://localhost:5000")
    print("   Admin Dashboard: http://localhost:5000/admin/dashboard")
    print("   Database Management: http://localhost:5000/admin/database")
    
    print("\n📱 Testing Instructions:")
    print("1. Open http://localhost:5000 in Chrome/Firefox")
    print("2. Log in as admin")
    print("3. Go to Admin → Database Management")
    print("4. Scroll to 'PWA Notification Testing' section")
    print("5. Check system status and send test notifications")
    
    print("\n⚠️  Important Notes:")
    print("• PWA notifications work best with HTTPS")
    print("• For full testing, use ngrok or deploy to test environment")
    print("• Chrome DevTools → Application → Service Workers to debug")
    
    print("\n" + "=" * 60)
    print("Starting server... Press Ctrl+C to stop")
    
    try:
        # Run with debug mode for local testing
        app.run(
            host='localhost',
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n✅ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == "__main__":
    run_local_server()