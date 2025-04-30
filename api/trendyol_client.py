# api/trendyol_client.py
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

class TrendyolClient(BaseAPIClient):
    """Trendyol API Client implementation"""
    
    def __init__(self):
        super().__init__()
        # Initialize credentials
        self.store_id = os.getenv('TRENDYOL_STORE_ID')
        self.auth_hash = os.getenv('TRENDYOL_AUTH_HASH')
        
        if not all([self.store_id, self.auth_hash]):
            raise AuthenticationError("Missing Trendyol API credentials")
            
        # API configuration
        self.base_url = "https://api.trendyol.com/sapigw/suppliers"
        self.batch_size = 100
        self.max_retries = 3
        self.rate_limit_wait = 15
        self.request_timeout = 30
        
        # Set headers
        self.headers = {
            'User-Agent': f'{self.store_id} - Integration',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.auth_hash}'
        }

    async def authenticate(self) -> None:
        """Authenticate with Trendyol API"""
        try:
            # Test authentication with a simple request
            test_response = await self._make_request(
                endpoint="/products",
                params={'page': 0, 'size': 1}
            )
            
            if not test_response or 'totalElements' not in test_response:
                raise AuthenticationError("Trendyol authentication failed")
                
            logger.info("Trendyol authentication successful")
            
        except Exception as e:
            logger.error(f"Trendyol authentication failed: {str(e)}")
            raise AuthenticationError(f"Trendyol authentication failed: {str(e)}")

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from Trendyol"""
        try:
            page = kwargs.get('page', 0)
            size = kwargs.get('size', self.batch_size)
            filters = kwargs.get('filters', '')
            
            products: List[Dict[str, Any]] = []
            
            while True:
                uri_addon = f"?page={page}&size={size}{filters}"
                response = await self._make_request(
                    endpoint=f"/products{uri_addon}"
                )
                
                if not response.get('content'):
                    break
                    
                for item in response['content']:
                    product = self._format_product(item)
                    if product:
                        products.append(product)
                
                if page >= int(response['totalPages']) - 1:
                    break
                    
                page += 1
            
            logger.info(f"Retrieved {len(products)} products from Trendyol")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            raise APIError(f"Failed to fetch products: {str(e)}")

    async def update_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on Trendyol"""
        try:
            payload = {
                "items": [{
                    "barcode": product['id'],
                    "quantity": int(product['quantity']),
                    "salePrice": float(product['price'])
                }]
            }
            
            response = await self._make_request(
                endpoint="/products/price-and-inventory",
                method="POST",
                data=payload
            )
            
            batch_status = await self._wait_for_batch_completion(
                response['batchRequestId']
            )
            
            if not batch_status['items']:
                raise APIError("No status received for batch update")
                
            status = batch_status['items'][0]['status']
            
            if status == 'SUCCESS':
                logger.info(
                    f'Product {product["sku"]} updated: '
                    f'quantity {product["quantity"]}, price {product["price"]}'
                )
                return product
            else:
                error_msg = batch_status["items"][0].get("failureReasons", ["Unknown error"])[0]
                raise APIError(f"Failed to update product: {error_msg}")
                
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
        url = f"{self.base_url}/{self.store_id}{endpoint}"
        
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
                        if response.status == 429:  # Rate limit
                            logger.warning("Rate limit reached, waiting...")
                            await asyncio.sleep(self.rate_limit_wait)
                            continue
                            
                        response.raise_for_status()
                        return await response.json()
                        
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")
                    
                logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        raise APIError(f"Request failed after {self.max_retries} attempts")

    async def _wait_for_batch_completion(self, batch_id: str) -> Dict[str, Any]:
        """Wait for batch request completion"""
        while True:
            response = await self._make_request(
                endpoint=f'/products/batch-requests/{batch_id}'
            )
            
            if not response.get('items'):
                await asyncio.sleep(1)
                continue
                
            status = response['items'][0].get('status')
            if status == 'SUCCESS':
                return response
            elif status == 'FAILED':
                raise APIError(
                    f"Batch request failed: {response['items'][0].get('failureReasons', ['Unknown error'])}"
                )
                
            await asyncio.sleep(1)

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data to standard format"""
        try:
            return {
                'sku': item.get('stockCode') or item.get('barcode'),
                'id': item.get('barcode'),
                'quantity': int(item.get('quantity', 0)),
                'price': float(item.get('salePrice', 0.0)),
                'data': {
                    'title': item.get('title'),
                    'description': item.get('description', ''),
                    'images': [img.get('url') for img in item.get('images', [])],
                    'category': item.get('categoryName'),
                    'brand': item.get('brand', ''),
                    'status': item.get('status'),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error formatting product: {str(e)}")
            return None
