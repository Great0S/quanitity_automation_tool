"""
Hepsiburada API client
"""

import aiohttp
import json
import base64
import asyncio
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class HepsiburadaClient(BaseAPIClient):
    """Client for Hepsiburada API"""
    
    def __init__(self):
        """Initialize the Hepsiburada client"""
        super().__init__()
        self.api_url = "https://api.hepsiburada.com"
        self.username = None
        self.password = None
        self.merchant_id = None
        self.access_token = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.username = os.getenv("HEPSIBURADA_USERNAME")
        self.password = os.getenv("HEPSIBURADA_PASSWORD")
        self.merchant_id = os.getenv("HEPSIBURADA_MERCHANT_ID")
        
        if not self.username:
            logger.warning("HEPSIBURADA_USERNAME environment variable not set")
        if not self.password:
            logger.warning("HEPSIBURADA_PASSWORD environment variable not set")
        if not self.merchant_id:
            logger.warning("HEPSIBURADA_MERCHANT_ID environment variable not set")
            
        # Setup headers with Basic Auth
        if self.merchant_id and self.password:
            auth_string = f"{self.merchant_id}:{self.password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "sentosyazilim_dev",
                "Authorization": f"Basic {encoded_auth}"
            }
        else:
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "sentosyazilim_dev"
            }
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Hepsiburada API"""
        if not self.merchant_id or not self.password:
            raise AuthenticationError("Hepsiburada merchant_id or password not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=f"https://mpop.hepsiburada.com/product/api/products/all-products-of-merchant/{self.merchant_id}",
                headers=self.headers,
                params={"page": 0, "size": 100}
            )
            
            self.authenticated = True
            logger.info("Hepsiburada authentication successful")
            
        except Exception as e:
            logger.error(f"Hepsiburada authentication failed: {str(e)}")
            raise AuthenticationError(f"Hepsiburada authentication failed: {str(e)}")
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> Dict[str, Any]:
        """
        Get products from Hepsiburada
        
        Args:
            **kwargs: Optional filters
                - page: Page number (default: 0)
                - size: Page size (default: 100)
                - force_refresh: Force refresh from API
                
        Returns:
            Dictionary with products and pagination info
        """
        # Build query parameters
        params = {}
        
        # Add required pagination parameters
        params["page"] = kwargs.get("page", 0)  # Hepsiburada uses 0-based indexing
        params["size"] = kwargs.get("size", 100)  # Hepsiburada returns 100 items per page
        
        logger.info(f"Fetching Hepsiburada products with params: {params}")
        
        # Make request
        response = await self._make_request(
            method="GET",
            url=f"https://mpop.hepsiburada.com/product/api/products/all-products-of-merchant/{self.merchant_id}",
            headers=self.headers,
            params=params
        )
        
        # Extract products
        products = []
        
        if isinstance(response, dict) and "data" in response:
            logger.info(f"Received {len(response['data'])} products from Hepsiburada API")
            
            # Process product data
            for item in response["data"]:
                # Map Hepsiburada product data to our standard format
                product = {
                    "sku": item.get("merchantSku", ""),
                    "data": {
                        "title": item.get("productName", ""),
                        "price": float(item.get("price", 0)) if item.get("price") else 0,
                        "quantity": int(item.get("stock", 0)) if item.get("stock") else 0,
                        "status": "active" if item.get("status") == "MATCHED" else "inactive",
                        "platform_id": item.get("hbSku"),
                        "hepsiburada_sku": item.get("hbSku"),
                        "merchant_sku": item.get("merchantSku"),
                        "barcode": item.get("barcode"),
                        "brand": item.get("brand"),
                        "category_id": item.get("categoryId"),
                        "category_name": item.get("categoryName"),
                        "tax": item.get("tax"),
                        "description": item.get("description"),
                        "variant_group_id": item.get("variantGroupId"),
                        "status_code": item.get("status")
                    }
                }
                
                # Handle images properly
                if item.get("images") and isinstance(item["images"], list):
                    # Store the full images array
                    product["data"]["images"] = item["images"]
                    
                    # Extract the first image URL for convenience
                    if len(item["images"]) > 0:
                        product["data"]["image_url"] = item["images"][0]
                
                # Add base attributes
                if "baseAttributes" in item and isinstance(item["baseAttributes"], list):
                    base_attrs = {}
                    for attr in item["baseAttributes"]:
                        if "name" in attr and "value" in attr:
                            base_attrs[attr["name"]] = attr["value"]
                    product["data"]["base_attributes"] = base_attrs
                
                # Add product attributes
                if "productAttributes" in item and isinstance(item["productAttributes"], list):
                    prod_attrs = {}
                    for attr in item["productAttributes"]:
                        if "name" in attr and "value" in attr:
                            prod_attrs[attr["name"]] = attr["value"]
                    product["data"]["product_attributes"] = prod_attrs
                
                products.append(product)
        
        # Extract pagination info based on the actual response structure
        total_elements = response.get("totalElements", len(products))
        total_pages = response.get("totalPages", 1)
        page_number = response.get("number", params["page"])
        page_size = response.get("numberOfElements", params["size"])
        
        logger.info(f"Processed {len(products)} products from Hepsiburada, total: {total_elements}, page: {page_number}/{total_pages}")
        
        # Return paginated result with metadata
        return {
            "items": products,
            "total": total_elements,
            "page": page_number,
            "size": page_size,
            "totalPages": total_pages
        }
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in Hepsiburada
        
        Args:
            product_data: Product data to update
                - sku: Product SKU (merchant SKU)
                - data: Product data to update
                    - price: New price
                    - quantity: New quantity (stock)
                    - title: New product name
                    - description: New product description
                    - images: New product images
                    - attributes: New product attributes
                    
        Returns:
            Update result
        """
        sku = product_data.get("sku")
        if not sku:
            raise ValueError("SKU is required for product update")
            
        data = product_data.get("data", {})
        if not data:
            raise ValueError("No data provided for update")
        
        # Get the hbSku from the data
        hb_sku = data.get("hepsiburada_sku") or data.get("platform_id")
        if not hb_sku:
            raise ValueError("Hepsiburada SKU is required for product update")
        
        # Prepare update data for the new API endpoint
        item_data = {
            "hbSku": hb_sku
        }
        
        # Map fields to the new API format
        if "title" in data:
            item_data["productName"] = data["title"]
            
        if "description" in data:
            item_data["productDescription"] = data["description"]
        
        # Handle images
        if "images" in data and isinstance(data["images"], list):
            for i, img_url in enumerate(data["images"][:10], 1):  # Max 10 images
                item_data[f"image{i}"] = img_url
        
        # Handle attributes
        if "attributes" in data and isinstance(data["attributes"], dict):
            item_data["attributes"] = data["attributes"]
        
        # Create the full update payload
        update_payload = {
            "merchantId": self.merchant_id,
            "items": [item_data]
        }
        
        # For price and quantity updates, use the old endpoint
        if "price" in data or "quantity" in data:
            # Prepare update data for price/stock
            stock_update_data = {
                "merchantSku": sku
            }
            
            if "price" in data:
                stock_update_data["price"] = data["price"]
            
            if "quantity" in data:
                stock_update_data["stock"] = data["quantity"]
            
            # Make price/stock update request
            await self._make_request(
                method="PUT",
                url=f"https://mpop.hepsiburada.com/product/api/products/update/{self.merchant_id}/{sku}",
                headers=self.headers,
                json=stock_update_data
            )
        
        # If we have other fields to update, use the new endpoint
        if len(item_data) > 1:  # More than just hbSku
            # Create a temporary JSON file
            import tempfile
            import os
            
            # Write JSON to a file with text mode
            with open(tempfile.gettempdir() + '/product_update.json', 'w', encoding='utf-8') as temp_file:
                json.dump(update_payload, temp_file)
                temp_file_path = temp_file.name
            
            try:
                # Prepare multipart form data
                form_data = aiohttp.FormData()
                form_data.add_field('file', 
                                   open(temp_file_path, 'rb'),
                                   filename='product_update.json',
                                   content_type='application/json')
                
                # Make update request with multipart form data
                await self._make_request(
                    method="POST",
                    url="https://mpop.hepsiburada.com/ticket-api/api/integrator/import",
                    headers={**self.headers, "Content-Type": None},  # Remove Content-Type for multipart
                    data=form_data,
                    params={"version": 1}
                )
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product update request submitted successfully"
        }
        
    @handle_exceptions
    async def get_all_products(self) -> List[Dict[str, Any]]:
        """
        Get all products from Hepsiburada by paginating through all pages
        
        Returns:
            List of all products
        """
        all_products = []
        current_page = 0  # Hepsiburada API uses 0-based indexing
        page_size = 100  # Hepsiburada returns 100 items per page
        
        logger.info("Fetching all products from Hepsiburada (this may take a while)...")
        
        # Make initial request to get total pages
        initial_response = await self.get_products(page=current_page, size=page_size)
        total_pages = initial_response.get("totalPages", 1)
        total_elements = initial_response.get("total", 0)
        
        logger.info(f"Hepsiburada has {total_elements} products across {total_pages} pages")
        
        # Add products from first page
        if "items" in initial_response and isinstance(initial_response["items"], list):
            all_products.extend(initial_response["items"])
            logger.info(f"Fetched {len(initial_response['items'])} products from page {current_page+1}/{total_pages}")
        
        # Fetch remaining pages
        current_page += 1
        while current_page < total_pages:
            try:
                logger.info(f"Fetching Hepsiburada products page {current_page+1}/{total_pages}")
                
                # Get products for current page
                result = await self.get_products(page=current_page, size=page_size)
                
                # Add products to the list
                if "items" in result and isinstance(result["items"], list):
                    all_products.extend(result["items"])
                    logger.info(f"Fetched {len(result['items'])} products from page {current_page+1}/{total_pages}")
                else:
                    logger.warning(f"No items found in response for page {current_page+1}, but continuing pagination")
                
                # Move to next page
                current_page += 1
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching page {current_page+1}: {str(e)}")
                # Continue with next page despite errors
                current_page += 1
                await asyncio.sleep(1)  # Longer delay after error
        
        logger.info(f"Fetched a total of {len(all_products)} products from Hepsiburada")
        
        return all_products