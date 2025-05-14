"""
Amazon API client
"""

import aiohttp
import json
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError
from api.base_client import BaseAPIClient
from core.error_handler import handle_exceptions

class AmazonClient(BaseAPIClient):
    """Client for Amazon Marketplace Web Service (MWS) API"""
    
    def __init__(self):
        """Initialize the Amazon client"""
        super().__init__()
        self.access_key = None
        self.secret_key = None
        self.seller_id = None
        self.marketplace_id = None
        self.region = None
        self.api_version = "2011-10-01"
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup API credentials from environment variables"""
        import os
        self.access_key = os.getenv("AMAZON_ACCESS_KEY")
        self.secret_key = os.getenv("AMAZON_SECRET_KEY")
        self.seller_id = os.getenv("AMAZON_SELLER_ID")
        self.marketplace_id = os.getenv("AMAZON_MARKETPLACE_ID")
        self.region = os.getenv("AMAZON_REGION", "us-east-1")
        
        if not self.access_key:
            logger.warning("AMAZON_ACCESS_KEY environment variable not set")
        if not self.secret_key:
            logger.warning("AMAZON_SECRET_KEY environment variable not set")
        if not self.seller_id:
            logger.warning("AMAZON_SELLER_ID environment variable not set")
        if not self.marketplace_id:
            logger.warning("AMAZON_MARKETPLACE_ID environment variable not set")
            
        # Set API endpoint based on region
        region_endpoints = {
            "us-east-1": "mws.amazonservices.com",
            "eu-west-1": "mws-eu.amazonservices.com",
            "ap-southeast-1": "mws-fe.amazonservices.com"
        }
        
        self.endpoint = region_endpoints.get(self.region, "mws.amazonservices.com")
        self.base_url = f"https://{self.endpoint}"
    
    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Amazon MWS API"""
        if not self.access_key or not self.secret_key or not self.seller_id:
            raise AuthenticationError("Amazon MWS credentials not set")
            
        try:
            # Test authentication with a simple request
            params = {
                "Action": "GetServiceStatus",
                "SellerId": self.seller_id,
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            # Make request
            response = await self._make_mws_request(
                method="GET",
                path="/Products/2011-10-01",
                params=params
            )
            
            self.authenticated = True
            logger.info("Amazon MWS authentication successful")
            
        except Exception as e:
            logger.error(f"Amazon MWS authentication failed: {str(e)}")
            raise AuthenticationError(f"Amazon MWS authentication failed: {str(e)}")
    
    async def _make_mws_request(self, method: str, path: str, params: Dict[str, str]) -> Any:
        """
        Make a request to Amazon MWS API with authentication
        
        Args:
            method: HTTP method
            path: API path
            params: Request parameters
            
        Returns:
            Response data
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create canonical query string
        canonical_query_string = "&".join([
            f"{urllib.parse.quote(k)}={urllib.parse.quote(str(v))}"
            for k, v in sorted_params
        ])
        
        # Create string to sign
        string_to_sign = f"{method}\n{self.endpoint}\n{path}\n{canonical_query_string}"
        
        # Calculate signature
        signature = base64.b64encode(
            hmac.new(
                (self.secret_key or "").encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        
        # Add signature to parameters
        params["Signature"] = signature
        
        # Make request
        url = f"{self.base_url}{path}"
        
        if method == "GET":
            response = await self._make_request(
                method="GET",
                url=url,
                params=params
            )
        else:
            response = await self._make_request(
                method=method,
                url=url,
                data=urllib.parse.urlencode(params)
            )
            
        return response
    
    @handle_exceptions
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get products from Amazon
        
        Args:
            **kwargs: Optional filters
                - sku: Filter by SKU
                
        Returns:
            List of products
        """
        products = []
        
        # If SKU is provided, get specific product
        if "sku" in kwargs:
            sku = kwargs["sku"]
            
            params = {
                "Action": "GetMatchingProductForId",
                "SellerId": self.seller_id,
                "MarketplaceId": self.marketplace_id,
                "IdType": "SellerSKU",
                "IdList.Id.1": sku,
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            # Get product data
            product_response = await self._make_mws_request(
                method="GET",
                path="/Products/2011-10-01",
                params=params
            )
            
            # Get inventory data
            inventory_params = {
                "Action": "ListInventorySupply",
                "SellerId": self.seller_id,
                "MarketplaceId": self.marketplace_id,
                "SellerSkus.member.1": sku,
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            inventory_response = await self._make_mws_request(
                method="GET",
                path="/FulfillmentInventory/2010-10-01",
                params=inventory_params
            )
            
            # Parse responses and add product
            product = self._parse_product(product_response, inventory_response, sku)
            if product:
                products.append(product)
                
        else:
            # Get list of SKUs
            params = {
                "Action": "ListInventorySupply",
                "SellerId": self.seller_id,
                "MarketplaceId": self.marketplace_id,
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            # Add pagination parameters
            if "limit" in kwargs:
                params["MaxResultsPerPage"] = str(kwargs["limit"])
            
            inventory_response = await self._make_mws_request(
                method="GET",
                path="/FulfillmentInventory/2010-10-01",
                params=params
            )
            
            # Extract SKUs from inventory response
            skus = self._extract_skus_from_inventory(inventory_response)
            
            # Get product data for each SKU
            for sku in skus:
                product_params = {
                    "Action": "GetMatchingProductForId",
                    "SellerId": self.seller_id,
                    "MarketplaceId": self.marketplace_id,
                    "IdType": "SellerSKU",
                    "IdList.Id.1": sku,
                    "SignatureMethod": "HmacSHA256",
                    "SignatureVersion": "2",
                    "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "Version": self.api_version,
                    "AWSAccessKeyId": self.access_key
                }
                
                product_response = await self._make_mws_request(
                    method="GET",
                    path="/Products/2011-10-01",
                    params=product_params
                )
                
                # Parse response and add product
                product = self._parse_product(product_response, inventory_response, sku)
                if product:
                    products.append(product)
                    
        return products
    
    def _extract_skus_from_inventory(self, inventory_response: str) -> List[str]:
        """
        Extract SKUs from inventory response
        
        Args:
            inventory_response: Inventory response XML
            
        Returns:
            List of SKUs
        """
        skus = []
        
        try:
            # Parse XML response
            root = ET.fromstring(inventory_response)
            
            # Extract SKUs
            namespace = {"ns": "http://mws.amazonaws.com/FulfillmentInventory/2010-10-01"}
            for item in root.findall(".//ns:SellerSKU", namespace):
                skus.append(item.text)
                
        except Exception as e:
            logger.error(f"Error extracting SKUs from inventory response: {str(e)}")
            
        return skus
    
    def _parse_product(self, product_response: str, inventory_response: str, sku: str) -> Optional[Dict[str, Any]]:
        """
        Parse product and inventory responses
        
        Args:
            product_response: Product response XML
            inventory_response: Inventory response XML
            sku: Product SKU
            
        Returns:
            Parsed product data
        """
        try:
            # Parse product XML
            product_root = ET.fromstring(product_response)
            
            # Extract product data
            product_namespace = {"ns": "http://mws.amazonaws.com/schema/Products/2011-10-01"}
            product_result = product_root.find(".//ns:Product", product_namespace)
            
            if product_result is None:
                return None
                
            # Get product attributes
            attributes = product_result.find(".//ns:AttributeSets", product_namespace)
            title = None
            if attributes is not None:
                title = attributes.find(".//ns:Title", product_namespace)
            title_text = title.text if title is not None else ""
            
            # Parse inventory XML
            inventory_root = ET.fromstring(inventory_response)
            
            # Find inventory item for this SKU
            inventory_namespace = {"ns": "http://mws.amazonaws.com/FulfillmentInventory/2010-10-01"}
            inventory_item = None
            
            for item in inventory_root.findall(".//ns:InventorySupplyDetail", inventory_namespace):
                item_sku = item.find(".//ns:SellerSKU", inventory_namespace)
                if item_sku is not None and item_sku.text == sku:
                    inventory_item = item
                    break
                    
            # Get quantity
            quantity = 0
            if inventory_item is not None:
                quantity_elem = inventory_item.find(".//ns:Quantity", inventory_namespace)
                if quantity_elem is not None:
                    quantity = int(quantity_elem.text) if quantity_elem.text is not None else 0
                    
            # Get status
            status = "inactive"
            if inventory_item is not None:
                status_elem = inventory_item.find(".//ns:InStockSupplyQuantity", inventory_namespace)
                if status_elem is not None and status_elem.text is not None and int(status_elem.text) > 0:
                    status = "active"
                    
            # Return formatted product
            return {
                "sku": sku,
                "data": {
                    "title": title_text,
                    "price": 0.0,  # Price not available in this API call
                    "quantity": quantity,
                    "status": status,
                    "platform_id": sku,
                    "last_updated": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing product response: {str(e)}")
            return None
    
    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product in Amazon
        
        Args:
            product_data: Product data to update
                - sku: Product SKU
                - data: Product data to update
                    - price: New price
                    - quantity: New quantity
                    
        Returns:
            Update result
        """
        sku = product_data.get("sku")
        if not sku:
            raise ValueError("SKU is required for product update")
            
        data = product_data.get("data", {})
        if not data:
            raise ValueError("No data provided for update")
            
        # Update quantity if provided
        if "quantity" in data:
            quantity = data["quantity"]
            
            params = {
                "Action": "UpdateInventoryAvailability",
                "SellerId": self.seller_id,
                "MarketplaceId": self.marketplace_id,
                "SellerSKU": sku,
                "Quantity": str(quantity),
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            await self._make_mws_request(
                method="POST",
                path="/FulfillmentInventory/2010-10-01",
                params=params
            )
            
        # Update price if provided
        if "price" in data:
            price = data["price"]
            
            params = {
                "Action": "UpdatePrice",
                "SellerId": self.seller_id,
                "MarketplaceId": self.marketplace_id,
                "SKU": sku,
                "Price": str(price),
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": self.api_version,
                "AWSAccessKeyId": self.access_key
            }
            
            await self._make_mws_request(
                method="POST",
                path="/Products/2011-10-01",
                params=params
            )
            
        return {
            "sku": sku,
            "status": "success",
            "message": "Product updated successfully"
        }
