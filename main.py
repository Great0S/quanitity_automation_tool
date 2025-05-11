"""
Generate JWT secret key and initialize environment
"""

import secrets
import base64
import os
from dotenv import load_dotenv, set_key

def generate_jwt_secret():
    """Generate a secure random key for JWT signing"""
    # Generate a secure random key (32 bytes = 256 bits)
    secret_key = secrets.token_bytes(32)
    
    # Convert to base64 for easier storage
    secret_key_b64 = base64.b64encode(secret_key).decode('utf-8')
    
    return secret_key_b64

def update_env_file(jwt_secret):
    """Update .env file with the JWT secret"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Load existing .env file
    load_dotenv(env_path)
    
    # Update JWT_SECRET_KEY
    set_key(env_path, 'JWT_SECRET_KEY', jwt_secret)
    
    print(f"Updated .env file with new JWT_SECRET_KEY")

def main():
    """Main function to generate and set JWT secret"""
    # Generate JWT secret
    jwt_secret = generate_jwt_secret()
    print(f"Generated JWT_SECRET_KEY: {jwt_secret}")
    
    # Ask if user wants to update .env file
    update = input("Update .env file with this key? (y/n): ")
    if update.lower() == 'y':
        update_env_file(jwt_secret)
    
    print("\nTo manually update your .env file, add this line:")
    print(f"JWT_SECRET_KEY={jwt_secret}")

if __name__ == "__main__":
    main()