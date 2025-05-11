"""
Simple authentication module for the API server
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pydantic import BaseModel
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours

# User model
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

# Token model
class Token(BaseModel):
    access_token: str
    token_type: str

# Token data model
class TokenData(BaseModel):
    username: Optional[str] = None

# Mock user database
users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "password123",  # In a real app, this would be hashed
        "disabled": False,
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hashed password
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password is correct, False otherwise
    """
    # In a real app, you would use a proper password hashing library
    # For example: return pwd_context.verify(plain_password, hashed_password)
    return plain_password == hashed_password

def get_user(db: Dict[str, Dict[str, Any]], username: str) -> Optional[User]:
    """
    Get user from database
    
    Args:
        db: User database
        username: Username
        
    Returns:
        User object or None if not found
    """
    if username in db:
        user_dict = db[username]
        return User(**user_dict)
    return None

def authenticate_user(db: Dict[str, Dict[str, Any]], username: str, password: str) -> Optional[User]:
    """
    Authenticate user
    
    Args:
        db: User database
        username: Username
        password: Password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, db[username]["hashed_password"]):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token data
        expires_delta: Token expiration time
        
    Returns:
        JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get current user from token
    
    Args:
        token: JWT token
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    if token_data.username is None:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user
    
    Args:
        current_user: Current user
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user