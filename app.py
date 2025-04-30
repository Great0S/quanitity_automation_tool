"""
Enhanced Quantity Automation Tool
Main application file with improved workflow management and error handling
"""

import os
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import aiohttp
import pandas as pd
import plotly.express as px
import streamlit as st

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
from services.product_service import ProductService
from utils.validators import ProductValidator
from utils.formatters import DataFormatter

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
        self.clients: Dict[str, Any] = {}
        self.sync_service: Optional[SyncService] = None
        self.export_service: ExportService = ExportService()  # Initialize directly
        self.validator: ProductValidator = ProductValidator()  # Initialize directly
        self.formatter: DataFormatter = DataFormatter()  # Initialize directly
        self.date_range: tuple = (datetime.now() - timedelta(days=30), datetime.now())
        self.selected_platforms: List[str] = []
        
        # Setup components
        self.setup_streamlit()
        self.initialize_clients()

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

    def initialize_clients(self) -> None:
        """Initialize API clients with available credentials"""
        try:
            # Initialize clients dictionary
            self.clients = {}
            
            # N11
            if all([os.getenv('N11_APP_KEY'), os.getenv('N11_APP_SECRET')]):
                n11_client = N11Client()
                asyncio.run(n11_client.authenticate())
                self.clients['N11'] = ProductService(n11_client)
                self.logger.info("N11 client initialized successfully")

            # Trendyol
            if all([os.getenv('TRENDYOL_API_KEY'), os.getenv('TRENDYOL_API_SECRET')]):
                trendyol_client = TrendyolClient()
                asyncio.run(trendyol_client.authenticate())
                self.clients['Trendyol'] = ProductService(trendyol_client)
                self.logger.info("Trendyol client initialized successfully")

            # Hepsiburada
            if all([os.getenv('HEPSIBURADA_USERNAME'), os.getenv('HEPSIBURADA_PASSWORD')]):
                hepsiburada_client = HepsiburadaClient()
                asyncio.run(hepsiburada_client.authenticate())
                self.clients['Hepsiburada'] = ProductService(hepsiburada_client)
                self.logger.info("Hepsiburada client initialized successfully")

            # Pazarama
            if all([os.getenv('PAZARAMA_API_KEY'), os.getenv('PAZARAMA_SELLER_ID')]):
                pazarama_client = PazaramaClient()
                asyncio.run(pazarama_client.authenticate())
                self.clients['Pazarama'] = ProductService(pazarama_client)
                self.logger.info("Pazarama client initialized successfully")

            # PTTAVM
            if all([os.getenv('PTTAVM_USERNAME'), os.getenv('PTTAVM_PASSWORD')]):
                pttavm_client = PTTAVMClient()
                asyncio.run(pttavm_client.authenticate())
                self.clients['PTTAVM'] = ProductService(pttavm_client)
                self.logger.info("PTTAVM client initialized successfully")

            # WordPress/WooCommerce
            if all([
                os.getenv('WP_SITE_URL'),
                os.getenv('WC_CONSUMER_KEY'),
                os.getenv('WC_CONSUMER_SECRET')
            ]):
                wordpress_client = WordPressClient()
                asyncio.run(wordpress_client.authenticate())
                self.clients['WordPress'] = ProductService(wordpress_client)
                self.logger.info("WordPress client initialized successfully")

            if not self.clients:
                st.warning("No API clients were initialized. Please check your credentials.")
            else:
                st.success(f"Successfully initialized {len(self.clients)} API clients")

        except Exception as e:
            self.logger.error(f"Error initializing clients: {str(e)}")
            st.error(f"Error initializing clients: {str(e)}")

    def initialize_services(self) -> None:
        """Initialize services"""
        try:
            # Initialize validator and formatter
            self.validator = ProductValidator()
            self.formatter = DataFormatter()
            self.export_service = ExportService()
            
            # Initialize sync service with None initially
            self.sync_service = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            st.error("Failed to initialize services")

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
                    st.rerun()

    def render_platform_selector(self) -> None:
        """Render platform selection dropdown"""
        st.session_state.selected_platform = st.selectbox(
            "Select Platform",
            options=list(self.clients.keys())
        )

    def render_action_buttons(self) -> None:
        """Render action buttons"""
        if st.button("🔄 Fetch Products"):
            asyncio.run(self.fetch_products())
            
        if st.button("💾 Save Changes"):
            asyncio.run(self.save_changes())
            
        if st.button("📤 Export Data"):
            self.export_data()

    def render_settings(self) -> None:
        """Render settings section"""
        st.subheader("Settings")
        
        auto_refresh = st.checkbox(
            "Auto-refresh",
            key="auto_refresh",
            help="Automatically refresh product data"
        )
        
        if auto_refresh:
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
                    st.rerun()
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

    def render_filters(self) -> None:
        """Render filter controls"""
        with st.sidebar:
            st.subheader("Filters")
            self.date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=30), datetime.now())
            )
            self.selected_platforms = st.multiselect(
                "Platforms",
                options=list(self.clients.keys()),
                default=list(self.clients.keys())
            )

    def render_product_table(self, products: List[Dict[str, Any]]) -> None:
        """Render product data table"""
        if not products:
            st.info("No products found matching the criteria")
            return

        df = pd.DataFrame(products)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "quantity": st.column_config.NumberColumn(
                    "Quantity",
                    help="Current stock quantity",
                    format="%d"
                ),
                "price": st.column_config.NumberColumn(
                    "Price",
                    help="Current price",
                    format="%.2f"
                )
            }
        )

    def render_metrics(self, data: Dict[str, Any]) -> None:
        """Render key metrics"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", data.get("total_products", 0))
        with col2:
            st.metric("Low Stock Items", data.get("low_stock", 0))
        with col3:
            st.metric("Out of Stock", data.get("out_of_stock", 0))
        with col4:
            st.metric("Active Listings", data.get("active_listings", 0))

    def render_charts(self, data: Dict[str, Any]) -> None:
        """Render analytics charts"""
        col1, col2 = st.columns(2)
        
        with col1:
            if data.get("stock_distribution"):
                fig = px.pie(
                    data["stock_distribution"],
                    values="count",
                    names="category",
                    title="Stock Level Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if data.get("platform_stats"):
                fig = px.bar(
                    data["platform_stats"],
                    x="platform",
                    y="products",
                    title="Products by Platform"
                )
                st.plotly_chart(fig, use_container_width=True)

    def render_products_tab(self) -> None:
        """Render products tab content"""
        platform = st.session_state.selected_platform
        products = st.session_state.products.get(platform, [])
        
        if not products:
            st.info("No products loaded. Please fetch products from a platform.")
            return
            
        with st.expander("Filters"):
            self.render_filters()
            
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
            asyncio.run(self.start_sync(source, target))

    def render_analytics_tab(self) -> None:
        """Render analytics tab content"""
        st.subheader("Analytics")
        
        platform = st.session_state.selected_platform
        products = st.session_state.products.get(platform, [])
        
        if not products:
            st.info("No data available. Please fetch products first.")
            return
            
        self.render_metrics(self.calculate_metrics(products))
        self.render_charts(self.calculate_charts_data(products))

    def calculate_metrics(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics from products data"""
        return {
            "total_products": len(products),
            "low_stock": sum(1 for p in products if p.get("quantity", 0) < 10),
            "out_of_stock": sum(1 for p in products if p.get("quantity", 0) == 0),
            "active_listings": sum(1 for p in products if p.get("status") == "active")
        }

    def calculate_charts_data(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data for charts"""
        stock_distribution = pd.DataFrame([
            {"category": "Out of Stock", "count": sum(1 for p in products if p.get("quantity", 0) == 0)},
            {"category": "Low Stock", "count": sum(1 for p in products if 0 < p.get("quantity", 0) < 10)},
            {"category": "In Stock", "count": sum(1 for p in products if p.get("quantity", 0) >= 10)}
        ])
        
        return {
            "stock_distribution": stock_distribution,
            "platform_stats": pd.DataFrame(self.clients.keys(), columns=["platform"])
        }

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

    async def start_sync(self, source: str, target: str) -> None:
        """Start product synchronization"""
        try:
            if source == target:
                st.warning("Source and target platforms must be different")
                return
                
            with st.spinner("Synchronizing products..."):
                source_client = self.clients[source]
                target_client = self.clients[target]
                
                # Validate that both clients implement ProductService
                if not isinstance(source_client, ProductService) or not isinstance(target_client, ProductService):
                    raise ValueError("Both source and target must implement ProductService")
                
                # Create SyncService instance with the actual services
                sync_service = SyncService(
                    source_service=source_client,
                    target_service=target_client
                )
                
                # Fetch products from source
                products = await source_client.get_products()
                
                # Perform sync
                result = await sync_service.sync_products(products)
                
                st.success(
                    f"Sync completed: {result['successful']} successful, "
                    f"{result['failed']} failed"
                )
                
        except ValueError as ve:
            self.logger.error(f"Invalid service configuration: {str(ve)}")
            st.error(str(ve))
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            st.error(f"Sync failed: {str(e)}")

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

if __name__ == "__main__":
    app = ECommerceManager()
    app.run()

