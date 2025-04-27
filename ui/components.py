import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime

class HeaderComponent:
    def render(self):
        """Render the header component"""
        st.markdown("""
            <div class="header">
                <h1>📦 E-Commerce Product Manager</h1>
                <p class="subtitle">Manage and sync your products across multiple platforms</p>
            </div>
        """, unsafe_allow_html=True)

class NavigationComponent:
    def render(self):
        """Render the navigation component"""
        st.sidebar.markdown("### Navigation")
        return st.sidebar.radio(
            "Select Page",
            ["Dashboard", "Products", "Sync", "Settings"],
            key="navigation"
        )

class FilterComponent:
    def render(self, categories: List[str], statuses: List[str]) -> Dict[str, Any]:
        """Render filter controls"""
        with st.expander("Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                category = st.selectbox(
                    "Category",
                    ["All"] + categories,
                    key="filter_category"
                )
                
            with col2:
                status = st.selectbox(
                    "Status",
                    ["All"] + statuses,
                    key="filter_status"
                )
                
            with col3:
                price_range = st.slider(
                    "Price Range",
                    min_value=0,
                    max_value=10000,
                    value=(0, 10000),
                    key="filter_price"
                )
                
            search = st.text_input(
                "Search",
                placeholder="Search by SKU, title, or description...",
                key="filter_search"
            )
            
            return {
                "category": category,
                "status": status,
                "price_range": price_range,
                "search": search
            }

class ProductFormComponent:
    def render(self, product: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render product form"""
        with st.form("product_form"):
            st.subheader("Product Details")
            
            sku = st.text_input(
                "SKU",
                value=product.get("sku", "") if product else "",
                disabled=bool(product)
            )
            
            title = st.text_input(
                "Title",
                value=product.get("data", {}).get("title", "") if product else ""
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                price = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=float(product.get("data", {}).get("price", 0)) if product else 0.0,
                    step=0.01
                )
                
            with col2:
                quantity = st.number_input(
                    "Quantity",
                    min_value=0,
                    value=int(product.get("data", {}).get("quantity", 0)) if product else 0
                )
                
            category = st.text_input(
                "Category",
                value=product.get("data", {}).get("categoryName", "") if product else ""
            )
            
            description = st.text_area(
                "Description",
                value=product.get("data", {}).get("description", "") if product else ""
            )
            
            submitted = st.form_submit_button("Save Product")
            
            if submitted:
                return {
                    "sku": sku,
                    "data": {
                        "title": title,
                        "price": price,
                        "quantity": quantity,
                        "categoryName": category,
                        "description": description
                    }
                }
            return None

class BulkActionsComponent:
    def render(self) -> Dict[str, Any]:
        """Render bulk actions controls"""
        st.markdown("### Bulk Actions")
        
        action = st.selectbox(
            "Select Action",
            ["Update Prices", "Update Stock", "Delete Selected"]
        )
        
        if action == "Update Prices":
            return self._render_price_update()
        elif action == "Update Stock":
            return self._render_stock_update()
        else:
            return {"action": "delete"} if st.button("Delete Selected Items") else None

    def _render_price_update(self) -> Dict[str, Any]:
        """Render price update controls"""
        col1, col2 = st.columns(2)
        
        with col1:
            update_type = st.selectbox(
                "Update Type",
                ["Fixed Price", "Percentage Increase", "Percentage Decrease"]
            )
            
        with col2:
            value = st.number_input(
                "Value",
                min_value=0.0,
                step=0.01
            )
            
        if st.button("Apply Price Update"):
            return {
                "action": "update_price",
                "update_type": update_type,
                "value": value
            }
        return None

    def _render_stock_update(self) -> Dict[str, Any]:
        """Render stock update controls"""
        col1, col2 = st.columns(2)
        
        with col1:
            update_type = st.selectbox(
                "Update Type",
                ["Set Fixed Stock", "Add Stock", "Subtract Stock"]
            )
            
        with col2:
            value = st.number_input(
                "Value",
                min_value=0,
                step=1
            )
            
        if st.button("Apply Stock Update"):
            return {
                "action": "update_stock",
                "update_type": update_type,
                "value": value
            }
        return None

class StatusComponent:
    def render(self, stats: Dict[str, Any]):
        """Render status information"""
        st.markdown("### Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Products",
                stats.get("total_products", 0)
            )
            
        with col2:
            st.metric(
                "Out of Stock",
                stats.get("out_of_stock", 0)
            )
            
        with col3:
            st.metric(
                "Last Sync",
                self._format_timestamp(stats.get("last_sync"))
            )

    def _format_timestamp(self, timestamp: Optional[datetime]) -> str:
        """Format timestamp for display"""
        if not timestamp:
            return "Never"
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

class NotificationComponent:
    def render(self):
        """Render notifications"""
        if "notification" in st.session_state:
            notification = st.session_state.notification
            if notification["type"] == "success":
                st.success(notification["message"])
            elif notification["type"] == "error":
                st.error(notification["message"])
            elif notification["type"] == "warning":
                st.warning(notification["message"])
            elif notification["type"] == "info":
                st.info(notification["message"])
