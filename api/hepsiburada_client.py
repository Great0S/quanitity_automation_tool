# api/hepsiburada_client.py
import asyncio
import os
import json
import base64
from typing import Dict, List, Any, Optional
import aiohttp
from datetime import datetime
from core.exceptions import APIError, AuthenticationError
from core.logger import logger
from .base_client import BaseAPIClient

class HepsiburadaClient(BaseAPIClient):
    """Hepsiburada API Client implementation"""
    
    def __init__(self):
        super().__init__()
        # Initialize credentials
        self.merchant_id = os.getenv('HEPSIBURADA_MERCHANT_ID')
        self.api_key = os.getenv('HEPSIBURADA_API_KEY')
        
        if not all([self.merchant_id, self.api_key]):
            raise AuthenticationError("Missing Hepsiburada API credentials")
            
        # API configuration
        self.base_url = "https://api.hepsiburada.com"
        self.batch_size = 100
        self.max_retries = 3
        self.request_timeout = 30
        
        # Set headers
        self.headers = {
            'User-Agent': 'Integration/1.0',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        
        if self.merchant_id:
            self.headers['MerchantId'] = self.merchant_id

    async def authenticate(self) -> None:
        """Authenticate with Hepsiburada API"""
        try:
            # Test authentication with a simple request
            test_response = await self._make_request(
                endpoint="/listings/merchants/inventory",
                params={'offset': 0, 'limit': 1}
            )
            
            if not test_response or 'totalCount' not in test_response:
                raise AuthenticationError("Hepsiburada authentication failed")
                
            logger.info("Hepsiburada authentication successful")
            
        except Exception as e:
            logger.error(f"Hepsiburada authentication failed: {str(e)}")
            raise AuthenticationError(f"Hepsiburada authentication failed: {str(e)}")

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from Hepsiburada"""
        try:
            offset = kwargs.get('offset', 0)
            limit = kwargs.get('limit', self.batch_size)
            
            products: List[Dict[str, Any]] = []
            total_count = None
            
            while True:
                response = await self._make_request(
                    endpoint="/listings/merchants/inventory",
                    params={'offset': offset, 'limit': limit}
                )
                
                if not response.get('listings'):
                    break
                    
                if total_count is None:
                    total_count = response.get('totalCount', 0)
                
                for item in response['listings']:
                    product = self._format_product(item)
                    if product:
                        products.append(product)
                
                if offset + limit >= total_count:
                    break
                    
                offset += limit
            
            logger.info(f"Retrieved {len(products)} products from Hepsiburada")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            raise APIError(f"Failed to fetch products: {str(e)}")

    async def update_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on Hepsiburada"""
        try:
            payload = {
                "listings": [{
                    "merchantSku": product['sku'],
                    "price": str(product['price']),
                    "availableStock": int(product['quantity'])
                }]
            }
            
            response = await self._make_request(
                endpoint="/listings/merchantid/inventory-uploads",
                method="POST",
                data=payload
            )
            
            if response.get('status') != 'SUCCESS':
                raise APIError(f"Failed to update product: {response.get('message')}")
                
            logger.info(
                f'Product {product["sku"]} updated: '
                f'quantity {product["quantity"]}, price {product["price"]}'
            )
            return product
            
        except Exception as e:
            logger.error(f"Error updating product {product.get('sku')}: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make API request with retry mechanism"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                        
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")
                    
                logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        raise APIError(f"Request failed after {self.max_retries} attempts")

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data to standard format"""
        try:
            return {
                'sku': item.get('merchantSku'),
                'id': item.get('hbSku'),
                'quantity': int(item.get('availableStock', 0)),
                'price': float(item.get('price', 0.0)),
                'data': {
                    'title': item.get('name'),
                    'description': item.get('description', ''),
                    'images': item.get('images', []),
                    'category': item.get('category', {}).get('name'),
                    'brand': item.get('brand', {}).get('name'),
                    'status': item.get('status'),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error formatting product: {str(e)}")
            return None
