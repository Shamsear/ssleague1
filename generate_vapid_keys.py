"""
Utility script to generate VAPID keys for web push notifications.
Run this script once to generate a key pair, then save them in environment variables.
"""

from pywebpush import webpush, WebPushException
import os
import base64
import json

def generate_vapid_keys():
    """Generate VAPID key pair for web push notifications."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    
    # Generate a new EC key pair
    private_key = ec.generate_private_key(ec.SECP256R1())
    
    # Get the public key in PKCS8 format
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Get the private key in PKCS8 format
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Convert the keys to base64
    public_key_b64 = base64.urlsafe_b64encode(public_key).decode("utf-8").rstrip("=")
    private_key_b64 = base64.urlsafe_b64encode(pem).decode("utf-8").rstrip("=")
    
    return {
        "public_key": public_key_b64,
        "private_key": private_key_b64
    }

if __name__ == "__main__":
    keys = generate_vapid_keys()
    
    # Print the keys
    print("\n===== VAPID Keys for Web Push Notifications =====\n")
    print(f"Public Key: {keys['public_key']}")
    print(f"Private Key: {keys['private_key']}")
    print("\n===== Store these keys securely =====\n")
    print("Add to .env file:")
    print(f"VAPID_PUBLIC_KEY={keys['public_key']}")
    print(f"VAPID_PRIVATE_KEY={keys['private_key']}")
    print("VAPID_CONTACT_EMAIL=admin@example.com")  # Replace with your email
    
    # Save to a file for backup
    try:
        with open("vapid_keys.json", "w") as f:
            json.dump(keys, f, indent=2)
        print("\nKeys also saved to vapid_keys.json - KEEP THIS FILE SECURE!")
    except Exception as e:
        print(f"Error saving keys to file: {e}") 