import secrets
import base64

# Generate a secure random key (32 bytes = 256 bits)
secret_key = secrets.token_bytes(32)

# Convert to base64 for easier storage
secret_key_b64 = base64.b64encode(secret_key).decode('utf-8')

print(f"Generated JWT_SECRET_KEY: {secret_key_b64}")
