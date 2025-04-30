"""
Handles WooCommerce product management
"""

import os
from typing import Dict, List, Any, Optional, cast
from datetime import datetime
from woocommerce import API
from core.exceptions import APIError, AuthenticationError
from core.logger import logger
from .base_client import BaseAPIClient

class WordPressClient(BaseAPIClient):
    """WordPress/WooCommerce API Client"""
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self.logger = logger

    async def authenticate(self) -> None:
        """Authenticate with WordPress/WooCommerce API using consumer credentials"""
        try:
            # Create auth dict with explicit type casting
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            test_response = await self._make_request(
                endpoint="/wp-json/wc/v3/products",
                auth=auth,
                params={'per_page': 1}
            )
            
            if not test_response or not isinstance(test_response, list):
                raise AuthenticationError("WordPress/WooCommerce authentication failed")
                
            self.logger.info("WordPress/WooCommerce authentication successful")
            
        except Exception as e:
            self.logger.error(f"WordPress/WooCommerce authentication failed: {str(e)}")
            raise AuthenticationError(f"WordPress/WooCommerce authentication failed: {str(e)}")

    def _setup_credentials(self) -> None:
        """Setup WooCommerce API credentials"""
        self.site_url = os.getenv('WP_SITE_URL')
        self.consumer_key = os.getenv('WC_CONSUMER_KEY')
        self.consumer_secret = os.getenv('WC_CONSUMER_SECRET')
        
        if not all([self.site_url, self.consumer_key, self.consumer_secret]):
            raise AuthenticationError("Missing WordPress/WooCommerce API credentials")
            
        # Initialize WooCommerce API client
        self.wcapi = API(
            url=str(self.site_url),
            consumer_key=str(self.consumer_key),
            consumer_secret=str(self.consumer_secret),
            version="wc/v3"
        )
        
        # Set base URL
        self.base_url = str(self.site_url)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from WooCommerce"""
        try:
            params = {
                'page': kwargs.get('page', 1),
                'per_page': kwargs.get('size', 100),
                'status': kwargs.get('status', 'publish')
            }
            
            # WooCommerce API doesn't support async, so we run it in a thread
            response = await self._make_request(
                endpoint="/wp-json/wc/v3/products",
                params=params,
                auth={
                    'consumer_key': str(self.consumer_key),
                    'consumer_secret': str(self.consumer_secret)
                }
            )
            
            products = []
            for item in response:
                product = self._format_product(item)
                if product:
                    products.append(product)
                    
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to fetch products: {str(e)}")
            raise APIError(f"Failed to fetch products: {str(e)}")

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data"""
        try:
            return {
                'sku': item.get('sku', ''),
                'data': {
                    'title': item.get('name', ''),
                    'description': item.get('description', ''),
                    'price': float(item.get('regular_price', 0)),
                    'sale_price': float(item.get('sale_price', 0)),
                    'quantity': int(item.get('stock_quantity', 0)),
                    'category': [cat.get('name', '') for cat in item.get('categories', [])],
                    'images': [img.get('src', '') for img in item.get('images', [])],
                    'attributes': item.get('attributes', []),
                    'status': item.get('status', ''),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting product: {str(e)}")
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on WooCommerce"""
        try:
            sku = product_data.get('sku', '')
            data = product_data.get('data', {})
            
            # First, find product ID by SKU
            product_id = await self._get_product_id_by_sku(sku)
            if not product_id:
                raise APIError(f"Product with SKU {sku} not found")
            
            update_data = {
                'name': data.get('title', ''),
                'regular_price': str(data.get('price', 0)),
                'stock_quantity': data.get('quantity', 0),
                'description': data.get('description', ''),
                'images': [{'src': img} for img in data.get('images', [])]
            }
            
            # Update product
            response = await self._make_request(
                endpoint=f"/wp-json/wc/v3/products/{product_id}",
                method="PUT",
                data=update_data,
                auth={
                    'consumer_key': str(self.consumer_key),
                    'consumer_secret': str(self.consumer_secret)
                }
            )
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Failed to update product {sku}: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")

    async def _get_product_id_by_sku(self, sku: str) -> Optional[int]:
        """Get WooCommerce product ID by SKU"""
        try:
            response = await self._make_request(
                endpoint="/wp-json/wc/v3/products",
                params={'sku': sku},
                auth={
                    'consumer_key': str(self.consumer_key),
                    'consumer_secret': str(self.consumer_secret)
                }
            )
            
            if response and isinstance(response, list) and len(response) > 0:
                return int(response[0].get('id', 0))
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting product ID for SKU {sku}: {str(e)}")
            return None
