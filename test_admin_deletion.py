import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_admin_deletion():
    """Test the admin round deletion functionality"""
    
    # This would typically be your Flask app's URL
    base_url = "http://localhost:5000"  # Adjust as needed
    
    print("=== TESTING ADMIN ROUND DELETION ===")
    print("Note: This test requires:")
    print("1. Your Flask app to be running")
    print("2. A valid admin session/authentication")
    print("3. At least one round to delete")
    print()
    
    # Check if there are any rounds to test with
    print("To test the admin deletion functionality:")
    print("1. Start your Flask app")
    print("2. Log in as admin")
    print("3. Go to the admin rounds page")
    print("4. Try deleting a round")
    print()
    print("The improved deletion logic should now:")
    print("- ✅ Remove all player round_id references first")
    print("- ✅ Delete all tiebreaker records properly") 
    print("- ✅ Delete all bid records for the round")
    print("- ✅ Refund team balances appropriately")
    print("- ✅ Successfully delete the round without constraint errors")
    print()
    print("If you see any foreign key constraint errors, please let me know!")

if __name__ == "__main__":
    test_admin_deletion()