from cryptography.hazmat.primitives import serialization

print("===== Encoding =====")
for attr in dir(serialization.Encoding):
    if not attr.startswith('_'):
        print(f"- {attr}")

print("\n===== PrivateFormat =====")
for attr in dir(serialization.PrivateFormat):
    if not attr.startswith('_'):
        print(f"- {attr}")

print("\n===== PublicFormat =====")
for attr in dir(serialization.PublicFormat):
    if not attr.startswith('_'):
        print(f"- {attr}")

print("\n===== Encoding values =====")
for attr in dir(serialization.Encoding):
    if not attr.startswith('_'):
        try:
            value = getattr(serialization.Encoding, attr)
            print(f"- {attr}: {value}")
        except Exception as e:
            print(f"- {attr}: Error: {e}") 