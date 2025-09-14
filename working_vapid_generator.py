#!/usr/bin/env python3
"""
Working VAPID Key Generator
Uses cryptography library directly to generate valid VAPID keys
"""

import base64
import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def generate_vapid_keys():
    """Generate VAPID keys in the correct format for pywebpush"""
    
    # Generate a new ECDSA private key using P-256 curve
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    # Get private key as DER bytes and extract the 32-byte key material
    private_key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Extract the 32-byte private key value (skip DER encoding overhead)
    private_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    
    # Get public key as uncompressed point (65 bytes: 0x04 + 32 bytes x + 32 bytes y)
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    # Remove the 0x04 prefix for VAPID format (keep only the 64 coordinate bytes)
    public_key_bytes = public_key_bytes[1:]
    
    # Convert to base64url encoding (URL-safe base64 without padding)
    private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('ascii').rstrip('=')
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('ascii').rstrip('=')
    
    return {
        'private_key': private_key_b64,
        'public_key': public_key_b64
    }

if __name__ == "__main__":
    try:
        print("🔑 Generating VAPID keys using cryptography...")
        print("=" * 60)
        
        keys = generate_vapid_keys()
        
        print("✅ VAPID keys generated successfully!")
        print()
        print("📋 Environment Variables (copy these to your deployment):")
        print("=" * 70)
        print(f"VAPID_PRIVATE_KEY={keys['private_key']}")
        print(f"VAPID_PUBLIC_KEY={keys['public_key']}")
        print(f"VAPID_CLAIMS_SUB=mailto:toses16742@merumart.com")
        print("=" * 70)
        print()
        print("📝 Key Details:")
        print(f"✓ Private Key: {len(keys['private_key'])} characters")
        print(f"✓ Public Key: {len(keys['public_key'])} characters")
        print(f"✓ Format: Base64URL encoded (RFC 4648)")
        print(f"✓ Curve: ECDSA P-256 (NIST secp256r1)")
        print(f"✓ Compatible: pywebpush library")
        print()
        print("🚀 Next Steps:")
        print("1. Copy the environment variables above")
        print("2. Set them in your deployment environment")
        print("3. Restart your application")
        print("4. Test push notifications")
        print()
        print("🔒 Security:")
        print("• Keep PRIVATE KEY secret - never share publicly")
        print("• PUBLIC KEY can be used in client JavaScript")
        print("• Both keys are unique to your application")
        
    except Exception as e:
        print(f"❌ Error generating keys: {e}")
        print("Make sure cryptography library is installed: pip install cryptography")