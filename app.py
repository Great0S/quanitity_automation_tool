import streamlit as st
import pandas as pd
from api.n11_rest_api import N11RestAPI
from api.trendyol_api import TrendyolClient
from api.amazon_seller_api import AmazonListingManager
from api.hepsiburada_api import Hb_API
from api.pazarama_api import PazaramaAPIClient
from api.pttavm_api import getpttavm_procuctskdata
from api.wordpress_api import WooCommerceAPIClient

# Initialize session state variables
if "products_table" not in st.session_state:
    st.session_state.products_table = {"edited_rows": {}}
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "fetched_data" not in st.session_state:
    st.session_state.fetched_data = []
if "notification" not in st.session_state:
    st.session_state.notification = {"type": None, "message": None}
if "show_edit_form" not in st.session_state:
    st.session_state.show_edit_form = False
if "edit_product" not in st.session_state:
    st.session_state.edit_product = None
if "current_operation" not in st.session_state:
    st.session_state.current_operation = "Create"

# Real API clients
clients = {
    "N11": N11RestAPI(),
    "Trendyol": TrendyolClient(),
    "Amazon": AmazonListingManager(),
    "HepsiBurada": Hb_API(),
    "PTTAVM": {"get": getpttavm_procuctskdata},
    "Pazarama": PazaramaAPIClient(),
    "WooCommerce": WooCommerceAPIClient(),
}

# Page configuration
st.set_page_config(
    page_title="E-Commerce Product Manager", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply appropriate theme
if st.session_state.dark_mode:
    theme_bg = "rgba(46, 52, 64, 1)"
    theme_text = "rgba(236, 239, 244, 1)"
    theme_secondary = "rgba(76, 86, 106, 1)"
    button_color = "#a78bfa"
else:
    theme_bg = "rgba(236, 239, 244, 1)"
    theme_text = "rgba(46, 52, 64, 1)"
    theme_secondary = "rgba(216, 222, 233, 1)"
    button_color = "#a78bfa"

# CSS for responsive design and theme
st.markdown(f"""
    <style>
        /* Base theme */
        .stApp {{
            background-color: {theme_bg};
            color: {theme_text};
        }}
        
        /* Button styling */
        .stButton>button {{
            background-color: {button_color} !important;
            color: white;
            border-radius: 8px;
            width: 100%;
            transition: all 0.3s ease;
        }}
        .stButton>button:hover {{
            opacity: 0.85;
            transform: translateY(-2px);
        }}
        
        /* Form elements */
        .stTextInput>div>div>input, .stNumberInput>div>div>input {{
            border-radius: 6px;
        }}
        
        /* Data editor */
        .stDataFrame {{
            border-radius: 8px;
            overflow: hidden;
        }}
        
        /* Expander styling */
        .streamlit-expanderHeader {{
            border-radius: 8px;
            background-color: {theme_secondary};
        }}
        
        /* Small box utilities */
        .small-box {{ 
            padding: 5px 10px; 
            border-radius: 5px; 
            margin: 5px 0;
        }}
        
        /* Responsive grid */
        @media (max-width: 768px) {{
            .responsive-cols {{
                display: flex;
                flex-direction: column;
            }}
            .responsive-cols > div {{
                width: 100% !important;
                margin-bottom: 10px;
            }}
        }}
        
        /* Status badges */
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .success-badge {{
            background-color: rgba(72, 187, 120, 0.2);
            color: rgb(72, 187, 120);
        }}
        .warning-badge {{
            background-color: rgba(246, 173, 85, 0.2);
            color: rgb(246, 173, 85);
        }}
        .error-badge {{
            background-color: rgba(245, 101, 101, 0.2);
            color: rgb(245, 101, 101);
        }}
        
        /* Fix for preventOverflow warning */
        [data-testid="stPopover"] {{
            position: relative !important;
        }}
        div[data-baseweb="popover"] {{
            z-index: 1000 !important;
        }}
    </style>
""", unsafe_allow_html=True)

# App header
st.title("📦 E-Commerce Product Manager")

def toggle_dark_mode():
    st.session_state.dark_mode = not st.session_state.dark_mode

# Dark mode toggle in the sidebar
with st.sidebar:
    st.title("Settings")
    # Fix for dark mode toggle to preserve current operation
    if st.toggle("🌗 Dark Mode", value=st.session_state.dark_mode, on_change=toggle_dark_mode):
        # Store current operation before rerunning
        # st.session_state.current_operation = operation
        # st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# Main layout
st.markdown("Manage products across multiple e-commerce platforms")

# Operation selection
col1, col2 = st.columns([1, 3])
with col1:
    # Use the stored operation when toggling dark mode
    operation = st.selectbox("Operation", ["Create", "Update"], 
                             index=0 if st.session_state.current_operation == "Create" else 1)
    # Store the current operation
    st.session_state.current_operation = operation

# Platform selection with responsive columns
col_source, col_target = st.columns(2, gap="medium")
with col_source:
    source_platform = st.selectbox("Source Platform", list(clients.keys()))
with col_target:
    target_platform = st.selectbox("Target Platform", list(clients.keys()))

# Display notification if exists
if st.session_state.notification["type"]:
    if st.session_state.notification["type"] == "success":
        st.success(st.session_state.notification["message"])
    elif st.session_state.notification["type"] == "error":
        st.error(st.session_state.notification["message"])
    elif st.session_state.notification["type"] == "warning":
        st.warning(st.session_state.notification["message"])
    # Clear notification after displaying
    st.session_state.notification = {"type": None, "message": None}

# Add Edit Product Form (popup dialog)
if st.session_state.show_edit_form and st.session_state.edit_product is not None:
    with st.expander("Edit Product", expanded=True):
        st.markdown("### Edit Product Details")
        with st.form("edit_product_form"):
            edit_prod = st.session_state.edit_product
            edit_data = next((p for p in st.session_state.fetched_data 
                             if p.get("sku") == edit_prod.get("SKU")), None)
            
            if edit_data:  # Make sure we found the product data
                form_col1, form_col2 = st.columns(2)
                with form_col1:
                    sku = st.text_input("SKU/Stock Code", value=edit_prod.get("SKU", ""), disabled=True)
                    edit_title = st.text_input("Title", value=edit_prod.get("Title", ""))
                    edit_category = st.text_input("Category", value=edit_prod.get("Category", ""))
                
                with form_col2:
                    edit_price = st.number_input("Price", value=float(edit_prod.get("Price", 0)), 
                                               min_value=0.0, step=0.01, format="%.2f")
                    edit_qty = st.number_input("Quantity", value=int(edit_prod.get("Quantity", 0)), 
                                             min_value=0, step=1)
                    edit_description = st.text_area("Description", 
                                                 value=edit_data.get("data", {}).get("description", ""), 
                                                 height=100)
                
                st.info(f"Editing product: {edit_prod.get('Title', '')}")
                
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    cancel_button = st.form_submit_button("Cancel", use_container_width=True)
                
                with edit_col2:
                    save_button = st.form_submit_button("Save Changes", use_container_width=True)
                
                if cancel_button:
                    st.session_state.show_edit_form = False
                    st.session_state.edit_product = None
                    st.rerun()
                
                if save_button:
                    # Update the product in fetched_data
                    edit_data["data"]["title"] = edit_title
                    edit_data["data"]["price"] = edit_price
                    edit_data["data"]["salePrice"] = edit_price
                    edit_data["data"]["listPrice"] = edit_price
                    edit_data["data"]["quantity"] = edit_qty
                    edit_data["data"]["categoryName"] = edit_category
                    edit_data["data"]["description"] = edit_description
                    
                    st.session_state.notification = {
                        "type": "success", 
                        "message": f"Product '{edit_title}' updated successfully"
                    }
                    st.session_state.show_edit_form = False
                    st.session_state.edit_product = None
                    st.rerun()
            else:
                st.error(f"Could not find product with SKU: {edit_prod.get('SKU', '')}")
                if st.form_submit_button("Close"):
                    st.session_state.show_edit_form = False
                    st.session_state.edit_product = None
                    st.rerun()

# Conditional UI based on operation
# Define filter variables with default empty values
sku_filter = ""
category_filter = ""

# Different UI for each operation mode
if operation == "Update":
    # In Update mode, show filters and fetch button
    with st.container():
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            sku_filter = st.text_input("Filter by SKU", placeholder="Enter SKU code...")
        with filter_col2:
            category_filter = st.text_input("Filter by Category", placeholder="Enter category name...")
    
    # Fetch button
    if st.button("🔄 Fetch Products from Source", use_container_width=True):
        try:
            with st.spinner(f"Fetching products from {source_platform}..."):
                client = clients[source_platform]
                # Handle different API client structures
                if source_platform == "PTTAVM":
                    data = client["get"](True)
                elif hasattr(client, "get_products"):
                    data = client.get_products(raw_data=True)
                else:
                    data = client.get_listings(every_product=True)
                
                # Apply filters if provided
                if sku_filter:
                    data = [item for item in data if sku_filter.lower() in item.get("sku", "").lower()]
                if category_filter:
                    data = [item for item in data if category_filter.lower() in 
                           (item.get("data", {}).get("categoryName", "") or "").lower()]
                
                st.session_state.fetched_data = data
                st.session_state.notification = {
                    "type": "success", 
                    "message": f"Successfully fetched {len(data)} products from {source_platform}."
                }
                st.rerun()
        except Exception as e:
            st.session_state.notification = {
                "type": "error", 
                "message": f"Failed to fetch products: {str(e)}"
            }
            st.rerun()

elif operation == "Create":
    # In Create mode, show fetch, file upload, and manual entry
    create_col1, create_col2 = st.columns(2)
    
    with create_col1:
        # Fetch button for Create mode
        if st.button("🔄 Fetch Existing Products", use_container_width=True):
            try:
                with st.spinner(f"Fetching products from {source_platform}..."):
                    client = clients[source_platform]
                    # Handle different API client structures
                    if source_platform == "PTTAVM":
                        data = client["get"](True)
                    elif hasattr(client, "get_products"):
                        data = client.get_products(raw_data=True)
                    else:
                        data = client.get_listings(every_product=True)
                    
                    st.session_state.fetched_data = data
                    st.session_state.notification = {
                        "type": "success", 
                        "message": f"Successfully fetched {len(data)} products from {source_platform}."
                    }
                    st.rerun()
            except Exception as e:
                st.session_state.notification = {
                    "type": "error", 
                    "message": f"Failed to fetch products: {str(e)}"
                }
                st.rerun()
    
    with create_col2:
        # File upload option (only in Create mode)
        uploaded_file = st.file_uploader("📁 Upload Product File (CSV, Excel)", 
                                        type=["csv", "xlsx", "xls"], 
                                        help="Upload a file with product data")
        
        if uploaded_file is not None:
            try:
                with st.spinner("Processing uploaded file..."):
                    # Determine file type by extension
                    file_type = uploaded_file.name.split(".")[-1].lower()
                    
                    if file_type == "csv":
                        # Process CSV file
                        import io
                        import csv
                        
                        # Read CSV file
                        content = uploaded_file.getvalue().decode("utf-8")
                        csv_data = csv.DictReader(io.StringIO(content))
                        
                        products = []
                        for row in csv_data:
                            if "sku" in row and "title" in row:
                                product = {
                                    "sku": row.get("sku", ""),
                                    "data": {
                                        "title": row.get("title", ""),
                                        "price": float(row.get("price", 0)),
                                        "salePrice": float(row.get("price", 0)),
                                        "listPrice": float(row.get("price", 0)),
                                        "quantity": int(row.get("quantity", 0)),
                                        "categoryName": row.get("category", ""),
                                        "stockCode": row.get("sku", ""),
                                        "description": row.get("description", ""),
                                        "images": []
                                    }
                                }
                                products.append(product)
                        
                        # Add to session state
                        st.session_state.fetched_data.extend(products)
                        st.session_state.notification = {
                            "type": "success", 
                            "message": f"Successfully imported {len(products)} products from CSV file."
                        }
                        st.rerun()
                    
                    elif file_type in ["xlsx", "xls"]:
                        # Process Excel file
                        import pandas as pd
                        
                        df = pd.read_excel(uploaded_file)
                        
                        # Check for required columns
                        required_cols = ["sku", "title"]
                        if not all(col in df.columns for col in required_cols):
                            st.session_state.notification = {
                                "type": "error", 
                                "message": f"Excel file must contain columns: {', '.join(required_cols)}"
                            }
                            st.rerun()
                        
                        products = []
                        for _, row in df.iterrows():
                            product = {
                                "sku": str(row.get("sku", "")),
                                "data": {
                                    "title": str(row.get("title", "")),
                                    "price": float(row.get("price", 0)),
                                    "salePrice": float(row.get("price", 0)),
                                    "listPrice": float(row.get("price", 0)),
                                    "quantity": int(row.get("quantity", 0)),
                                    "categoryName": str(row.get("category", "")),
                                    "stockCode": str(row.get("sku", "")),
                                    "description": str(row.get("description", "")),
                                    "images": []
                                }
                            }
                            products.append(product)
                        
                        # Add to session state
                        st.session_state.fetched_data.extend(products)
                        st.session_state.notification = {
                            "type": "success", 
                            "message": f"Successfully imported {len(products)} products from Excel file."
                        }
                        st.rerun()
            
            except Exception as e:
                st.session_state.notification = {
                    "type": "error", 
                    "message": f"Failed to process file: {str(e)}"
                }
                st.rerun()

# Manual product entry (available in both Create and Update modes)
with st.expander("➕ Add Product Manually", expanded=False):
    with st.form("manual_product_form"):
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            sku = st.text_input("SKU/Stock Code", placeholder="Enter unique product code")
            title = st.text_input("Title", placeholder="Enter product title")
            category = st.text_input("Category", placeholder="Enter product category")
        
        with form_col2:
            price = st.number_input("Price", min_value=0.0, step=0.01, format="%.2f")
            qty = st.number_input("Quantity", min_value=0, step=1)
            description = st.text_area("Description", placeholder="Enter product description", height=100)
        
        submitted = st.form_submit_button("Add Product", use_container_width=True)
        
        if submitted:
            # Validate required fields
            if not sku or not title or price <= 0:
                st.session_state.notification = {
                    "type": "warning", 
                    "message": "Please fill in all required fields (SKU, Title, and Price)"
                }
            else:
                # Check for duplicate SKU
                if any(item.get("sku") == sku for item in st.session_state.fetched_data):
                    st.session_state.notification = {
                        "type": "warning", 
                        "message": f"Product with SKU '{sku}' already exists"
                    }
                else:
                    # Add new product to session state
                    st.session_state.fetched_data.append({
                        "sku": sku,
                        "data": {
                            "title": title,
                            "price": price,
                            "salePrice": price,
                            "listPrice": price,
                            "quantity": qty,
                            "categoryName": category,
                            "stockCode": sku,
                            "description": description or "Manual Entry",
                            "images": []
                        }
                    })
                    st.session_state.notification = {
                        "type": "success", 
                        "message": f"Product '{title}' added successfully"
                    }
            st.rerun()

# Product data table
if st.session_state.fetched_data:
    # Table options
    table_options_col1, table_options_col2, table_options_col3 = st.columns([1, 1, 2])
    
    with table_options_col1:
        row_limit = st.selectbox("Show Rows", ["All", 10, 25, 50, 100], index=1)
    
    with table_options_col2:
        sort_by = st.selectbox("Sort By", ["SKU", "Title", "Price", "Quantity", "Category"])
    
    with table_options_col3:
        # Add Select All checkbox
        select_all = st.checkbox("Select All Products", key="select_all_products")
        st.markdown(f"**{len(st.session_state.fetched_data)}** products available")
    
    # Prepare table data
    table_data = []
    for item in st.session_state.fetched_data:
        d = item.get("data", {})
        table_data.append({
            "Select": False,
            "SKU": item.get("sku", ""),
            "Title": d.get("title", ""),
            "Price": d.get("salePrice") or d.get("listPrice") or d.get("price", 0),
            "Quantity": d.get("quantity", 0),
            "Category": d.get("categoryName", "")
        })
    
    # Apply row limit if not "All"
    df = pd.DataFrame(table_data)
    
    # Sort the dataframe
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by)
    
    if row_limit != "All":
        df = df.head(int(row_limit))
    
    # Apply Select All if checked
    if select_all and not df.empty:
        df["Select"] = True
    
    # Display editable table
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "Title": st.column_config.TextColumn("Title"),
            "Price": st.column_config.NumberColumn("Price", format="%.2f", min_value=0, step=0.01),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
            "Category": st.column_config.TextColumn("Category")
        },
        key="products_table"
    )
    
    # Get selected rows from the data editor
    selected_rows = edited_df[edited_df["Select"] == True]
    selected_count = len(selected_rows)
    
    # Show action buttons when rows are selected
    if selected_count > 0:
        st.markdown(f"**{selected_count}** products selected")
        
        # Action buttons in columns
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        
        with edit_col1:
            if selected_count == 1:
                if st.button("✏️ Edit Selected", use_container_width=True, key="edit_selected_button"):
                    # Get the selected product
                    product_to_edit = selected_rows.iloc[0].to_dict()
                    st.session_state.edit_product = product_to_edit
                    st.session_state.show_edit_form = True
                    st.rerun()
            else:
                st.button("✏️ Edit (select one product)", disabled=True, use_container_width=True)
        
        with edit_col2:
            if st.button(f"❌ Delete Selected ({selected_count})", use_container_width=True):
                selected_skus = selected_rows["SKU"].tolist()
                st.session_state.fetched_data = [p for p in st.session_state.fetched_data 
                                               if p.get("sku") not in selected_skus]
                st.session_state.notification = {
                    "type": "success", 
                    "message": f"Deleted {selected_count} products"
                }
                st.rerun()
        
        with edit_col3:
            if st.button(f"📤 Upload to {target_platform} ({selected_count})", use_container_width=True):
                try:
                    with st.spinner(f"Uploading to {target_platform}..."):
                        client = clients[target_platform]
                        count = 0
                        errors = []
                        
                        for _, row in selected_rows.iterrows():
                            try:
                                # Find matching product in fetched data
                                match = next((p for p in st.session_state.fetched_data 
                                             if p.get("sku") == row["SKU"]), None)
                                
                                if match:
                                    # Update with edited values
                                    match["data"]["title"] = row["Title"]
                                    match["data"]["salePrice"] = row["Price"]
                                    match["data"]["listPrice"] = row["Price"]
                                    match["data"]["price"] = row["Price"]
                                    match["data"]["quantity"] = row["Quantity"]
                                    match["data"]["categoryName"] = row["Category"]
                                    
                                    # Handle different API methods
                                    if hasattr(client, "create_product"):
                                        client.create_product([match])
                                    elif hasattr(client, "add_listing"):
                                        client.add_listing(match)
                                    elif hasattr(client, "update_product"):
                                        client.update_product(match)
                                    elif hasattr(client, "update_listing"):
                                        client.update_listing(match)
                                    else:
                                        raise Exception(f"No suitable upload method found for {target_platform}")
                                    
                                    count += 1
                            except Exception as e:
                                errors.append(f"{row['SKU']}: {str(e)}")
                        
                        if errors:
                            st.session_state.notification = {
                                "type": "warning", 
                                "message": f"Uploaded {count}/{selected_count} products. Errors: {', '.join(errors[:3])}{' and more...' if len(errors) > 3 else ''}"
                            }
                        else:
                            st.session_state.notification = {
                                "type": "success", 
                                "message": f"Successfully uploaded {count} products to {target_platform}"
                            }
                        st.rerun()
                except Exception as e:
                    st.session_state.notification = {
                        "type": "error", 
                        "message": f"Upload failed: {str(e)}"
                    }
                    st.rerun()
    else:
        st.info("Select products from the table to perform actions")

else:
    # Empty state
    st.info("No products loaded. Please fetch products from a source platform or add products manually.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; opacity: 0.7;'>E-Commerce Product Manager • "
    "Made with ❤️ and Streamlit</div>", 
    unsafe_allow_html=True
)