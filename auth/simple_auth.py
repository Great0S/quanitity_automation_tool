"""
Simple authentication system that doesn't require AWS Cognito
"""

import os
import hashlib
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from core.exceptions import AuthenticationError
from core.logger import logger

class SimpleAuthManager:
    """Simple authentication manager using JWT tokens"""
    
    def __init__(self):
        """Initialize the auth manager with a secret key"""
        # Get secret key from environment or use a default for development
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'dev_secret_key_replace_in_production')
        
        # In a real app, you would use a database instead of this in-memory store
        # This is just for demonstration purposes
        self._users = {}
        
        # Always ensure admin user exists
        admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin')
        
        # Print debug info
        print(f"SimpleAuthManager initializing with user: {admin_username}")
        
        self._users[admin_username] = {
            "password_hash": self._hash_password(admin_password),
            "email": "admin@example.com",
            "role": "admin"
        }
        
        self.logger = logger
    
    def _hash_password(self, password: str) -> str:
        """Hash a password for storing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, stored_hash: str, provided_password: str) -> bool:
        """Verify a stored password against a provided password"""
        return stored_hash == self._hash_password(provided_password)
    
    def _generate_token(self, username: str, expiry_hours: int = 24) -> str:
        """Generate a JWT token for the user"""
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and get tokens"""
        try:
            # Print debug info
            print(f"Login attempt for user: {username}")
            print(f"Available users: {list(self._users.keys())}")
            
            if username not in self._users:
                raise AuthenticationError("Invalid username or password")
                
            user = self._users[username]
            if not self._verify_password(user["password_hash"], password):
                raise AuthenticationError("Invalid username or password")
                
            # Generate tokens
            access_token = self._generate_token(username, expiry_hours=24)
            refresh_token = self._generate_token(username, expiry_hours=720)  # 30 days
            
            self.logger.info(f"User logged in: {username}")
            
            return {
                'AccessToken': access_token,
                'RefreshToken': refresh_token,
                'ExpiresIn': 86400  # 24 hours in seconds
            }
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            raise AuthenticationError(str(e))
    
    def create_user(self, username: str, password: str, email: str) -> Dict[str, Any]:
        """Create a new user"""
        try:
            if username in self._users:
                raise AuthenticationError("Username already exists")
                
            # Store the new user
            self._users[username] = {
                "password_hash": self._hash_password(password),
                "email": email,
                "role": "user"
            }
            
            self.logger.info(f"Created user: {username}")
            
            return {
                "username": username,
                "email": email
            }
            
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise AuthenticationError(str(e))
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            # Verify the refresh token
            payload = self.verify_token(refresh_token)
            username = payload.get('username')
            
            if not username or username not in self._users:
                raise AuthenticationError("Invalid refresh token")
            
            # Generate a new access token
            access_token = self._generate_token(username, expiry_hours=24)
            
            self.logger.info(f"Token refreshed for user: {username}")
            
            return {
                'AccessToken': access_token,
                'ExpiresIn': 86400  # 24 hours in seconds
            }
            
        except Exception as e:
            self.logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(str(e))