"""
Magento API client
"""

import aiohttp
import json
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class MagentoClient(BaseAPIClient):
    """Client for Magento API"""
    
    def __init__(self):
        """Initialize the Magento client"""
        super().__init__()
        self.api_url = None
        self.access_token = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.api_url = os.getenv("MAGENTO_URL")
        self.access_token = os.getenv("MAGENTO_ACCESS_TOKEN")
        
        if not self.api_url:
            logger.warning("MAGENTO_URL environment variable not set")
        if not self.access_token:
            logger.warning("MAGENTO_ACCESS_TOKEN environment variable not set")
            
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Magento API"""
        if not self.api_url or not self.access_token:
            raise AuthenticationError("Magento API URL or access token not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=f"{self.api_url}/rest/V1/products",
                headers=self.headers,
                params={"searchCriteria[pageSize]": 1}
            )
            
            self.authenticated = True
            logger.info("Magento authentication successful")
            
        except Exception as e:
            logger.error(f"Magento authentication failed: {str(e)}")
            raise AuthenticationError(f"Magento authentication failed: {str(e)}")
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get products from Magento
        
        Args:
            **kwargs: Optional filters
                - limit: Maximum number of products to return
                - page: Page number
                - sku: Filter by SKU
                
        Returns:
            List of products
        """
        params = {"searchCriteria": {"filterGroups": [{"filters": [{}]}]}}
        
        # Add filters
        if "limit" in kwargs:
            params["searchCriteria[pageSize]"] = kwargs["limit"]
        if "page" in kwargs:
            params["searchCriteria[currentPage]"] = kwargs["page"]
        if "sku" in kwargs:
            params["searchCriteria"]["filterGroups"][0]["filters"][0]["field"] = "sku"
            params["searchCriteria"]["filterGroups"][0]["filters"][0]["value"] = kwargs["sku"]
            params["searchCriteria"]["filterGroups"][0]["filters"][0]["conditionType"] = "eq"
            
        # Make request
        response = await self._make_request(
            method="GET",
            url=f"{self.api_url}/rest/V1/products",
            headers=self.headers,
            params=params
        )
        
        # Extract products
        products = []
        if isinstance(response, dict) and "items" in response:
            for product in response["items"]:
                products.append({
                    "sku": product.get("sku", ""),
                    "data": {
                        "title": product.get("name", ""),
                        "price": float(product.get("price", 0)),
                        "quantity": int(product.get("extension_attributes", {}).get("stock_item", {}).get("qty", 0)),
                        "status": "active" if product.get("status") == 1 else "inactive",
                        "platform_id": product.get("id"),
                        "last_updated": product.get("updated_at", "")
                    }
                })
                
        return products
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in Magento
        
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
            
        # Prepare update data
        update_data = {
            "product": {
                "sku": sku
            }
        }
        
        if "price" in data:
            update_data["product"]["price"] = data["price"]
            
        if "status" in data:
            update_data["product"]["status"] = 1 if data["status"] == "active" else 2
            
        # Make update request for product data
        if "price" in data or "status" in data:
            await self._make_request(
                method="PUT",
                url=f"{self.api_url}/rest/V1/products/{sku}",
                headers=self.headers,
                json=update_data
            )
            
        # Update stock separately if quantity is provided
        if "quantity" in data:
            stock_data = {
                "stockItem": {
                    "qty": data["quantity"],
                    "is_in_stock": data["quantity"] > 0
                }
            }
            
            await self._make_request(
                method="PUT",
                url=f"{self.api_url}/rest/V1/products/{sku}/stockItems/1",
                headers=self.headers,
                json=stock_data
            )
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }