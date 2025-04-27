"""
Handles WooCommerce product management
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
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

    def _setup_credentials(self) -> None:
        """Setup WooCommerce API credentials"""
        self.site_url = os.getenv('WP_SITE_URL')
        self.consumer_key = os.getenv('WC_CONSUMER_KEY')
        self.consumer_secret = os.getenv('WC_CONSUMER_SECRET')
        
        if not all([self.site_url, self.consumer_key, self.consumer_secret]):
            raise AuthenticationError("Missing WordPress/WooCommerce API credentials")
            
        self.wcapi = API(
            url=self.site_url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version="wc/v3"
        )

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from WooCommerce"""
        try:
            params = {
                'page': kwargs.get('page', 1),
                'per_page': kwargs.get('size', 100),
                'status': kwargs.get('status', 'publish')
            }
            
            # WooCommerce API doesn't support async, so we run it in a thread
            response = await asyncio.to_thread(
                self.wcapi.get,
                "products",
                params=params
            )
            
            if response.status_code != 200:
                raise APIError(f"Failed to fetch products: {response.text}")
            
            products = []
            for item in response.json():
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
                'sku': item.get('sku'),
                'data': {
                    'title': item.get('name'),
                    'description': item.get('description'),
                    'price': float(item.get('regular_price', 0)),
                    'sale_price': float(item.get('sale_price', 0)),
                    'quantity': int(item.get('stock_quantity', 0)),
                    'category': [cat['name'] for cat in item.get('categories', [])],
                    'images': [img['src'] for img in item.get('images', [])],
                    'attributes': item.get('attributes', []),
                    'status': item.get('status'),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting product: {str(e)}")
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on WooCommerce"""
        try:
            sku = product_data['sku']
            data = product_data['data']
            
            # First, find product ID by SKU
            product_id = await self._get_product_id_by_sku(sku)
            if not product_id:
                raise APIError(f"Product with SKU {sku} not found")
            
            update_data = {
                'name': data['title'],
                'regular_price': str(data['price']),
                'stock_quantity': data['quantity'],
                'description': data.get('description', ''),
                'images': [{'src': img} for img in data.get('images', [])]
            }
            
            # Update product
            response = await asyncio.to_thread(
                self.wcapi.put,
                f"products/{product_id}",
                update_data
            )
            
            if response.status_code not in [200, 201]:
                raise APIError(f"Failed to update product: {response.text}")
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Failed to update product {sku}: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")

    async def _get_product_id_by_sku(self, sku: str) -> Optional[int]:
        """Get WooCommerce product ID by SKU"""
        try:
            response = await asyncio.to_thread(
                self.wcapi.get,
                "products",
                params={'sku': sku}
            )
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    return products[0]['id']
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting product ID for SKU {sku}: {str(e)}")
            return None

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get WooCommerce categories"""
        try:
            response = await asyncio.to_thread(
                self.wcapi.get,
                "products/categories",
                params={'per_page': 100}
            )
            
            if response.status_code != 200:
                raise APIError(f"Failed to fetch categories: {response.text}")
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to fetch categories: {str(e)}")
            raise APIError(f"Failed to fetch categories: {str(e)}")
