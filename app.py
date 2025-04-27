"""
Enhanced Quantity Automation Tool
Main application file with improved workflow management and error handling
"""

import os
import asyncio
import streamlit as st
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError
from api.n11_client import N11Client
from api.trendyol_client import TrendyolClient
from api.hepsiburada_client import HepsiburadaClient
from api.pazarama_client import PazaramaClient
from api.pttavm_client import PTTAVMClient
from api.wordpress_client import WordPressClient
from services.sync_service import SyncService
from services.export_service import ExportService
from utils.validators import ProductValidator
from utils.formatters import DataFormatter

# Set page config at the very beginning
st.set_page_config(
    page_title="Quantity Automation Tool",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)


class ECommerceManager:
    """Main application class for Quantity Automation Tool"""
    
    def __init__(self):
        # Initialize logger first
        self.logger = logger

        """Initialize application components"""
        self.setup_streamlit()
        self.initialize_clients()
        self.initialize_services()

    def setup_streamlit(self) -> None:
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'products' not in st.session_state:
            st.session_state.products = {}
        if 'selected_platform' not in st.session_state:
            st.session_state.selected_platform = None

    def initialize_clients(self) -> None:
        """Initialize API clients"""
        try:
            self.clients = {
                'N11': N11Client(),
                'Trendyol': TrendyolClient(),
                'Hepsiburada': HepsiburadaClient(),
                'Pazarama': PazaramaClient(),
                'PTTAVM': PTTAVMClient(),
                'WordPress': WordPressClient()
            }
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {str(e)}")
            st.error("Failed to initialize API clients. Please check your credentials.")

    def initialize_services(self) -> None:
        """Initialize services"""
        # Initialize validator and formatter first
        self.validator = ProductValidator()
        self.formatter = DataFormatter()
        self.export_service = ExportService()

        # Initialize sync service with None initially
        # We'll set the source and target services when needed
        self.sync_service = None

    async def start_sync(self, source: str, target: str) -> None:
        """Start product synchronization"""
        try:
            if source == target:
                st.warning("Source and target platforms must be different")
                return
                
            with st.spinner("Synchronizing products..."):
                source_client = self.clients[source]
                target_client = self.clients[target]
                
                # Create a new SyncService instance for this specific sync operation
                sync_service = SyncService(
                    source_service=source_client,
                    target_service=target_client
                )
                
                result = await sync_service.sync_products(
                    await source_client.get_products()  # Pass the actual products to sync
                )
                
                st.success(
                    f"Sync completed: {result['successful']} successful, "
                    f"{result['failed']} failed"
                )
                
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            st.error(f"Sync failed: {str(e)}")

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
            st.error("An unexpected error occurred. Please check the logs for details.")

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
                    st.experimental_rerun()

    def render_platform_selector(self) -> None:
        """Render platform selection dropdown"""
        st.session_state.selected_platform = st.selectbox(
            "Select Platform",
            options=list(self.clients.keys())
        )

    def render_action_buttons(self) -> None:
        """Render action buttons"""
        if st.button("🔄 Fetch Products"):
            self.fetch_products()
            
        if st.button("💾 Save Changes"):
            self.save_changes()
            
        if st.button("📤 Export Data"):
            self.export_data()

    def render_settings(self) -> None:
        """Render settings section"""
        st.subheader("Settings")
        
        st.checkbox(
            "Auto-refresh",
            key="auto_refresh",
            help="Automatically refresh product data"
        )
        
        if st.session_state.get("auto_refresh"):
            st.number_input(
                "Refresh Interval (seconds)",
                min_value=30,
                value=300,
                key="refresh_interval"
            )

    def render_login(self) -> None:
        """Render login form"""
        st.title("Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                # Implement your authentication logic here
                if username == "admin" and password == "admin":
                    st.session_state.authenticated = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")

    def render_main_interface(self) -> None:
        """Render main interface"""
        st.title("Quantity Automation Tool")
        
        # Create tabs
        tabs = st.tabs(["Products", "Sync", "Analytics"])
        
        with tabs[0]:
            self.render_products_tab()
            
        with tabs[1]:
            self.render_sync_tab()
            
        with tabs[2]:
            self.render_analytics_tab()

    async def fetch_products(self) -> None:
        """Fetch products from selected platform"""
        try:
            platform = st.session_state.selected_platform
            if not platform:
                st.warning("Please select a platform")
                return
                
            with st.spinner(f"Fetching products from {platform}..."):
                client = self.clients[platform]
                products = await client.get_products()
                
                st.session_state.products[platform] = products
                self.logger.info(f"Fetched {len(products)} products from {platform}")
                
                st.success(f"Successfully fetched {len(products)} products")
                
        except Exception as e:
            self.logger.error(f"Failed to fetch products: {str(e)}")
            st.error(f"Failed to fetch products: {str(e)}")

    async def save_changes(self) -> None:
        """Save product changes"""
        try:
            platform = st.session_state.selected_platform
            if not platform:
                st.warning("Please select a platform")
                return
                
            changes = st.session_state.get('changes', [])
            if not changes:
                st.info("No changes to save")
                return
                
            with st.spinner("Saving changes..."):
                client = self.clients[platform]
                
                success = 0
                failed = 0
                
                for product in changes:
                    try:
                        await client.update_product(product)
                        success += 1
                    except Exception as e:
                        self.logger.error(f"Failed to update product {product['sku']}: {str(e)}")
                        failed += 1
                
                st.success(f"Successfully updated {success} products ({failed} failed)")
                
        except Exception as e:
            self.logger.error(f"Failed to save changes: {str(e)}")
            st.error(f"Failed to save changes: {str(e)}")

    def export_data(self) -> None:
        """Export product data"""
        try:
            platform = st.session_state.selected_platform
            if not platform:
                st.warning("Please select a platform")
                return
                
            products = st.session_state.products.get(platform, [])
            if not products:
                st.warning("No products to export")
                return
                
            format = st.selectbox(
                "Export Format",
                options=["CSV", "Excel", "JSON"]
            )
            
            data = self.export_service.export_data(products, format.lower())
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{platform}_products_{timestamp}.{format.lower()}"
            
            # Offer download
            st.download_button(
                label="Download Export",
                data=data,
                file_name=filename,
                mime=self.export_service.get_mime_type(format.lower())
            )
            
        except Exception as e:
            self.logger.error(f"Failed to export data: {str(e)}")
            st.error(f"Failed to export data: {str(e)}")

    def render_products_tab(self) -> None:
        """Render products tab content"""
        platform = st.session_state.selected_platform
        products = st.session_state.products.get(platform, [])
        
        if not products:
            st.info("No products loaded. Please fetch products from a platform.")
            return
            
        # Render filters
        with st.expander("Filters"):
            self.render_filters()
            
        # Render product table
        self.render_product_table(products)

    def render_sync_tab(self) -> None:
        """Render sync tab content"""
        st.subheader("Product Synchronization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            source = st.selectbox(
                "Source Platform",
                options=list(self.clients.keys()),
                key="sync_source"
            )
            
        with col2:
            target = st.selectbox(
                "Target Platform",
                options=list(self.clients.keys()),
                key="sync_target"
            )
            
        if st.button("Start Sync"):
            self.start_sync(source, target)

    def render_analytics_tab(self) -> None:
        """Render analytics tab content"""
        st.subheader("Analytics")
        
        platform = st.session_state.selected_platform
        products = st.session_state.products.get(platform, [])
        
        if not products:
            st.info("No data available. Please fetch products first.")
            return
            
        # Display metrics
        self.render_metrics(products)
        
        # Display charts
        self.render_charts(products)

    async def start_sync(self, source: str, target: str) -> None:
        """Start product synchronization"""
        try:
            if source == target:
                st.warning("Source and target platforms must be different")
                return
                
            with st.spinner("Synchronizing products..."):
                source_client = self.clients[source]
                target_client = self.clients[target]
                
                result = await self.sync_service.sync_products(
                    source_client,
                    target_client
                )
                
                st.success(
                    f"Sync completed: {result['successful']} successful, "
                    f"{result['failed']} failed"
                )
                
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            st.error(f"Sync failed: {str(e)}")

if __name__ == "__main__":
    app = ECommerceManager()
    app.run()
