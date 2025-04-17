from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Generate a private key using the P-256 curve
private_key = ec.generate_private_key(ec.SECP256R1())

# Get the raw bytes of the private and public keys
private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
public_key = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Encode keys in URL-safe Base64
vapid_private_key = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('utf-8')
vapid_public_key = base64.urlsafe_b64encode(public_key).rstrip(b'=').decode('utf-8')

print("VAPID PUBLIC KEY:", vapid_public_key)
print("VAPID PRIVATE KEY:", vapid_private_key)
