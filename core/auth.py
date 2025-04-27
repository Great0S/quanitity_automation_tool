import os
import jwt
import hashlib
import datetime
from typing import Dict, Optional, Any
from functools import wraps
import streamlit as st
from core.exceptions import AuthError

class Auth:
    def __init__(self):
        """Initialize authentication manager"""
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        if not self.secret_key:
            raise AuthError("JWT_SECRET_KEY not found in environment variables")
        
        # Initialize session state for auth
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate user with username and password
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Hash password
            hashed_password = self._hash_password(password)
            
            # Verify credentials (implement your own verification logic)
            if self._verify_credentials(username, hashed_password):
                # Generate JWT token
                token = self._generate_token({
                    'username': username,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                })
                
                # Set session state
                st.session_state.authenticated = True
                st.session_state.user = {
                    'username': username,
                    'token': token
                }
                
                return True
            return False
            
        except Exception as e:
            raise AuthError(f"Login failed: {str(e)}")

    def logout(self) -> None:
        """Log out current user"""
        st.session_state.authenticated = False
        st.session_state.user = None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        return st.session_state.get('user')

    def verify_token(self, token: str) -> bool:
        """
        Verify JWT token
        
        Args:
            token (str): JWT token
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return True
        except jwt.ExpiredSignatureError:
            raise AuthError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthError("Invalid token")

    def _generate_token(self, payload: Dict[str, Any]) -> str:
        """
        Generate JWT token
        
        Args:
            payload (Dict[str, Any]): Token payload
            
        Returns:
            str: JWT token
        """
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_credentials(self, username: str, hashed_password: str) -> bool:
        """
        Verify user credentials
        
        Args:
            username (str): Username
            hashed_password (str): Hashed password
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # Implement your own verification logic here
        # This is just a example implementation
        valid_users = {
            'admin': hashlib.sha256('admin123'.encode()).hexdigest(),
            'user': hashlib.sha256('user123'.encode()).hexdigest()
        }
        
        return (username in valid_users and 
                valid_users[username] == hashed_password)

def login_required(func):
    """
    Decorator to require authentication for routes
    
    Args:
        func: Function to wrap
        
    Returns:
        Function wrapper
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            st.error("Please log in to access this page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

class LoginManager:
    def __init__(self):
        """Initialize login manager"""
        self.auth = Auth()

    def render_login(self) -> None:
        """Render login form"""
        st.title("Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                try:
                    if self.auth.login(username, password):
                        st.success("Login successful!")
                        st.experimental_rerun()
                    else:
                        st.error("Invalid username or password")
                except AuthError as e:
                    st.error(str(e))

    def render_logout(self) -> None:
        """Render logout button"""
        if st.sidebar.button("Logout"):
            self.auth.logout()
            st.experimental_rerun()

    def render_user_info(self) -> None:
        """Render current user information"""
        user = self.auth.get_current_user()
        if user:
            st.sidebar.markdown(f"Logged in as: **{user['username']}**")

class PasswordManager:
    def __init__(self):
        """Initialize password manager"""
        self.auth = Auth()

    def change_password(self, username: str, current_password: str, 
                       new_password: str) -> bool:
        """
        Change user password
        
        Args:
            username (str): Username
            current_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: True if password changed successfully, False otherwise
        """
        try:
            # Verify current password
            if not self.auth._verify_credentials(
                username, 
                self.auth._hash_password(current_password)
            ):
                raise AuthError("Current password is incorrect")
            
            # Implement password change logic here
            # This is just a placeholder
            st.success("Password changed successfully")
            return True
            
        except Exception as e:
            raise AuthError(f"Password change failed: {str(e)}")

    def reset_password(self, username: str, email: str) -> bool:
        """
        Reset user password
        
        Args:
            username (str): Username
            email (str): User email
            
        Returns:
            bool: True if password reset email sent successfully
        """
        try:
            # Implement password reset logic here
            # This is just a placeholder
            st.info("Password reset instructions sent to your email")
            return True
            
        except Exception as e:
            raise AuthError(f"Password reset failed: {str(e)}")

    def render_change_password_form(self) -> None:
        """Render change password form"""
        st.subheader("Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input(
                "Current Password",
                type="password"
            )
            new_password = st.text_input(
                "New Password",
                type="password"
            )
            confirm_password = st.text_input(
                "Confirm New Password",
                type="password"
            )
            submitted = st.form_submit_button("Change Password")
            
            if submitted:
                if new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    try:
                        user = self.auth.get_current_user()
                        if user and self.change_password(
                            user['username'],
                            current_password,
                            new_password
                        ):
                            st.success("Password changed successfully")
                    except AuthError as e:
                        st.error(str(e))

    def render_reset_password_form(self) -> None:
        """Render reset password form"""
        st.subheader("Reset Password")
        
        with st.form("reset_password_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Reset Password")
            
            if submitted:
                try:
                    if self.reset_password(username, email):
                        st.info("Password reset instructions sent to your email")
                except AuthError as e:
                    st.error(str(e))

def init_auth():
    """Initialize authentication system"""
    try:
        auth = Auth()
        login_manager = LoginManager()
        
        # Handle authentication
        if not auth.is_authenticated():
            login_manager.render_login()
            st.stop()
        else:
            login_manager.render_user_info()
            login_manager.render_logout()
            
    except AuthError as e:
        st.error(f"Authentication error: {str(e)}")
        st.stop()

# Example usage in your main app:
"""
import streamlit as st
from core.auth import init_auth, login_required

# Initialize authentication
init_auth()

# Protected route
@login_required
def main():
    st.title("Protected Page")
    st.write("This content is only visible to authenticated users")

if __name__ == "__main__":
    main()
"""
