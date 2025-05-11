"""
N11 API client
"""

import aiohttp
import json
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class N11Client(BaseAPIClient):
    """Client for N11 API"""
    
    def __init__(self):
        """Initialize the N11 client"""
        super().__init__()
        self.api_url = "https://api.n11.com/ms/product-query"
        self.app_key = None
        self.app_secret = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.app_key = os.getenv("N11_APP_KEY")
        self.app_secret = os.getenv("N11_APP_SECRET")
        
        if not self.app_key:
            logger.warning("N11_APP_KEY environment variable not set")
        if not self.app_secret:
            logger.warning("N11_APP_SECRET environment variable not set")
            
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with N11 API"""
        if not self.app_key or not self.app_secret:
            raise AuthenticationError("N11 API key or secret not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=self.api_url,
                headers=self.headers,
                params={"size": 1}
            )
            
            self.authenticated = True
            logger.info("N11 authentication successful")
            
        except Exception as e:
            logger.error(f"N11 authentication failed: {str(e)}")
            raise AuthenticationError(f"N11 authentication failed: {str(e)}")
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> Dict[str, Any]:
        """
        Get products from N11
        
        Args:
            **kwargs: Optional filters
                - id: N11 Product ID (long)
                - productMainId: Group code (string)
                - stockCode: Seller product code (string)
                - saleStatus: Sale status (On_Sale, Out_Of_Stock)
                - productStatus: Product approval status (Active, InCatalogApproval, Suspended, CatalogRejected, Prohibited, Unlisted)
                - brandName: Brand name (string)
                - categoryIds: Category IDs (list of long)
                - page: Page number (default: 0)
                - size: Page size (default: 250, max: 250)
                - get_all: Whether to fetch all pages (default: True)
                - force_refresh: Force refresh from API
                
        Returns:
            Dictionary with products and pagination info
        """
        # Build query parameters
        params = {}
        
        # Add optional filters
        optional_params = [
            "id", "productMainId", "stockCode", "saleStatus", 
            "productStatus", "brandName"
        ]
        
        for param in optional_params:
            if param in kwargs:
                params[param] = kwargs[param]
        
        # Handle category IDs
        if "categoryIds" in kwargs and isinstance(kwargs["categoryIds"], list):
            params["categoryIds"] = ",".join(map(str, kwargs["categoryIds"]))
        
        # Add pagination parameters (N11 uses 0-based indexing)
        page_size = min(kwargs.get("size", 250), 250)  # Maximum 250
        params["size"] = page_size
        
        # Check if we should get all pages
        get_all = kwargs.get("get_all", True)
        
        # If we're getting a specific page or not getting all pages
        if "page" in kwargs or not get_all:
            params["page"] = kwargs.get("page", 0)
            
            # Make request for a single page
            response = await self._make_request(
                method="GET",
                url=self.api_url,
                headers=self.headers,
                params=params
            )
            
            # Extract products
            products = []
            if isinstance(response, dict) and "content" in response:
                products = self._extract_products(response["content"])
                
                # Return paginated result with metadata
                return {
                    "items": products,
                    "total": response.get("totalElements", len(products)),
                    "page": response.get("number", params["page"]) + 1,  # Convert from 0-based to 1-based
                    "size": response.get("size", page_size),
                    "totalPages": response.get("totalPages", 1)
                }
            
            # Return empty result if no content
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "size": page_size,
                "totalPages": 0
            }
        else:
            # Get all pages
            all_products = []
            current_page = 0
            total_pages = 1  # Will be updated after first request
            total_elements = 0
            
            logger.info("Fetching all products from N11 (this may take a while)...")
            
            while current_page < total_pages:
                params["page"] = current_page
                
                # Make request
                response = await self._make_request(
                    method="GET",
                    url=self.api_url,
                    headers=self.headers,
                    params=params
                )
                
                # Extract products
                if isinstance(response, dict) and "content" in response:
                    page_products = self._extract_products(response["content"])
                    all_products.extend(page_products)
                    
                    # Update pagination info
                    total_pages = response.get("totalPages", 1)
                    total_elements = response.get("totalElements", 0)
                    
                    logger.info(f"Fetched page {current_page + 1}/{total_pages} from N11 ({len(page_products)} products)")
                    
                    # Move to next page
                    current_page += 1
                else:
                    # No more pages or error
                    break
            
            # Return all products with metadata
            return {
                "items": all_products,
                "total": total_elements,
                "page": 1,  # When getting all pages, we return as if it's a single page
                "size": len(all_products),
                "totalPages": 1
            }
    
    def _extract_products(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and format products from API response content"""
        products = []
        
        for item in content:
            # Map N11 product data to our standard format
            product = {
                "sku": item.get("stockCode", ""),
                "data": {
                    "title": item.get("title", ""),
                    "price": float(item.get("salePrice", 0)),
                    "list_price": float(item.get("listPrice", 0)),
                    "quantity": int(item.get("quantity", 0)),
                    "status": self._map_status(item.get("status", "")),
                    "platform_id": item.get("n11ProductId"),
                    "barcode": item.get("barcode"),
                    "seller_id": item.get("sellerId"),
                    "seller_nickname": item.get("sellerNickname"),
                    "description": item.get("description", ""),
                    "category_id": item.get("categoryId"),
                    "product_main_id": item.get("productMainId"),
                    "sale_status": item.get("saleStatus"),
                    "preparing_day": item.get("preparingDay"),
                    "shipment_template": item.get("shipmentTemplate"),
                    "max_purchase_quantity": item.get("maxPurchaseQuantity"),
                    "custom_text_options": item.get("customTextOptions", []),
                    "catalog_id": item.get("catalogId"),
                    "group_id": item.get("groupId"),
                    "currency_type": item.get("currencyType"),
                    "attributes": item.get("attributes", []),
                    "vat_rate": item.get("vatRate"),
                    "commission_rate": item.get("commissionRate")
                }
            }
            
            # Add image URLs if available
            if item.get("imageUrls") and len(item["imageUrls"]) > 0:
                product["data"]["image_url"] = item["imageUrls"][0]
                product["data"]["images"] = item["imageUrls"]
            
            products.append(product)
            
        return products
    
    def _map_status(self, status: str) -> str:
        """Map N11 status to standard status"""
        status_map = {
            "Active": "active",
            "InCatalogApproval": "pending",
            "Suspended": "inactive",
            "CatalogRejected": "inactive",
            "Unlisted": "inactive",
            "Prohibited": "inactive"
        }
        return status_map.get(status, "inactive")
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in N11
        
        Args:
            product_data: Product data to update
                - sku: Product SKU (stock code)
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
            "stockCode": sku
        }
        
        if "price" in data:
            update_data["price"] = data["price"]
            
        if "quantity" in data:
            update_data["quantity"] = data["quantity"]
            
        if "status" in data:
            update_data["productStatus"] = self._reverse_map_status(data["status"])
            
        # Make update request
        response = await self._make_request(
            method="PUT",
            url="https://api.n11.com/ms/product-update",
            headers=self.headers,
            json=update_data
        )
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }
    
    def _reverse_map_status(self, status: str) -> str:
        """Map standard status to N11 status"""
        reverse_map = {
            "active": "Active",
            "inactive": "Suspended",
            "pending": "InCatalogApproval"
        }
        return reverse_map.get(status, "Suspended")