#!/usr/bin/env python3
"""
Test script for timer functionality
"""

import requests
import json
import time
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(endpoint, description=""):
    """Test an endpoint and return the result"""
    try:
        print(f"\n🧪 Testing: {endpoint}")
        if description:
            print(f"   Description: {description}")
        
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"   HTML Response length: {len(response.text)} characters")
                # Check for key timer elements
                if "TimerUtils" in response.text:
                    print("   ✅ TimerUtils found in response")
                if "countdown" in response.text:
                    print("   ✅ Countdown element found in response")
                if "timer-bar" in response.text:
                    print("   ✅ Timer bar element found in response")
                return {"status": "success", "html_length": len(response.text)}
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Network Error: {e}")
        return None

def test_bulk_round_status():
    """Test bulk round status endpoint"""
    print("\n🔍 Testing bulk round status endpoints...")
    
    # Try a few different bulk round IDs
    for bulk_id in [1, 2, 3]:
        endpoint = f"/check_bulk_round_status/{bulk_id}"
        result = test_endpoint(endpoint, f"Bulk round {bulk_id} status")
        if result and isinstance(result, dict) and 'remaining' in result:
            print(f"   ✅ Found active bulk round {bulk_id} with {result.get('remaining', 0)} seconds remaining")
            return bulk_id
    
    print("   ℹ️  No active bulk rounds found")
    return None

def test_round_status():
    """Test regular round status endpoint"""
    print("\n🔍 Testing round status endpoints...")
    
    # Try a few different round IDs
    for round_id in [1, 2, 3]:
        endpoint = f"/round/{round_id}/status"
        result = test_endpoint(endpoint, f"Round {round_id} status")
        if result and isinstance(result, dict) and 'remaining' in result:
            print(f"   ✅ Found active round {round_id} with {result.get('remaining', 0)} seconds remaining")
            return round_id
    
    print("   ℹ️  No active rounds found")
    return None

def test_timer_pages():
    """Test timer-related pages"""
    print("\n📄 Testing timer-related pages...")
    
    pages = [
        ("/test_bulk_timer", "Test bulk timer debug page"),
        ("/", "Main dashboard"),
    ]
    
    for endpoint, description in pages:
        test_endpoint(endpoint, description)

def run_comprehensive_test():
    """Run comprehensive timer tests"""
    print("🚀 Starting Timer Functionality Tests")
    print("=" * 50)
    
    # Test basic connectivity
    print("\n1. Testing basic connectivity...")
    result = test_endpoint("/", "Main page")
    if not result:
        print("❌ Cannot connect to Flask app. Make sure it's running on http://127.0.0.1:5000")
        return
    
    # Test timer pages
    print("\n2. Testing timer pages...")
    test_timer_pages()
    
    # Test bulk round status
    print("\n3. Testing bulk round status...")
    active_bulk_id = test_bulk_round_status()
    
    # Test regular round status
    print("\n4. Testing round status...")
    active_round_id = test_round_status()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 TEST SUMMARY:")
    print(f"   Active Bulk Round: {active_bulk_id if active_bulk_id else 'None found'}")
    print(f"   Active Round: {active_round_id if active_round_id else 'None found'}")
    
    if active_bulk_id or active_round_id:
        print("   ✅ Timer endpoints are working")
    else:
        print("   ⚠️  No active timers found - create a round to test fully")
    
    print("\n✨ Timer standardization test complete!")

if __name__ == "__main__":
    run_comprehensive_test()
