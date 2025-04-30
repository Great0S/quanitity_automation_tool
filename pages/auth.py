# pages/auth.py
import streamlit as st
from auth.cognito_manager import CognitoManager
from core.exceptions import AuthenticationError

def show_login_page():
    st.title("Login")
    
    # Initialize Cognito manager
    cognito = CognitoManager()
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:  # Login tab
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    auth_result = cognito.login(username, password)
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
                    cognito.create_user(new_username, new_password, new_email)
                    st.success("Registration successful! Please check your email for confirmation code.")
                    
                    # Show confirmation code input
                    with st.form("confirm_form"):
                        confirmation_code = st.text_input("Confirmation Code")
                        confirm_submit = st.form_submit_button("Confirm Registration")
                        
                        if confirm_submit:
                            try:
                                cognito.confirm_user(new_username, confirmation_code)
                                st.success("Email confirmed! You can now login.")
                            except AuthenticationError as e:
                                st.error(f"Confirmation failed: {str(e)}")
                                
                except AuthenticationError as e:
                    st.error(f"Registration failed: {str(e)}")

# Update your main app.py
def main():
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        show_login_page()
        return
        
    # Your existing application code here
    show_main_app()

if __name__ == "__main__":
    main()
