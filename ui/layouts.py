import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from .components import (
    HeaderComponent,
    NavigationComponent,
    FilterComponent,
    ProductFormComponent,
    BulkActionsComponent,
    StatusComponent,
    NotificationComponent
)
from .styles import apply_custom_styles

class MainLayout:
    def __init__(self):
        self.header = HeaderComponent()
        self.navigation = NavigationComponent()
        self.filters = FilterComponent()
        self.product_form = ProductFormComponent()
        self.bulk_actions = BulkActionsComponent()
        self.status = StatusComponent()
        self.notification = NotificationComponent()
        apply_custom_styles()

    def render(self):
        """Render main application layout"""
        # Header
        self.header.render()
        
        # Create two columns for main layout
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            self._render_main_content()
            
        with right_col:
            self._render_side_panel()
            
        # Footer status
        self._render_footer()

    def _render_main_content(self):
        """Render main content area"""
        # Navigation tabs
        tabs = st.tabs(["Products", "Sync", "Analytics"])
        
        with tabs[0]:
            self._render_products_tab()
            
        with tabs[1]:
            self._render_sync_tab()
            
        with tabs[2]:
            self._render_analytics_tab()

    def _render_products_tab(self):
        """Render products tab content"""
        # Filters
        with st.expander("Filters", expanded=False):
            self.filters.render(
                categories=st.session_state.get('categories', []),
                statuses=st.session_state.get('statuses', [])
            )
        
        # Bulk Actions
        self.bulk_actions.render()
        
        # Products Table
        if st.session_state.get('fetched_data'):
            st.dataframe(
                st.session_state.fetched_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No products loaded. Please fetch products from a platform.")

    def _render_sync_tab(self):
        """Render sync tab content"""
        st.subheader("Product Synchronization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            source = st.selectbox(
                "Source Platform",
                ["N11", "Trendyol", "Amazon"],
                key="sync_source"
            )
            
        with col2:
            target = st.selectbox(
                "Target Platform",
                ["N11", "Trendyol", "Amazon"],
                key="sync_target"
            )
            
        if st.button("Start Sync"):
            st.session_state.action = "sync"

    def _render_analytics_tab(self):
        """Render analytics tab content"""
        st.subheader("Analytics")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", st.session_state.get('total_products', 0))
        with col2:
            st.metric("Active Products", st.session_state.get('active_products', 0))
        with col3:
            st.metric("Out of Stock", st.session_state.get('out_of_stock', 0))
        with col4:
            st.metric("Last Sync", st.session_state.get('last_sync', 'Never'))

    def _render_side_panel(self):
        """Render side panel"""
        with st.sidebar:
            st.subheader("Controls")
            
            # Platform Selection
            st.selectbox(
                "Platform",
                ["N11", "Trendyol", "Amazon"],
                key="selected_platform"
            )
            
            # Actions
            if st.button("🔄 Fetch Products"):
                st.session_state.action = "fetch"
                
            if st.button("💾 Save Changes"):
                st.session_state.action = "save"
                
            if st.button("📤 Export"):
                st.session_state.action = "export"
            
            # Settings
            st.subheader("Settings")
            st.checkbox("Auto-refresh", key="auto_refresh")
            if st.session_state.get("auto_refresh"):
                st.number_input(
                    "Refresh Interval (seconds)",
                    min_value=5,
                    value=30,
                    key="refresh_interval"
                )

    def _render_footer(self):
        """Render footer with status information"""
        self.status.render({
            'total_products': len(st.session_state.get('fetched_data', [])),
            'out_of_stock': sum(
                1 for p in st.session_state.get('fetched_data', [])
                if p.get('data', {}).get('quantity', 0) == 0
            ),
            'last_sync': st.session_state.get('last_sync')
        })
