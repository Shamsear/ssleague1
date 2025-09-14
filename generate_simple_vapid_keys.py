#!/usr/bin/env python3
"""
Simple VAPID Key Generation Script using pywebpush
Generates VAPID keys in the correct format for push notifications
"""

try:
    from py_vapid import Vapid
    import base64
    
    print("🔑 Generating VAPID keys using py_vapid...")
    print("=" * 60)
    
    # Generate VAPID key pair using py_vapid
    vapid = Vapid()
    vapid.generate_keys()
    
    # Get the keys using py_vapid's built-in methods
    private_key_str = vapid.private_key_str()
    public_key_str = vapid.public_key_str()
    
    vapid_keys = {
        'private_key': private_key_str,
        'public_key': public_key_str
    }
    
    print("✅ VAPID keys generated successfully!")
    print()
    print("📋 Environment Variables (copy to your .env file):")
    print("=" * 60)
    print(f"VAPID_PRIVATE_KEY={vapid_keys['private_key']}")
    print(f"VAPID_PUBLIC_KEY={vapid_keys['public_key']}")
    print(f"VAPID_CLAIMS_SUB=mailto:toses16742@merumart.com")
    print("=" * 60)
    print()
    print("📝 Key Details:")
    print(f"✓ Private Key: {len(vapid_keys['private_key'])} characters")
    print(f"✓ Public Key: {len(vapid_keys['public_key'])} characters")
    print(f"✓ Format: Base64URL encoded")
    print(f"✓ Algorithm: ECDSA P-256")
    print()
    print("🚀 Next Steps:")
    print("1. Copy the environment variables above")
    print("2. Set them in your deployment environment (Render, Heroku, etc.)")
    print("3. Restart your application")
    print("4. Test push notifications from admin settings")
    print()
    print("⚠️  Security Notes:")
    print("• Keep PRIVATE KEY secret - never commit to git")
    print("• PUBLIC KEY can be used in client-side JavaScript")
    print("• These keys are specific to your application")
    
except ImportError:
    print("❌ Error: py_vapid not installed")
    print("Run: pip install py_vapid")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure py_vapid is properly installed")
