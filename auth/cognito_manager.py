# auth/cognito_manager.py
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
import hmac
import hashlib
import base64
from core.exceptions import AuthenticationError
from core.logger import logger


class CognitoManager:
    def __init__(self):
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET')

        if not all([self.user_pool_id, self.client_id, self.client_secret]):
            raise AuthenticationError("Missing Cognito credentials")

        self.client = boto3.client('cognito-idp')

    def refresh_token(self, refresh_token: str, username: str) -> Dict[str, Any]:
        """Refresh access token using refresh token and username"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                    'SECRET_HASH': self._get_secret_hash(username)
                }
            )
            logger.info("Token refreshed successfully")
            return response['AuthenticationResult']
        except ClientError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(str(e))

        # Default return to satisfy all code paths
        return {}


    def forgot_password(self, username: str) -> Dict[str, Any]:
        """Initiate forgot password flow"""
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username
            )
            logger.info(f"Forgot password initiated for user: {username}")
            return response
        except ClientError as e:
            logger.error(f"Forgot password failed: {str(e)}")
            raise AuthenticationError(str(e))
    
    
    def confirm_forgot_password(self, username: str, password: str, confirmation_code: str) -> Dict[str, Any]:
        """Confirm new password with confirmation code"""
        try:
            response = self.client.confirm_forgot_password(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username,
                Password=password,
                ConfirmationCode=confirmation_code
            )
            logger.info(f"Password reset completed for user: {username}")
            return response
        except ClientError as e:
            logger.error(f"Password reset failed: {str(e)}")
            raise AuthenticationError(str(e))
    
    
    def create_user(self, username: str, password: str, email: str) -> Dict[str, Any]:
        """Create a new user in Cognito"""
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email}
                ]
            )
            logger.info(f"Created user: {username}")
            return response
        except ClientError as e:
            logger.error(f"Error creating user: {str(e)}")
            raise AuthenticationError(str(e))
    
    
    def confirm_user(self, username: str, confirmation_code: str) -> Dict[str, Any]:
        """Confirm user registration"""
        try:
            response = self.client.confirm_sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username,
                ConfirmationCode=confirmation_code
            )
            logger.info(f"Confirmed user: {username}")
            return response
        except ClientError as e:
            logger.error(f"Error confirming user: {str(e)}")
            raise AuthenticationError(str(e))
    
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and get tokens"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': self._get_secret_hash(username)
                }
            )
            logger.info(f"User logged in: {username}")
            return response['AuthenticationResult']
        except ClientError as e:
            logger.error(f"Login failed: {str(e)}")
            raise AuthenticationError(str(e))
        
    def _get_secret_hash(self, username: str) -> str:
        """Calculate secret hash for Cognito API calls"""
        msg = f"{username}{self.client_id}"
        dig = hmac.new(
            str(self.client_secret).encode('utf-8'),
            msg=str(msg).encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()
    