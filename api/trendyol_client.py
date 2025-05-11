"""
Trendyol API client
"""

import aiohttp
import json
import base64
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class TrendyolClient(BaseAPIClient):
    """Client for Trendyol API"""
    
    def __init__(self):
        """Initialize the Trendyol client"""
        super().__init__()
        self.api_url = "https://api.trendyol.com/sapigw"
        self.api_key = None
        self.api_secret = None
        self.supplier_id = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.api_key = os.getenv("TRENDYOL_API_KEY")
        self.api_secret = os.getenv("TRENDYOL_API_SECRET")
        self.supplier_id = os.getenv("TRENDYOL_SUPPLIER_ID")
        
        if not self.api_key:
            logger.warning("TRENDYOL_API_KEY environment variable not set")
        if not self.api_secret:
            logger.warning("TRENDYOL_API_SECRET environment variable not set")
        if not self.supplier_id:
            logger.warning("TRENDYOL_SUPPLIER_ID environment variable not set")
            
        # Setup authentication
        if self.api_key and self.api_secret:
            auth_string = f"{self.api_key}:{self.api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_auth}",
                "User-Agent": f'{self.supplier_id} - Integration',
            }
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Trendyol API"""
        if not self.api_key or not self.api_secret or not self.supplier_id:
            raise AuthenticationError("Trendyol API credentials not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=f"{self.api_url}/suppliers/{self.supplier_id}/products",
                headers=self.headers,
                params={"size": 2000, "page": 0}
            )
            
            self.authenticated = True
            logger.info("Trendyol authentication successful")
            
        except Exception as e:
            logger.error(f"Trendyol authentication failed: {str(e)}")
            raise AuthenticationError(f"Trendyol authentication failed: {str(e)}")
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> Dict[str, Any]:
        """
        Get products from Trendyol
        
        Args:
            **kwargs: Optional filters
                - page: Page number (default: 0)
                - size: Page size (default: 2000)
                - barcode: Filter by barcode
                - stockCode: Filter by stock code
                - approved: Filter by approval status (True/False)
                - dateQueryType: Filter by date type (CREATED_DATE, LAST_MODIFIED_DATE)
                - startDate: Filter by start date (timestamp)
                - endDate: Filter by end date (timestamp)
                - supplierId: Filter by supplier ID
                - archived: Filter archived products (True/False)
                - productMainId: Filter by product main ID
                - onSale: Filter products on sale (True/False)
                - rejected: Filter rejected products (True/False)
                - blacklisted: Filter blacklisted products (True/False)
                - brandIds: Filter by brand IDs (array)
                - force_refresh: Force refresh from API
                
        Returns:
            Dictionary with products and pagination info
        """
        # Build query parameters
        params = {}
        
        # Add pagination parameters (Trendyol uses 0-based indexing)
        params["page"] = kwargs.get("page", 0)
        params["size"] = kwargs.get("size", 2000)  # Increased default size to get more products
        
        # Add optional filters
        optional_params = [
            "barcode", "stockCode", "approved", "dateQueryType", 
            "startDate", "endDate", "supplierId", "archived", 
            "productMainId", "onSale", "rejected", "blacklisted"
        ]
        
        for param in optional_params:
            if param in kwargs:
                params[param] = kwargs[param]
        
        # Handle brand IDs array
        if "brandIds" in kwargs and isinstance(kwargs["brandIds"], list):
            for i, brand_id in enumerate(kwargs["brandIds"]):
                params[f"brandIds[{i}]"] = brand_id
            
        # Make request
        api_url = f"https://apigw.trendyol.com/integration/product/sellers/{self.supplier_id}/products"
        
        response = await self._make_request(
            method="GET",
            url=api_url,
            headers=self.headers,
            params=params
        )
        
        # Extract products
        products = []
        if isinstance(response, dict):
            # Handle paginated response
            if "content" in response and isinstance(response["content"], list):
                for item in response["content"]:
                    # Map Trendyol product data to our standard format
                    product = {
                        "sku": item.get("stockCode", ""),
                        "data": {
                            "title": item.get("title", ""),
                            "price": float(item.get("salePrice", 0)),
                            "list_price": float(item.get("listPrice", 0)),
                            "quantity": int(item.get("quantity", 0)),
                            "status": "active" if item.get("onSale", False) else "inactive",
                            "platform_id": item.get("id"),
                            "barcode": item.get("barcode"),
                            "brand": item.get("brand"),
                            "brand_id": item.get("brandId"),
                            "category_name": item.get("categoryName"),
                            "category_id": item.get("pimCategoryId"),
                            "description": item.get("description", ""),
                            "approved": item.get("approved", False),
                            "rejected": item.get("rejected", False),
                            "blacklisted": item.get("blacklisted", False),
                            "archived": item.get("archived", False),
                            "product_main_id": item.get("productMainId"),
                            "last_updated": item.get("lastUpdateDate"),
                            "product_url": item.get("productUrl"),
                            "vat_rate": item.get("vatRate")
                        }
                    }
                    
                    # Handle images properly
                    if item.get("images") and isinstance(item["images"], list):
                        # Store the full images array
                        product["data"]["images"] = item["images"]
                        
                        # Extract the first image URL for convenience
                        if len(item["images"]) > 0:
                            if isinstance(item["images"][0], dict) and "url" in item["images"][0]:
                                product["data"]["image_url"] = item["images"][0]["url"]
                            elif isinstance(item["images"][0], str):
                                product["data"]["image_url"] = item["images"][0]
                    
                    # Handle attributes
                    if item.get("attributes") and isinstance(item["attributes"], list):
                        product["data"]["attributes"] = item["attributes"]
                    
                    products.append(product)
                
                # Return paginated result with metadata
                return {
                    "items": products,
                    "total": response.get("totalElements", len(products)),
                    "page": response.get("number", params["page"]) + 1,  # Convert from 0-based to 1-based
                    "size": response.get("size", params["size"]),
                    "totalPages": response.get("totalPages", 1)
                }
        
        # Return simple list if no pagination info
        return {
            "items": products,
            "total": len(products),
            "page": int(params["page"]) + 1,  # Convert from 0-based to 1-based
            "size": params["size"],
            "totalPages": 1
        }
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in Trendyol
        
        Args:
            product_data: Product data to update
                - sku: Product SKU (stock code)
                - data: Product data to update
                    - price: New price
                    - quantity: New quantity
                    - status: New status
                    - title: New product title
                    - description: New product description
                    - barcode: New barcode
                    - brand: New brand name
                    - brand_id: New brand ID
                    - category_id: New category ID
                    - product_main_id: New product main ID
                    - vat_rate: New VAT rate
                    - attributes: New attributes
                    
        Returns:
            Update result
        """
        sku = product_data.get("sku")
        if not sku:
            raise ValueError("SKU is required for product update")
            
        data = product_data.get("data", {})
        if not data:
            raise ValueError("No data provided for update")
        
        # For price, quantity, and status updates, use the existing endpoints
        if "price" in data or "list_price" in data or "quantity" in data:
            # Price and inventory update
            price_inventory_data = {
                "items": [
                    {
                        "stockCode": sku
                    }
                ]
            }
            
            if "price" in data:
                price_inventory_data["items"][0]["salePrice"] = data["price"]
            
            if "list_price" in data:
                price_inventory_data["items"][0]["listPrice"] = data["list_price"]
                
            if "quantity" in data:
                price_inventory_data["items"][0]["quantity"] = data["quantity"]
            
            # Make price/inventory update request
            await self._make_request(
                method="POST",
                url=f"{self.api_url}/suppliers/{self.supplier_id}/products/price-and-inventory",
                headers=self.headers,
                json=price_inventory_data
            )
        
        if "status" in data:
            # Status update
            status_data = {
                "items": [
                    {
                        "stockCode": sku,
                        "onSale": data["status"] == "active"
                    }
                ]
            }
            
            await self._make_request(
                method="POST",
                url=f"{self.api_url}/suppliers/{self.supplier_id}/products/batch-status",
                headers=self.headers,
                json=status_data
            )
        
        # For other product information updates, use the v2/products endpoint
        update_fields = ["title", "description", "barcode", "brand", "brand_id", 
                        "category_id", "product_main_id", "vat_rate", "attributes"]
        
        if any(field in data for field in update_fields):
            # Prepare product update data
            product_update_data = {
                "items": [
                    {
                        "stockCode": sku
                    }
                ]
            }
            
            # Map fields to the Trendyol API format
            item_data = product_update_data["items"][0]
            
            if "title" in data:
                item_data["title"] = data["title"]
                
            if "description" in data:
                item_data["description"] = data["description"]
                
            if "barcode" in data:
                item_data["barcode"] = data["barcode"]
                
            if "brand" in data:
                item_data["brand"] = data["brand"]
                
            if "brand_id" in data:
                item_data["brandId"] = data["brand_id"]
                
            if "category_id" in data:
                item_data["categoryId"] = data["category_id"]
                
            if "product_main_id" in data:
                item_data["productMainId"] = data["product_main_id"]
                
            if "vat_rate" in data:
                item_data["vatRate"] = data["vat_rate"]
                
            if "attributes" in data and isinstance(data["attributes"], list):
                item_data["attributes"] = data["attributes"]
            
            # Make product update request
            await self._make_request(
                method="POST",
                url=f"{self.api_url}/suppliers/{self.supplier_id}/v2/products",
                headers=self.headers,
                json=product_update_data
            )
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }