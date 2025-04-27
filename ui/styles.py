import streamlit as st

def apply_custom_styles():
    """Apply custom CSS styles"""
    st.markdown("""
        <style>
            /* Main Layout */
            .main {
                padding: 1rem;
            }
            
            /* Header */
            .header {
                padding: 2rem 0;
                text-align: center;
                background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
                border-radius: 10px;
                margin-bottom: 2rem;
            }
            
            .header h1 {
                color: #1a1a1a;
                margin-bottom: 0.5rem;
                font-size: 2.5rem;
            }
            
            .subtitle {
                color: #666;
                font-size: 1.1rem;
            }
            
            /* Navigation */
            .stRadio > label {
                font-weight: 600;
                color: #1a1a1a;
            }
            
            /* Forms */
            .stForm {
                background: #fff;
                padding: 1.5rem;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .stTextInput > div > div > input,
            .stNumberInput > div > div > input,
            .stTextArea > div > div > textarea {
                border-radius: 5px;
                border: 1px solid #ddd;
                padding: 0.5rem;
            }
            
            .stTextInput > div > div > input:focus,
            .stNumberInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus {
                border-color: #80bdff;
                box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
            }
            
            /* Buttons */
            .stButton > button {
                width: 100%;
                border-radius: 5px;
                padding: 0.5rem 1rem;
                font-weight: 600;
                transition: all 0.2s;
            }
            
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            /* Tables */
            .dataframe {
                border: none;
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                font-family: sans-serif;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            }
            
            .dataframe thead tr {
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }
            
            .dataframe th,
            .dataframe td {
                padding: 12px 15px;
            }
            
            .dataframe tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            
            .dataframe tbody tr:nth-of-type(even) {
                background-color: #f3f3f3;
            }
            
            .dataframe tbody tr:last-of-type {
                border-bottom: 2px solid #009879;
            }
            
            /* Status Component */
            .metric-container {
                background: #fff;
                padding: 1rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: 600;
                color: #1a1a1a;
            }
            
            .metric-label {
                color: #666;
                font-size: 0.9rem;
            }
            
            /* Notifications */
            .stAlert {
                border-radius: 8px;
                margin: 1rem 0;
            }
            
            /* Dark Mode */
            @media (prefers-color-scheme: dark) {
                .header {
                    background: linear-gradient(90deg, #1a1a1a 0%, #2d3436 100%);
                }
                
                .header h1 {
                    color: #fff;
                }
                
                .subtitle {
                    color: #ddd;
                }
                
                .stForm {
                    background: #2d3436;
                }
                
                .metric-container {
                    background: #2d3436;
                }
                
                .metric-value {
                    color: #fff;
                }
                
                .metric-label {
                    color: #ddd;
                }
            }
        </style>
    """, unsafe_allow_html=True)

def apply_theme():
    """Apply custom theme settings"""
    st.set_page_config(
        page_title="E-Commerce Product Manager",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
