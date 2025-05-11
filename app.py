"""
Enhanced Quantity Automation Tool
Main application file with improved workflow management and error handling
"""

import os
import asyncio
import base64
import ssl
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix SSL certificate issues on macOS
if os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true':
    # This is insecure and should only be used for development
    ssl._create_default_https_context = ssl._create_unverified_context
    print("WARNING: SSL certificate verification is disabled. This is insecure!")

import pandas as pd
import streamlit as st

from core.logger import logger
from core.exceptions import (
    AuthenticationError, 
    NetworkError, 
    RateLimitError
)
from api.n11_client import N11Client
from api.trendyol_client import TrendyolClient
from api.hepsiburada_client import HepsiburadaClient
from api.pazarama_client import PazaramaClient
from api.pttavm_client import PTTAVMClient
from api.wordpress_client import WordPressClient
from services.sync_service import SyncService
from services.export_service import ExportService
from services.product_service import ProductService
from utils.validators import ProductValidator
from utils.formatters import DataFormatter
from utils.helpers import retry_async, create_excel_report

# Set page config at the very beginning
st.set_page_config(
    page_title="Ecommerce Management Tool",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ECommerceManager:
    """Main application class for Quantity Automation Tool"""
    
    def __init__(self):
        """Initialize application components"""
        # Initialize logger first
        self.logger = logger
        
        # Initialize instance variables
        self.clients: Dict[str, ProductService] = {}
        self.sync_service: Optional[SyncService] = None
        self.export_service: ExportService = ExportService()
        self.validator: ProductValidator = ProductValidator()
        self.formatter: DataFormatter = DataFormatter()
        self.date_range: Tuple[datetime, datetime] = (datetime.now() - timedelta(days=30), datetime.now())
        self.selected_platforms: List[str] = []
        self.initialization_errors: Dict[str, str] = {}
        
        # Setup components
        self.setup_streamlit()
        self.initialize_clients()
        self.initialize_services()

    def setup_streamlit(self) -> None:
        """Initialize Streamlit session state"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'products' not in st.session_state:
            st.session_state.products = {}
        if 'selected_platform' not in st.session_state:
            st.session_state.selected_platform = None
        if 'changes' not in st.session_state:
            st.session_state.changes = []
        if 'sync_status' not in st.session_state:
            st.session_state.sync_status = None
        if 'error_messages' not in st.session_state:
            st.session_state.error_messages = []
        if 'success_messages' not in st.session_state:
            st.session_state.success_messages = []

    def initialize_clients(self) -> None:
        """Initialize API clients with available credentials"""
        try:
            # Initialize clients dictionary
            self.clients = {}
            self.initialization_errors = {}
            
            # N11
            if all([os.getenv('N11_APP_KEY'), os.getenv('N11_APP_SECRET')]):
                try:
                    n11_client = N11Client()
                    asyncio.run(n11_client.authenticate())
                    self.clients['N11'] = ProductService(n11_client)
                    self.logger.info("N11 client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"N11 authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['N11'] = error_msg
                except NetworkError as e:
                    error_msg = f"N11 network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['N11'] = error_msg
                except RateLimitError as e:
                    error_msg = f"N11 rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['N11'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize N11 client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['N11'] = error_msg

            # Trendyol
            if all([os.getenv('TRENDYOL_API_KEY'), os.getenv('TRENDYOL_API_SECRET')]):
                try:
                    trendyol_client = TrendyolClient()
                    asyncio.run(trendyol_client.authenticate())
                    self.clients['Trendyol'] = ProductService(trendyol_client)
                    self.logger.info("Trendyol client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"Trendyol authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Trendyol'] = error_msg
                except NetworkError as e:
                    error_msg = f"Trendyol network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Trendyol'] = error_msg
                except RateLimitError as e:
                    error_msg = f"Trendyol rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Trendyol'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize Trendyol client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Trendyol'] = error_msg

            # Hepsiburada
            if all([os.getenv('HEPSIBURADA_USERNAME'), os.getenv('HEPSIBURADA_PASSWORD')]):
                try:
                    hepsiburada_client = HepsiburadaClient()
                    asyncio.run(hepsiburada_client.authenticate())
                    self.clients['Hepsiburada'] = ProductService(hepsiburada_client)
                    self.logger.info("Hepsiburada client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"Hepsiburada authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Hepsiburada'] = error_msg
                except NetworkError as e:
                    error_msg = f"Hepsiburada network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Hepsiburada'] = error_msg
                except RateLimitError as e:
                    error_msg = f"Hepsiburada rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Hepsiburada'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize Hepsiburada client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Hepsiburada'] = error_msg

            # Pazarama
            if all([os.getenv('PAZARAMA_API_KEY'), os.getenv('PAZARAMA_SELLER_ID')]):
                try:
                    pazarama_client = PazaramaClient()
                    asyncio.run(pazarama_client.authenticate())
                    self.clients['Pazarama'] = ProductService(pazarama_client)
                    self.logger.info("Pazarama client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"Pazarama authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Pazarama'] = error_msg
                except NetworkError as e:
                    error_msg = f"Pazarama network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Pazarama'] = error_msg
                except RateLimitError as e:
                    error_msg = f"Pazarama rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Pazarama'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize Pazarama client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['Pazarama'] = error_msg

            # PTTAVM
            if all([os.getenv('PTTAVM_USERNAME'), os.getenv('PTTAVM_PASSWORD')]):
                try:
                    pttavm_client = PTTAVMClient()
                    asyncio.run(pttavm_client.authenticate())
                    self.clients['PTTAVM'] = ProductService(pttavm_client)
                    self.logger.info("PTTAVM client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"PTTAVM authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['PTTAVM'] = error_msg
                except NetworkError as e:
                    error_msg = f"PTTAVM network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['PTTAVM'] = error_msg
                except RateLimitError as e:
                    error_msg = f"PTTAVM rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['PTTAVM'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize PTTAVM client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['PTTAVM'] = error_msg

            # WordPress/WooCommerce
            if all([
                os.getenv('WP_SITE_URL'),
                os.getenv('WC_CONSUMER_KEY'),
                os.getenv('WC_CONSUMER_SECRET')
            ]):
                try:
                    wordpress_client = WordPressClient()
                    asyncio.run(wordpress_client.authenticate())
                    self.clients['WordPress'] = ProductService(wordpress_client)
                    self.logger.info("WordPress client initialized successfully")
                except AuthenticationError as e:
                    error_msg = f"WordPress authentication failed: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['WordPress'] = error_msg
                except NetworkError as e:
                    error_msg = f"WordPress network error: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['WordPress'] = error_msg
                except RateLimitError as e:
                    error_msg = f"WordPress rate limit exceeded: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['WordPress'] = error_msg
                except Exception as e:
                    error_msg = f"Failed to initialize WordPress client: {str(e)}"
                    self.logger.error(error_msg)
                    self.initialization_errors['WordPress'] = error_msg

            # Display initialization results
            if not self.clients:
                st.warning("No API clients were initialized. Please check your credentials.")
            else:
                st.success(f"Successfully initialized {len(self.clients)} API clients")
                
            # Display initialization errors if any
            if self.initialization_errors:
                with st.expander("Initialization Errors", expanded=True):
                    for platform, error in self.initialization_errors.items():
                        st.error(f"{platform}: {error}")

        except Exception as e:
            self.logger.error(f"Error initializing clients: {str(e)}")
            st.error(f"Error initializing clients: {str(e)}")

    def initialize_services(self) -> None:
        """Initialize services"""
        try:
            # Initialize export service
            self.export_service = ExportService()
            
            # Initialize sync service if we have at least one client
            if self.clients:
                # We'll initialize the sync service when needed with specific source and targets
                self.logger.info("Services initialized successfully")
            else:
                self.logger.warning("No services initialized due to missing API clients")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            st.error(f"Failed to initialize services: {str(e)}")

    def run(self) -> None:
        """Run the main application"""
        try:
            self.render_sidebar()
            
            if not st.session_state.authenticated:
                self.render_login()
                return
                
            self.render_main_interface()
            
        except Exception as e:
            self.logger.error(f"Application error: {str(e)}")
            st.error(f"An unexpected error occurred: {str(e)}")
            
            # Display detailed error information in an expander
            with st.expander("Error Details"):
                st.write(f"Error Type: {type(e).__name__}")
                st.write(f"Error Message: {str(e)}")
                st.write("Please check the logs for more details.")

    def render_sidebar(self) -> None:
        """Render sidebar with controls"""
        with st.sidebar:
            st.title("Controls")
            
            if st.session_state.authenticated:
                self.render_platform_selector()
                self.render_action_buttons()
                self.render_settings()
                
                if st.button("Logout"):
                    st.session_state.authenticated = False
                    st.rerun()

    def render_platform_selector(self) -> None:
        """Render platform selection dropdown"""
        if not self.clients:
            st.warning("No platforms available. Please check your API credentials.")
            return
            
        st.session_state.selected_platform = st.selectbox(
            "Select Platform",
            options=list(self.clients.keys())
        )

    def render_action_buttons(self) -> None:
        """Render action buttons"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Fetch Products", disabled=not self.clients):
                with st.spinner("Fetching products..."):
                    asyncio.run(self.fetch_products())
        
        with col2:
            if st.button("💾 Save Changes", disabled=not self.clients or not st.session_state.changes):
                with st.spinner("Saving changes..."):
                    asyncio.run(self.save_changes())
        
        with col3:
            if st.button("📤 Export Data", disabled=not self.clients or not st.session_state.products):
                with st.spinner("Exporting data..."):
                    self.export_data()

    def render_settings(self) -> None:
        """Render settings section"""
        with st.expander("Settings"):
            # Date range selector
            st.subheader("Date Range")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=self.date_range[0])
            with col2:
                end_date = st.date_input("End Date", value=self.date_range[1])
            
            if start_date and end_date:
                if start_date > end_date:
                    st.error("Start date must be before end date")
                else:
                    self.date_range = (
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time())
                    )
            
            # Platform selection for sync
            st.subheader("Sync Settings")
            self.selected_platforms = st.multiselect(
                "Select Target Platforms for Sync",
                options=[p for p in self.clients.keys() if p != st.session_state.selected_platform],
                help="Select platforms to sync products to"
            )
            
            # Batch size for sync
            batch_size = st.slider("Batch Size", min_value=10, max_value=100, value=50, step=10,
                                help="Number of products to process in each batch")
            
            # Save settings button
            if st.button("Save Settings"):
                st.success("Settings saved successfully")

    async def fetch_products(self) -> None:
        """Fetch products from selected platform"""
        if not st.session_state.selected_platform:
            st.error("Please select a platform first")
            return
            
        platform = st.session_state.selected_platform
        
        try:
            with st.spinner(f"Fetching products from {platform}..."):
                # Get the product service for the selected platform
                product_service = self.clients.get(platform)
                if not product_service:
                    st.error(f"No client available for {platform}")
                    return
                
                # Fetch products with retry
                @retry_async(max_retries=3, delay=2.0, backoff=2.0, 
                           exceptions=(NetworkError, RateLimitError))
                async def fetch_with_retry():
                    return await product_service.get_products()
                
                products = await fetch_with_retry()
                
                # Store products in session state
                st.session_state.products[platform] = products
                
                # Display success message
                st.success(f"Successfully fetched {len(products)} products from {platform}")
                self.logger.info(f"Fetched {len(products)} products from {platform}")
                
        except AuthenticationError as e:
            error_msg = f"Authentication error: {str(e)}"
            self.logger.error(error_msg)
            st.error(error_msg)
        except NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            self.logger.error(error_msg)
            st.error(error_msg)
        except RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            self.logger.error(error_msg)
            st.error(error_msg)
        except Exception as e:
            error_msg = f"Error fetching products: {str(e)}"
            self.logger.error(error_msg)
            st.error(error_msg)

    async def save_changes(self) -> None:
        """Save changes to products"""
        if not st.session_state.changes:
            st.info("No changes to save")
            return
            
        try:
            with st.spinner("Saving changes..."):
                # Group changes by platform
                changes_by_platform = {}
                for change in st.session_state.changes:
                    platform = change.get('platform')
                    if platform not in changes_by_platform:
                        changes_by_platform[platform] = []
                    changes_by_platform[platform].append(change)
                
                # Process changes for each platform
                total_success = 0
                total_errors = 0
                
                for platform, changes in changes_by_platform.items():
                    product_service = self.clients.get(platform)
                    if not product_service:
                        st.error(f"No client available for {platform}")
                        continue
                    
                    # Prepare products for update
                    products_to_update = [
                        {'sku': change['sku'], 'data': change['data']}
                        for change in changes
                    ]
                    
                    # Update products
                    result = await product_service.update_products(products_to_update)
                    
                    # Count successes and errors
                    total_success += len(result.get('updated', []))
                    total_errors += len(result.get('errors', []))
                    
                    # Display errors if any
                    if result.get('errors'):
                        with st.expander(f"Errors for {platform}"):
                            for error in result['errors']:
                                st.error(f"SKU {error['sku']}: {error['error']}")
                
                # Clear changes if all successful
                if total_errors == 0:
                    st.session_state.changes = []
                
                # Display summary
                if total_success > 0:
                    st.success(f"Successfully updated {total_success} products")
                if total_errors > 0:
                    st.error(f"Failed to update {total_errors} products")
                
        except Exception as e:
            self.logger.error(f"Error saving changes: {str(e)}")
            st.error(f"Error saving changes: {str(e)}")

    def export_data(self) -> None:
        """Export product data"""
        if not st.session_state.products:
            st.error("No products to export")
            return
            
        try:
            with st.spinner("Exporting data..."):
                platform = st.session_state.selected_platform
                products = st.session_state.products.get(platform, [])
                
                if not products:
                    st.error(f"No products available for {platform}")
                    return
                
                # Prepare data for export
                export_data = []
                for product in products:
                    # Flatten product data
                    flat_product = {
                        'sku': product.get('sku', ''),
                        'title': product.get('data', {}).get('title', ''),
                        'price': product.get('data', {}).get('price', 0),
                        'quantity': product.get('data', {}).get('quantity', 0),
                        'category': product.get('data', {}).get('categoryName', ''),
                        'status': product.get('data', {}).get('status', '')
                    }
                    export_data.append(flat_product)
                
                # Create Excel file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"products_{platform}_{timestamp}.xlsx"
                filepath = os.path.join("exports", filename)
                
                # Ensure directory exists
                os.makedirs("exports", exist_ok=True)
                
                # Create Excel report
                create_excel_report(export_data, filepath, sheet_name=f"{platform} Products")
                
                # Provide download link
                with open(filepath, "rb") as file:
                    st.download_button(
                        label="Download Excel File",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.success(f"Data exported successfully to {filename}")
                
        except Exception as e:
            self.logger.error(f"Error exporting data: {str(e)}")
            st.error(f"Error exporting data: {str(e)}")

    def render_login(self) -> None:
        """Render login form"""
        st.title("Login")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                if self.authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with col2:
            st.info("""
            ### Welcome to the Ecommerce Management Tool
            
            This tool helps you manage products across multiple e-commerce platforms.
            
            Please login to continue.
            """)

    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user"""
        # For demo purposes, use simple authentication
        # In production, use a proper authentication system
        if username == "admin" and password == "admin":
            return True
        return False

    def render_main_interface(self) -> None:
        """Render main interface"""
        st.title("Ecommerce Management Tool")
        
        # Display any error or success messages
        self.display_messages()
        
        # Check if we have any clients
        if not self.clients:
            st.warning("No API clients were initialized. Please check your credentials.")
            return
        
        # Check if a platform is selected
        if not st.session_state.selected_platform:
            st.info("Please select a platform from the sidebar")
            return
            
        # Get selected platform
        platform = st.session_state.selected_platform
        
        # Display platform info
        st.header(f"{platform} Products")
        
        # Check if we have products for this platform
        if platform not in st.session_state.products or not st.session_state.products[platform]:
            st.info(f"No products loaded for {platform}. Click 'Fetch Products' to load them.")
            return
            
        # Display products
        self.display_products(platform)

    def display_messages(self) -> None:
        """Display error and success messages"""
        # Display error messages
        for message in st.session_state.error_messages:
            st.error(message)
        
        # Display success messages
        for message in st.session_state.success_messages:
            st.success(message)
        
        # Clear messages after displaying
        st.session_state.error_messages = []
        st.session_state.success_messages = []

    def display_products(self, platform: str) -> None:
        """Display products for selected platform"""
        products = st.session_state.products.get(platform, [])
        
        # Create a dataframe for display
        data = []
        for product in products:
            data.append({
                'SKU': product.get('sku', ''),
                'Title': product.get('data', {}).get('title', ''),
                'Price': product.get('data', {}).get('price', 0),
                'Quantity': product.get('data', {}).get('quantity', 0),
                'Category': product.get('data', {}).get('categoryName', ''),
                'Status': product.get('data', {}).get('status', '')
            })
        
        df = pd.DataFrame(data)
        
        # Add filters
        with st.expander("Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Filter by status
                statuses = ['All'] + sorted(df['Status'].unique().tolist())
                selected_status = st.selectbox("Status", statuses)
                
                if selected_status != 'All':
                    df = df[df['Status'] == selected_status]
            
            with col2:
                # Filter by category
                categories = ['All'] + sorted(df['Category'].unique().tolist())
                selected_category = st.selectbox("Category", categories)
                
                if selected_category != 'All':
                    df = df[df['Category'] == selected_category]
            
            with col3:
                # Search by SKU or title
                search_term = st.text_input("Search (SKU or Title)")
                
                if search_term:
                    df = df[
                        df['SKU'].str.contains(search_term, case=False, na=False) |
                        df['Title'].str.contains(search_term, case=False, na=False)
                    ]
        
        # Display product count
        st.write(f"Showing {len(df)} products")
        
        # Display products in a table with pagination
        page_size = 20
        total_pages = (len(df) + page_size - 1) // page_size
        
        if total_pages > 0:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, len(df))
            
            # Display page navigation
            st.write(f"Page {page} of {total_pages}")
            
            # Display products for current page
            st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)
        else:
            st.info("No products match the selected filters")

# Main entry point
if __name__ == "__main__":
    try:
        app = ECommerceManager()
        app.run()
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}", exc_info=True)
        st.error(f"Application crashed: {str(e)}")
        st.error("Please check the logs for details.")