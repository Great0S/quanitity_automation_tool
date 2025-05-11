# pages/auth.py
import streamlit as st
import os
from auth.simple_auth import SimpleAuthManager
from core.exceptions import AuthenticationError

def show_login_page():
    st.title("Login")
    
    # Initialize auth manager
    auth_manager = SimpleAuthManager()
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:  # Login tab
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    auth_result = auth_manager.login(username, password)
                    # Store tokens in session state
                    st.session_state.access_token = auth_result['AccessToken']
                    st.session_state.refresh_token = auth_result['RefreshToken']
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()  # Refresh page to show main application
                except AuthenticationError as e:
                    st.error(f"Login failed: {str(e)}")
    
    with tab2:  # Registration tab
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                if new_password != confirm_password:
                    st.error("Passwords do not match!")
                    return
                    
                try:
                    auth_manager.create_user(new_username, new_password, new_email)
                    st.success("Registration successful! You can now login.")
                except AuthenticationError as e:
                    st.error(f"Registration failed: {str(e)}")

def show_main_app():
    """Show the main application after login"""
    st.title("Quantity Automation Tool")
    st.write(f"Welcome, {st.session_state.get('username', 'User')}!")
    
    if st.button("Logout"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def main():
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        show_login_page()
        return
        
    # Your existing application code here
    show_main_app()

if __name__ == "__main__":
    main()