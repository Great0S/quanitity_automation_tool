"""
OpenCart API client
"""

import aiohttp
import json
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class OpenCartClient(BaseAPIClient):
    """Client for OpenCart API"""
    
    def __init__(self):
        """Initialize the OpenCart client"""
        super().__init__()
        self.api_url = None
        self.api_key = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.api_url = os.getenv("OC_URL")
        self.api_key = os.getenv("OC_API_KEY")
        
        if not self.api_url:
            logger.warning("OC_URL environment variable not set")
        if not self.api_key:
            logger.warning("OC_API_KEY environment variable not set")
            
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with OpenCart API"""
        if not self.api_url or not self.api_key:
            raise AuthenticationError("OpenCart API URL or API key not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=f"{self.api_url}/api/products",
                headers=self.headers,
                params={"limit": 1}
            )
            
            self.authenticated = True
            logger.info("OpenCart authentication successful")
            
        except Exception as e:
            logger.error(f"OpenCart authentication failed: {str(e)}")
            raise AuthenticationError(f"OpenCart authentication failed: {str(e)}")
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get products from OpenCart
        
        Args:
            **kwargs: Optional filters
                - limit: Maximum number of products to return
                - page: Page number
                - sku: Filter by SKU
                
        Returns:
            List of products
        """
        params = {}
        
        # Add filters
        if "limit" in kwargs:
            params["limit"] = kwargs["limit"]
        if "page" in kwargs:
            params["page"] = kwargs["page"]
        if "sku" in kwargs:
            params["filter_sku"] = kwargs["sku"]
            
        # Make request
        response = await self._make_request(
            method="GET",
            url=f"{self.api_url}/api/products",
            headers=self.headers,
            params=params
        )
        
        # Extract products
        products = []
        if isinstance(response, dict) and "products" in response:
            for product in response["products"]:
                products.append({
                    "sku": product.get("sku", ""),
                    "data": {
                        "title": product.get("name", ""),
                        "price": float(product.get("price", 0)),
                        "quantity": int(product.get("quantity", 0)),
                        "status": "active" if product.get("status") == "1" else "inactive",
                        "platform_id": product.get("product_id"),
                        "last_updated": product.get("date_modified", "")
                    }
                })
                
        return products
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in OpenCart
        
        Args:
            product_data: Product data to update
                - sku: Product SKU
                - data: Product data to update
                    - price: New price
                    - quantity: New quantity
                    - status: New status
                    
        Returns:
            Update result
        """
        sku = product_data.get("sku")
        if not sku:
            raise ValueError("SKU is required for product update")
            
        data = product_data.get("data", {})
        if not data:
            raise ValueError("No data provided for update")
            
        # Find product by SKU
        products = await self.get_products(sku=sku)
        if not products:
            raise APIError(f"Product with SKU {sku} not found")
            
        product_id = products[0]["data"]["platform_id"]
        
        # Prepare update data
        update_data = {}
        
        if "price" in data:
            update_data["price"] = data["price"]
            
        if "quantity" in data:
            update_data["quantity"] = data["quantity"]
            
        if "status" in data:
            update_data["status"] = 1 if data["status"] == "active" else 0
            
        # Make update request
        response = await self._make_request(
            method="PUT",
            url=f"{self.api_url}/api/products/{product_id}",
            headers=self.headers,
            json=update_data
        )
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }