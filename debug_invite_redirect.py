#!/usr/bin/env python3

import os
import sys
import requests
from urllib.parse import urljoin

def test_invite_redirect_behavior(base_url="http://127.0.0.1:5000", token="nYuIX7bjdugrc7ZUzaVJyyT2uVIcEA6l"):
    """Test what happens when accessing a fully used invite via HTTP"""
    
    print(f"🔍 Testing HTTP behavior for fully used invite")
    print("=" * 70)
    
    invite_url = f"{base_url}/register?invite={token}"
    print(f"Testing URL: {invite_url}")
    
    try:
        # Make a GET request to the invite URL
        print(f"\n📤 Making GET request to invite URL...")
        response = requests.get(invite_url, allow_redirects=False)
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            redirect_location = response.headers.get('Location', 'No Location header')
            print(f"🔀 Redirect to: {redirect_location}")
            
            # Follow the redirect
            if redirect_location:
                if redirect_location.startswith('/'):
                    redirect_url = urljoin(base_url, redirect_location)
                else:
                    redirect_url = redirect_location
                    
                print(f"\n📤 Following redirect to: {redirect_url}")
                final_response = requests.get(redirect_url)
                
                print(f"📥 Final status: {final_response.status_code}")
                print(f"📥 Final URL: {final_response.url}")
                
                # Check if the expected message appears in the response
                if "fully used" in final_response.text.lower():
                    print("✅ Found 'fully used' message in response!")
                elif "error validating invitation" in final_response.text.lower():
                    print("❌ Found 'Error validating invitation' message instead!")
                else:
                    print("🔍 Flash message content not found in response")
                    
                # Look for any flash messages in the HTML
                if 'class="flash' in final_response.text or 'alert' in final_response.text:
                    print("📋 Response contains flash message elements")
                else:
                    print("⚠️  Response doesn't seem to contain flash message elements")
                    
        elif response.status_code == 200:
            print("📄 Direct 200 response (no redirect)")
            
            # Check if it's the registration page with an error
            if "fully used" in response.text.lower():
                print("✅ Found 'fully used' message in direct response!")
            elif "error validating invitation" in response.text.lower():
                print("❌ Found 'Error validating invitation' message instead!")
            else:
                print("🔍 Neither message found in direct response")
                
        else:
            print(f"❓ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app. Make sure it's running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Error during HTTP test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 DEBUGGING INVITE REDIRECT BEHAVIOR")
    print("=" * 70)
    print("⚠️  Make sure your Flask app is running on http://127.0.0.1:5000")
    print("⚠️  The invite should be fully used (1/1) for this test")
    print()
    
    success = test_invite_redirect_behavior()
    
    if success:
        print(f"\n💡 If the test shows 'Error validating invitation' instead of")
        print(f"'This invitation link has been fully used', there's likely:")
        print(f"1. An exception in the Flask validation logic")
        print(f"2. A template rendering issue")
        print(f"3. Flash message handling problem")
        print(f"\nCheck your Flask console for any error messages!")
    else:
        print(f"\n❌ Could not test - make sure Flask app is running")