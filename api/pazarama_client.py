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
from core.error_handler import handle_exceptions, safe_execute, error_handler
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
        try:
            self.api_key = os.getenv('PAZARAMA_API_KEY')
            self.api_secret = os.getenv('PAZARAMA_API_SECRET')
            self.seller_id = os.getenv('PAZARAMA_SELLER_ID')
            
            if not self.api_key:
                error_context = {'client': 'Pazarama', 'operation': '_setup_credentials', 'missing': 'PAZARAMA_API_KEY'}
                error_handler.log_error(AuthenticationError("PAZARAMA_API_KEY environment variable is not set"), error_context)
                self.logger.error("PAZARAMA_API_KEY environment variable is not set")
                
            if not self.api_secret:
                error_context = {'client': 'Pazarama', 'operation': '_setup_credentials', 'missing': 'PAZARAMA_API_SECRET'}
                error_handler.log_error(AuthenticationError("PAZARAMA_API_SECRET environment variable is not set"), error_context)
                self.logger.error("PAZARAMA_API_SECRET environment variable is not set")
                
            if not self.seller_id:
                error_context = {'client': 'Pazarama', 'operation': '_setup_credentials', 'missing': 'PAZARAMA_SELLER_ID'}
                error_handler.log_error(AuthenticationError("PAZARAMA_SELLER_ID environment variable is not set"), error_context)
                self.logger.error("PAZARAMA_SELLER_ID environment variable is not set")
                
            if not all([self.api_key, self.api_secret, self.seller_id]):
                raise AuthenticationError("Missing Pazarama API credentials")
                
            self.headers = {
                key: str(value) for key, value in {
                    "Content-Type": "application/json",
                    "X-API-KEY": self.api_key,
                    "X-SELLER-ID": self.seller_id
                }.items() if value is not None
            }
            
            # Log initialization (without sensitive data)
            logger.debug(f"Pazarama client initialized for seller ID: {self.seller_id}")
        except Exception as e:
            error_context = {'client': 'Pazarama', 'operation': '_setup_credentials'}
            error_handler.log_error(e, error_context)
            raise

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        try:
            self.base_url = "https://api.pazarama.com"
            self.endpoints = {
                'products': '/products',
                'orders': '/orders',
                'categories': '/categories',
                'inventory': '/inventory'
            }
            logger.debug(f"Pazarama endpoints configured: {list(self.endpoints.keys())}")
        except Exception as e:
            error_context = {'client': 'Pazarama', 'operation': '_setup_endpoints'}
            error_handler.log_error(e, error_context)
            raise

    @handle_exceptions
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
                error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'ConnectionError'}
                error_handler.log_error(e, error_context)
                raise NetworkError(f"Pazarama connection error: {str(e)}")
                
            except aiohttp.ClientResponseError as e:
                error_context = {
                    'client': 'Pazarama', 
                    'operation': 'authenticate', 
                    'error_type': 'ResponseError',
                    'status_code': str(getattr(e, 'status', 'unknown'))
                }
                error_handler.log_error(e, error_context)
                
                if getattr(e, 'status', 0) == 401 or getattr(e, 'status', 0) == 403:
                    raise AuthenticationError("Pazarama authentication failed: Invalid credentials")
                elif getattr(e, 'status', 0) == 429:
                    raise RateLimitError("Pazarama rate limit exceeded")
                else:
                    raise APIError(f"Pazarama API error: {str(e)}")
                    
            except asyncio.TimeoutError:
                error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'Timeout'}
                error_handler.log_error(TimeoutError("Pazarama API request timed out"), error_context)
                raise NetworkError("Pazarama API request timed out")
                
        except AuthenticationError as e:
            error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'AuthenticationError'}
            error_handler.log_error(e, error_context)
            raise
            
        except NetworkError as e:
            error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'NetworkError'}
            error_handler.log_error(e, error_context)
            raise
            
        except RateLimitError as e:
            error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'RateLimitError'}
            error_handler.log_error(e, error_context)
            raise
            
        except Exception as e:
            error_context = {'client': 'Pazarama', 'operation': 'authenticate', 'error_type': 'UnexpectedError'}
            error_handler.log_error(e, error_context)
            raise AuthenticationError(f"Pazarama authentication failed: {str(e)}")

    @handle_exceptions
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
                try:
                    product = self._format_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    error_context = {
                        'client': 'Pazarama',
                        'operation': 'get_products',
                        'product_id': str(item.get('id', 'unknown')),
                        'error_type': 'FormatError'
                    }
                    error_handler.log_error(e, error_context)
                    # Continue with other products
                    
            logger.info(f"Retrieved {len(products)} products from Pazarama")
            return products
            
        except Exception as e:
            error_context = {
                'client': 'Pazarama',
                'operation': 'get_products',
                'kwargs': str(kwargs)
            }
            error_handler.log_error(e, error_context)
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
            error_context = {
                'client': 'Pazarama',
                'operation': '_format_product',
                'product_id': str(item.get('id', 'unknown')),
                'error_type': 'FormatError'
            }
            error_handler.log_error(e, error_context)
            return None

    @handle_exceptions
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
                error = APIError("Cannot update product: SKU is missing")
                error_context = {
                    'client': 'Pazarama',
                    'operation': 'update_product',
                    'error_type': 'ValidationError'
                }
                error_handler.log_error(error, error_context)
                raise error
                
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
            
        except Exception as e:
            error_context = {
                'client': 'Pazarama',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown')
            }
            error_handler.log_error(e, error_context)
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
        request_context = {
            'client': 'Pazarama',
            'operation': '_make_request',
            'url': url,
            'method': method
        }
        
        # Disable SSL verification for development
        ssl_verify = os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true'
        
        # Log request details (without sensitive info)
        logger.debug(f"Pazarama API request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
            request_context['params'] = str(params)
        if data:
            logger.debug(f"Request data: {data}")
            request_context['data'] = str(data)
        
        for attempt in range(retry_count):
            request_context['attempt'] = str(attempt + 1)
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
                        request_context['status_code'] = str(response.status)
                        
                        if response.status == 429:  # Rate limit
                            wait_time = self.rate_limit_wait * (2 ** attempt)
                            logger.warning(f"Pazarama rate limit hit, waiting {wait_time} seconds")
                            request_context['wait_time'] = str(wait_time)
                            await asyncio.sleep(wait_time)
                            continue
                            
                        elif response.status == 401 or response.status == 403:
                            response_text = await response.text()
                            logger.error(f"Pazarama authentication error: {response_text}")
                            request_context['response_text'] = response_text
                            error = AuthenticationError(f"Authentication failed: {response.status} - {response_text}")
                            error_handler.log_error(error, request_context)
                            raise error
                        
                        elif response.status >= 500:
                            response_text = await response.text()
                            logger.error(f"Pazarama server error: {response_text}")
                            request_context['response_text'] = response_text
                            
                            if attempt < retry_count - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.info(f"Pazarama server error, retrying in {wait_time} seconds")
                                request_context['wait_time'] = str(wait_time)
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                error = APIError(f"Server error after {retry_count} attempts: {response.status} - {response_text}")
                                error_handler.log_error(error, request_context)
                                raise error
                        
                        elif response.status >= 400:
                            response_text = await response.text()
                            logger.error(f"Pazarama client error: {response_text}")
                            request_context['response_text'] = response_text
                            error = APIError(f"Request failed: {response.status} - {response_text}")
                            error_handler.log_error(error, request_context)
                            raise error
                        
                        # Success case
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            response_text = await response.text()
                            logger.warning(f"Pazarama response not JSON: {response_text[:100]}...")
                            return {"text": response_text}
                        
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Pazarama connection error: {str(e)}")
                request_context['error_type'] = 'ConnectionError'
                
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = NetworkError(f"Connection error after {retry_count} attempts: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Pazarama response error: {str(e)}")
                request_context['error_type'] = 'ResponseError'
                request_context['status_code'] = str(getattr(e, 'status', 'unknown'))
                
                if getattr(e, 'status', 0) == 429:
                    if attempt < retry_count - 1:
                        wait_time = self.rate_limit_wait * (2 ** attempt)
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                        request_context['wait_time'] = str(wait_time)
                        await asyncio.sleep(wait_time)
                    else:
                        error = RateLimitError(f"Rate limit exceeded after {retry_count} attempts")
                        error_handler.log_error(error, request_context)
                        raise error
                elif getattr(e, 'status', 0) in (401, 403):
                    error = AuthenticationError(f"Authentication failed: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error
                else:
                    error = APIError(f"Request failed: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except asyncio.TimeoutError:
                logger.error("Pazarama request timed out")
                request_context['error_type'] = 'Timeout'
                
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = NetworkError(f"Request timed out after {retry_count} attempts")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except (AuthenticationError, RateLimitError, NetworkError, APIError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during Pazarama API request: {str(e)}")
                request_context['error_type'] = 'UnexpectedError'
                
                if attempt < retry_count - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = APIError(f"Request failed after {retry_count} attempts: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error

        # This should never be reached due to the raise statements above
        error = APIError(f"Request failed after {retry_count} attempts")
        error_handler.log_error(error, request_context)
        raise error

    @handle_exceptions
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
            error_context = {
                'client': 'Pazarama',
                'operation': 'get_categories'
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch categories: {str(e)}")

    @handle_exceptions
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
            error_context = {
                'client': 'Pazarama',
                'operation': 'get_product_by_sku',
                'sku': sku
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch product with SKU {sku}: {str(e)}")
