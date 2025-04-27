# utils/table_manager.py
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st
from datetime import datetime
import logging

class TableManager:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.last_operation = None

    def prepare_table_data(self, data: List[Dict[str, Any]], 
                          search: str = "", 
                          sort_by: Optional[str] = None,
                          filters: Dict[str, Any] = None) -> pd.DataFrame:
        """Prepare data for table display with search and sorting"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                "Select": False,
                "SKU": item.get("sku", ""),
                "Title": item.get("data", {}).get("title", ""),
                "Price": float(item.get("data", {}).get("price", 0)),
                "Quantity": int(item.get("data", {}).get("quantity", 0)),
                "Category": item.get("data", {}).get("categoryName", ""),
                "Status": "Active" if int(item.get("data", {}).get("quantity", 0)) > 0 else "Out of Stock"
            } for item in data])

            # Apply search
            if search:
                mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False)).any(axis=1)
                df = df[mask]

            # Apply filters
            if filters:
                for column, value in filters.items():
                    if value:
                        df = df[df[column].astype(str).str.contains(value, case=False)]

            # Apply sorting
            if sort_by:
                df = df.sort_values(by=sort_by)

            return df

        except Exception as e:
            logging.error(f"Error preparing table data: {str(e)}")
            st.error("Error preparing table data")
            return pd.DataFrame()

    def handle_bulk_update(self, selected_rows: pd.DataFrame, 
                          update_type: str, 
                          value: float) -> None:
        """Handle bulk updates for price or quantity"""
        try:
            # Store current state for undo
            self.undo_stack.append({
                "data": st.session_state.fetched_data.copy(),
                "operation": f"bulk_{update_type}"
            })

            # Update selected products
            skus = selected_rows["SKU"].tolist()
            updated_count = 0

            for product in st.session_state.fetched_data:
                if product.get("sku") in skus:
                    if update_type == "price":
                        product["data"]["price"] = round(float(value), 2)
                        product["data"]["salePrice"] = round(float(value), 2)
                        product["data"]["listPrice"] = round(float(value), 2)
                    elif update_type == "quantity":
                        product["data"]["quantity"] = int(value)
                    updated_count += 1

            st.success(f"Updated {updated_count} products")
            self.last_operation = {
                "type": f"bulk_{update_type}",
                "affected": updated_count,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logging.error(f"Bulk update failed: {str(e)}")
            st.error("Update failed")

    def handle_row_edit(self, edited_rows: Dict[int, Dict[str, Any]]) -> None:
        """Handle individual row edits"""
        try:
            if edited_rows:
                # Store current state for undo
                self.undo_stack.append({
                    "data": st.session_state.fetched_data.copy(),
                    "operation": "row_edit"
                })

                for idx, changes in edited_rows.items():
                    product = st.session_state.fetched_data[idx]
                    
                    # Validate changes
                    if "Price" in changes and changes["Price"] < 0:
                        st.error(f"Invalid price for SKU {product['sku']}")
                        continue
                        
                    if "Quantity" in changes and changes["Quantity"] < 0:
                        st.error(f"Invalid quantity for SKU {product['sku']}")
                        continue

                    # Apply changes
                    if "Title" in changes:
                        product["data"]["title"] = changes["Title"]
                    if "Price" in changes:
                        price = round(float(changes["Price"]), 2)
                        product["data"]["price"] = price
                        product["data"]["salePrice"] = price
                        product["data"]["listPrice"] = price
                    if "Quantity" in changes:
                        product["data"]["quantity"] = int(changes["Quantity"])
                    if "Category" in changes:
                        product["data"]["categoryName"] = changes["Category"]

                st.success("Changes saved successfully")
                self.last_operation = {
                    "type": "row_edit",
                    "affected": len(edited_rows),
                    "timestamp": datetime.now()
                }

        except Exception as e:
            logging.error(f"Row edit failed: {str(e)}")
            st.error("Edit failed")

    def undo_last_operation(self) -> None:
        """Undo last table operation"""
        try:
            if self.undo_stack:
                last_state = self.undo_stack.pop()
                self.redo_stack.append({
                    "data": st.session_state.fetched_data.copy(),
                    "operation": last_state["operation"]
                })
                st.session_state.fetched_data = last_state["data"]
                st.success("Undo successful")
            else:
                st.info("Nothing to undo")

        except Exception as e:
            logging.error(f"Undo failed: {str(e)}")
            st.error("Undo failed")

    def redo_last_operation(self) -> None:
        """Redo last undone operation"""
        try:
            if self.redo_stack:
                next_state = self.redo_stack.pop()
                self.undo_stack.append({
                    "data": st.session_state.fetched_data.copy(),
                    "operation": next_state["operation"]
                })
                st.session_state.fetched_data = next_state["data"]
                st.success("Redo successful")
            else:
                st.info("Nothing to redo")

        except Exception as e:
            logging.error(f"Redo failed: {str(e)}")
            st.error("Redo failed")
