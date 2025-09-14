#!/usr/bin/env python3
"""
Script to generate VAPID keys for web push notifications.
Run this script and add the generated keys to your Render environment variables.
"""

try:
    from pywebpush import webpush
    import base64
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    
    def generate_vapid_keys():
        # Generate a new private key
        private_key = ec.generate_private_key(ec.SECP256R1())
        
        # Get the public key
        public_key = private_key.public_key()
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Convert to base64 for storage
        private_key_b64 = base64.b64encode(private_pem).decode('utf-8')
        public_key_b64 = base64.b64encode(public_pem).decode('utf-8')
        
        return private_key_b64, public_key_b64
    
    if __name__ == "__main__":
        private_key, public_key = generate_vapid_keys()
        
        print("VAPID Keys Generated!")
        print("=" * 50)
        print("\nAdd these to your Render environment variables:")
        print("\nVAPID_PRIVATE_KEY:")
        print(private_key)
        print("\nVAPID_PUBLIC_KEY:")
        print(public_key)
        print("\nVAPID_CLAIMS_SUB:")
        print("mailto:admin@yourdomain.com")
        print("\n" + "=" * 50)
        print("Save these keys securely! You'll need them for your deployment.")

except ImportError as e:
    print("Error: Required packages not installed.")
    print("Please install: pip install pywebpush cryptography")
    print(f"Import error: {e}")
