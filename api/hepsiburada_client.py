"""
Hepsiburada API client
"""

import aiohttp
import json
import base64
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
        if self.username and self.password:
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
        if not self.username or not self.password or not self.merchant_id:
            raise AuthenticationError("Hepsiburada credentials not set")
            
        try:
            # Test authentication with a simple request
            await self._make_request(
                method="GET",
                url=f"https://listing-external.hepsiburada.com/listings/merchantid/{self.merchant_id}",
                headers=self.headers,
                params={"offset": 0, "limit": 1000}
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
                - offset: Offset for pagination (default: 0)
                - limit: Page size (default: 10)
                - hbSkuList: Filter by Hepsiburada SKU list
                - merchantSkuList: Filter by merchant SKU list
                - salable-listings: Filter salable listings (boolean)
                - notsalable-listings: Filter not salable listings (boolean)
                - updateStartDate: Filter by update start date
                - updateEndDate: Filter by update end date
                - force_refresh: Force refresh from API
                
        Returns:
            Dictionary with products and pagination info
        """
        # Build query parameters
        params = {}
        
        # Add required pagination parameters
        params["offset"] = kwargs.get("offset", 0)
        params["limit"] = kwargs.get("limit", 10)
        
        # Add optional filters
        optional_params = [
            "hbSkuList", "merchantSkuList", "salable-listings", 
            "notsalable-listings", "updateStartDate", "updateEndDate"
        ]
        
        for param in optional_params:
            if param in kwargs:
                params[param] = kwargs[param]
            
        # Make request
        response = await self._make_request(
            method="GET",
            url=f"https://listing-external.hepsiburada.com/listings/merchantid/{self.merchant_id}",
            headers=self.headers,
            params=params
        )
        
        # Extract products
        products = []
        total_count = 0
        
        if isinstance(response, dict):
            # Get total count if available
            total_count = response.get("totalCount", 0)
            
            # Process product data
            if "listings" in response and isinstance(response["listings"], list):
                for item in response["listings"]:
                    # Map Hepsiburada product data to our standard format
                    product = {
                        "sku": item.get("MerchantSku", ""),
                        "data": {
                            "title": item.get("ProductName", ""),
                            "price": float(item.get("Price", 0)),
                            "quantity": int(item.get("AvailableStock", 0)),
                            "status": "active" if item.get("IsSalable", False) else "inactive",
                            "platform_id": item.get("HepsiburadaSku"),
                            "hepsiburada_sku": item.get("HepsiburadaSku"),
                            "merchant_sku": item.get("MerchantSku"),
                            "dispatch_time": item.get("DispatchTime"),
                            "cargo_company1": item.get("CargoCompany1"),
                            "cargo_company2": item.get("CargoCompany2"),
                            "cargo_company3": item.get("CargoCompany3"),
                            "shipping_address_label": item.get("ShippingAddressLabel"),
                            "shipping_profile_name": item.get("shippingProfileName"),
                            "claim_address_label": item.get("ClaimAddressLabel"),
                            "final_price": item.get("Pricing", {}).get("FinalPrice"),
                            "pricing_start_date": item.get("Pricing", {}).get("StartDate"),
                            "pricing_end_date": item.get("Pricing", {}).get("EndDate"),
                            "pricing_debtor": item.get("Pricing", {}).get("Debtor"),
                            "pricing_amount": item.get("Pricing", {}).get("Amount"),
                            "maximum_purchasable_quantity": item.get("MaximumPurchasableQuantity"),
                            "is_salable": item.get("IsSalable", False),
                            "customizable_properties": item.get("CustomizableProperties"),
                            "is_suspended": item.get("IsSuspended", False),
                            "is_locked": item.get("IsLocked", False),
                            "lock_reasons": item.get("LockReasons"),
                            "is_frozen": item.get("IsFrozen", False),
                            "commission_rate": item.get("CommissionRate"),
                            "price_increase_disabled": item.get("priceIncreaseDisabled", False),
                            "price_decrease_disabled": item.get("priceDecreaseDisabled", False),
                            "stock_decrease_disabled": item.get("stockDecreaseDisabled", False)
                        }
                    }
                    
                    products.append(product)
        
        # Calculate pagination info
        page_size = params["limit"]
        current_offset = params["offset"]
        current_page = (current_offset // page_size) + 1
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Return paginated result with metadata
        return {
            "items": products,
            "total": total_count,
            "page": current_page,
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
                    - quantity: New quantity (AvailableStock)
                    - status: New status (IsSalable)
                    
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
            "MerchantSku": sku
        }
        
        if "price" in data:
            update_data["Price"] = data["price"]
        
        if "quantity" in data:
            update_data["AvailableStock"] = data["quantity"]
        
        if "status" in data:
            update_data["IsSalable"] = data["status"] == "active"
        
        # Make update request
        response = await self._make_request(
            method="PUT",
            url=f"https://listing-external.hepsiburada.com/listings/merchantid/{self.merchant_id}/merchantsku/{sku}",
            headers=self.headers,
            json=update_data
        )
        
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }