"""
Handles product management and inventory operations
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
from core.exceptions import APIError, AuthenticationError
from core.logger import logger
from .base_client import BaseAPIClient

class PTTAVMClient(BaseAPIClient):
    """PTTAVM API Client"""
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self._setup_endpoints()
        self.logger = logger

    def _setup_credentials(self) -> None:
        """Setup API credentials"""
        self.api_key = os.getenv('PTTAVM_API_KEY')
        self.api_secret = os.getenv('PTTAVM_API_SECRET')
        self.shop_id = os.getenv('PTTAVM_SHOP_ID')
        
        if not all([self.api_key, self.api_secret, self.shop_id]):
            raise AuthenticationError("Missing PTTAVM API credentials")
            
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Shop-Id": self.shop_id
        }

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        self.base_url = "https://api.epttavm.com/v2"
        self.endpoints = {
            'products': '/products',
            'stock': '/stock',
            'orders': '/orders',
            'categories': '/categories'
        }

    async def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Any = None,
        params: Dict[str, Any] = None,
        retry_count: int = 3
    ) -> Any:
        """Make API request with retry mechanism"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=30
                    ) as response:
                        response_data = await response.json()
                        
                        # Log request
                        self.logger.log_api_request(
                            method=method,
                            url=url,
                            status_code=response.status,
                            response_size=len(str(response_data))
                        )
                        
                        if response.status == 200:
                            return response_data
                            
                        if response.status == 401:
                            raise AuthenticationError("Invalid credentials")
                            
                        raise APIError(f"Request failed: {response_data}")
                        
            except Exception as e:
                if attempt == retry_count - 1:
                    raise APIError(f"Request failed after {retry_count} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from PTTAVM"""
        try:
            params = {
                'page': kwargs.get('page', 1),
                'limit': kwargs.get('size', 100),
                'status': kwargs.get('status', 'active')
            }
            
            response = await self._make_request(
                endpoint=self.endpoints['products'],
                params=params
            )
            
            products = []
            for item in response.get('data', []):
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
                'sku': item.get('stockCode'),
                'data': {
                    'title': item.get('name'),
                    'description': item.get('description'),
                    'price': float(item.get('price', 0)),
                    'quantity': int(item.get('stock', 0)),
                    'category': item.get('category', {}).get('name'),
                    'brand': item.get('brand'),
                    'images': item.get('images', []),
                    'attributes': item.get('attributes', {}),
                    'status': item.get('status'),
                    'barcode': item.get('barcode'),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting product: {str(e)}")
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on PTTAVM"""
        try:
            sku = product_data['sku']
            data = product_data['data']
            
            update_data = {
                'stockCode': sku,
                'name': data['title'],
                'price': data['price'],
                'stock': data['quantity'],
                'description': data.get('description', ''),
                'images': data.get('images', []),
                'attributes': data.get('attributes', {})
            }
            
            await self._make_request(
                endpoint=f"{self.endpoints['products']}/{sku}",
                method='PUT',
                data=update_data
            )
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Failed to update product {sku}: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get PTTAVM categories"""
        try:
            response = await self._make_request(
                endpoint=self.endpoints['categories']
            )
            return response.get('data', [])
        except Exception as e:
            self.logger.error(f"Failed to fetch categories: {str(e)}")
            raise APIError(f"Failed to fetch categories: {str(e)}")
