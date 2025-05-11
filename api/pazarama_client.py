"""
Handles product management and inventory operations
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
from .base_client import BaseAPIClient

class PazaramaClient(BaseAPIClient):
    """Pazarama API Client"""
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self._setup_endpoints()
        self.logger = logger
        self.retry_delay = 2  # seconds

    def _setup_credentials(self) -> None:
        """Setup API credentials"""
        self.api_key = os.getenv('PAZARAMA_API_KEY')
        self.api_secret = os.getenv('PAZARAMA_API_SECRET')
        self.seller_id = os.getenv('PAZARAMA_SELLER_ID')
        
        if not all([self.api_key, self.api_secret, self.seller_id]):
            logger.error("Missing Pazarama API credentials")
            raise AuthenticationError("Missing Pazarama API credentials")
            
        self.headers = {
            key: str(value) for key, value in {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key,
                "X-SELLER-ID": self.seller_id
            }.items() if value is not None
        }
        # Filter out any None values explicitly
        self.headers = {key: value for key, value in self.headers.items() if value is not None}
        
        # Log initialization (without sensitive data)
        logger.debug(f"Pazarama client initialized for seller ID: {self.seller_id}")

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        self.base_url = "https://api.pazarama.com"
        self.endpoints = {
            'products': '/products',
            'orders': '/orders',
            'categories': '/categories',
            'inventory': '/inventory'
        }
        logger.debug(f"Pazarama endpoints configured: {list(self.endpoints.keys())}")

    async def authenticate(self) -> None:
        """Authenticate with Pazarama API using API key"""
        try:
            logger.info("Authenticating with Pazarama API...")
            
            # Test authentication with a simple request
            try:
                test_response = await self._make_request(
                    endpoint=f"{self.endpoints['products']}",
                    params={'limit': 1}
                )
                
                if not test_response:
                    raise AuthenticationError("Pazarama authentication failed: Empty response")
                    
                logger.info("Pazarama authentication successful")
                
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Pazarama connection error: {str(e)}")
                raise NetworkError(f"Pazarama connection error: {str(e)}")
                
            except aiohttp.ClientResponseError as e:
                if e.status == 401 or e.status == 403:
                    logger.error(f"Pazarama authentication failed: Invalid credentials")
                    raise AuthenticationError("Pazarama authentication failed: Invalid credentials")
                elif e.status == 429:
                    logger.error(f"Pazarama rate limit exceeded")
                    raise RateLimitError("Pazarama rate limit exceeded")
                else:
                    logger.error(f"Pazarama API error: {str(e)}")
                    raise APIError(f"Pazarama API error: {str(e)}")
                    
            except asyncio.TimeoutError:
                logger.error("Pazarama API request timed out")
                raise NetworkError("Pazarama API request timed out")
                
        except AuthenticationError as e:
            logger.error(f"Pazarama authentication error: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Pazarama network error: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Pazarama rate limit error: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error during Pazarama authentication: {str(e)}")
            raise AuthenticationError(f"Pazarama authentication failed: {str(e)}")

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from Pazarama
        
        Args:
            **kwargs: Optional filters
                - page: Page number (default: 1)
                - size: Page size (default: 100)
                - status: Product status (default: active)
                
        Returns:
            List of products
        """
        try:
            logger.info("Fetching products from Pazarama...")
            
            params = {
                'page': kwargs.get('page', 1),
                'limit': kwargs.get('size', 100),
                'status': kwargs.get('status', 'active')
            }
            
            response = await self._make_request(
                endpoint=self.endpoints['products'],
                params=params
            )
            
            if not response or 'data' not in response:
                logger.warning("Pazarama returned empty product list")
                return []
                
            products = []
            for item in response.get('data', []):
                product = self._format_product(item)
                if product:
                    products.append(product)
                    
            logger.info(f"Retrieved {len(products)} products from Pazarama")
            return products
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while fetching Pazarama products: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while fetching Pazarama products: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while fetching Pazarama products: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while fetching Pazarama products: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while fetching Pazarama products: {str(e)}")
            raise APIError(f"Failed to fetch Pazarama products: {str(e)}")

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data"""
        try:
            # Extract SKU
            sku = item.get('stockCode')
            if not sku:
                logger.warning("Product missing SKU (stockCode)")
                return None
                
            return {
                'sku': sku,
                'data': {
                    'title': item.get('name', ''),
                    'description': item.get('description', ''),
                    'price': float(item.get('price', 0)),
                    'quantity': int(item.get('stock', 0)),
                    'category': item.get('category', {}).get('name', ''),
                    'brand': item.get('brand', ''),
                    'images': item.get('images', []),
                    'attributes': item.get('attributes', {}),
                    'status': item.get('status', ''),
                    'barcode': item.get('barcode', ''),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error formatting Pazarama product: {str(e)}")
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on Pazarama
        
        Args:
            product_data: Product data to update
            
        Returns:
            Updated product data
        """
        try:
            # Extract SKU and data
            sku = product_data.get('sku', '')
            if not sku:
                raise APIError("Cannot update product: SKU is missing")
                
            data = product_data.get('data', {})
            
            update_data = {
                'stockCode': sku,
                'name': data.get('title', ''),
                'price': data.get('price', 0),
                'stock': data.get('quantity', 0),
                'description': data.get('description', ''),
                'images': data.get('images', []),
                'attributes': data.get('attributes', {})
            }
            
            logger.info(f"Updating Pazarama product with SKU: {sku}")
            response = await self._make_request(
                endpoint=f"{self.endpoints['products']}/{sku}",
                method='PUT',
                data=update_data
            )
            
            logger.info(f"Successfully updated Pazarama product with SKU: {sku}")
            return product_data
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while updating Pazarama product {sku}: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while updating Pazarama product {sku}: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while updating Pazarama product {sku}: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while updating Pazarama product {sku}: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while updating Pazarama product {sku}: {str(e)}")
            raise APIError(f"Failed to update Pazarama product: {str(e)}")

    async def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Any = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 3
    ) -> Any:
        """Make API request with retry mechanism"""
        url = f"{self.base_url}{endpoint}"
        
        # Disable SSL verification for development
        ssl_verify = os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true'
        
        # Log request details (without sensitive info)
        logger.debug(f"Pazarama API request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if data:
            logger.debug(f"Request data: {data}")
        
        for attempt in range(retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30),
                        ssl=False if ssl_verify else True
                    ) as response:
                        # Log response status
                        logger.debug(f"Pazarama API response status: {response.status}")
                        
                        if response.status == 429:  # Rate limit
                            wait_time = self.rate_limit_wait * (2 ** attempt)
                            logger.warning(f"Pazarama rate limit hit, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        elif response.status == 401 or response.status == 403:
                            response_text = await response.text()
                            logger.error(f"Pazarama authentication error: {response_text}")
                            raise AuthenticationError(f"Authentication failed: {response.status} - {response_text}")
                        
                        elif response.status >= 500:
                            response_text = await response.text()
                            logger.error(f"Pazarama server error: {response_text}")
                            
                            if attempt < retry_count - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.info(f"Pazarama server error, retrying in {wait_time} seconds")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise APIError(f"Server error after {retry_count} attempts: {response.status} - {response_text}")
                        
                        elif response.status >= 400:
                            response_text = await response.text()
                            logger.error(f"Pazarama client error: {response_text}")
                            raise APIError(f"Request failed: {response.status} - {response_text}")
                        
                        # Success case
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            response_text = await response.text()
                            logger.warning(f"Pazarama response not JSON: {response_text[:100]}...")
                            return {"text": response_text}
                        
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Pazarama connection error: {str(e)}")
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Connection error after {retry_count} attempts: {str(e)}")
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Pazarama response error: {str(e)}")
                if e.status == 429:
                    if attempt < retry_count - 1:
                        wait_time = self.rate_limit_wait * (2 ** attempt)
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                        await asyncio.sleep(wait_time)
                    else:
                        raise RateLimitError(f"Rate limit exceeded after {retry_count} attempts")
                elif e.status in (401, 403):
                    raise AuthenticationError(f"Authentication failed: {str(e)}")
                else:
                    raise APIError(f"Request failed: {str(e)}")
                    
            except asyncio.TimeoutError:
                logger.error("Pazarama request timed out")
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Request timed out after {retry_count} attempts")
                    
            except (AuthenticationError, RateLimitError, NetworkError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during Pazarama API request: {str(e)}")
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(f"Request failed after {retry_count} attempts: {str(e)}")

        # This should never be reached due to the raise statements above
        raise APIError(f"Request failed after {retry_count} attempts")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get Pazarama categories
        
        Returns:
            List of categories
        """
        try:
            logger.info("Fetching Pazarama categories...")
            
            response = await self._make_request(
                endpoint=self.endpoints['categories']
            )
            
            if not response or 'data' not in response:
                logger.warning("Pazarama returned empty category list")
                return []
                
            categories = response.get('data', [])
            logger.info(f"Retrieved {len(categories)} categories from Pazarama")
            return categories
            
        except Exception as e:
            logger.error(f"Error fetching Pazarama categories: {str(e)}")
            raise APIError(f"Failed to fetch categories: {str(e)}")

    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a single product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data if found, None otherwise
        """
        try:
            logger.info(f"Fetching Pazarama product with SKU: {sku}")
            
            response = await self._make_request(
                endpoint=f"{self.endpoints['products']}/{sku}"
            )
            
            if not response or 'data' not in response:
                logger.warning(f"No product found with SKU: {sku}")
                return None
                
            product = self._format_product(response['data'])
            if product:
                logger.info(f"Found Pazarama product with SKU: {sku}")
            else:
                logger.warning(f"Failed to format product with SKU: {sku}")
                
            return product
            
        except APIError as e:
            if "404" in str(e):
                logger.warning(f"Product with SKU {sku} not found")
                return None
            raise
            
        except Exception as e:
            logger.error(f"Error fetching Pazarama product with SKU {sku}: {str(e)}")
            raise APIError(f"Failed to fetch product with SKU {sku}: {str(e)}")