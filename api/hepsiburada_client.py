"""
Hepsiburada API Client
"""

import os
import json
import base64
import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
from .base_client import BaseAPIClient

class HepsiburadaClient(BaseAPIClient):
    """Hepsiburada API Client"""
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self._setup_endpoints()
        self.logger = logger
        self.retry_delay = 2  # seconds

    def _setup_credentials(self) -> None:
        """Setup API credentials"""
        self.username = os.getenv('HEPSIBURADA_USERNAME')
        self.password = os.getenv('HEPSIBURADA_PASSWORD')
        self.merchant_id = os.getenv('HEPSIBURADA_MERCHANT_ID', self.username)  # Use username as merchant ID if not provided
        
        if not all([self.username, self.password]):
            logger.error("Missing Hepsiburada API credentials")
            raise AuthenticationError("Missing Hepsiburada API credentials")
            
        # Create Basic Auth header
        auth_string = f"{self.merchant_id}:{self.password}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        # API configuration
        self.base_url = "https://api.hepsiburada.com"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {auth_b64}",
            "User-Agent": self.username
        }
        
        # Log initialization (without sensitive data)
        logger.debug(f"Hepsiburada client initialized for merchant ID: {self.merchant_id}")

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        self.endpoints = {
            'listings': '/listings',
            'products': '/products',
            'orders': '/orders',
            'inventory': '/inventory'
        }
        logger.debug(f"Hepsiburada endpoints configured: {list(self.endpoints.keys())}")

    async def authenticate(self) -> None:
        """Authenticate with Hepsiburada API"""
        try:
            logger.info("Authenticating with Hepsiburada API...")
            
            # Test authentication with a simple request
            try:
                test_response = await self._make_request(
                    endpoint=f"{self.endpoints['listings']}",
                    params={'limit': 1}
                )
                
                # Print response for debugging
                logger.debug(f"Hepsiburada authentication response received")
                
                if not test_response:
                    raise AuthenticationError("Hepsiburada authentication failed: Empty response")
                    
                logger.info("Hepsiburada authentication successful")
                
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Hepsiburada connection error: {str(e)}")
                raise NetworkError(f"Hepsiburada connection error: {str(e)}")
                
            except aiohttp.ClientResponseError as e:
                if e.status == 401 or e.status == 403:
                    logger.error(f"Hepsiburada authentication failed: Invalid credentials")
                    raise AuthenticationError("Hepsiburada authentication failed: Invalid credentials")
                elif e.status == 429:
                    logger.error(f"Hepsiburada rate limit exceeded")
                    raise RateLimitError("Hepsiburada rate limit exceeded")
                else:
                    logger.error(f"Hepsiburada API error: {str(e)}")
                    raise APIError(f"Hepsiburada API error: {str(e)}")
                    
            except asyncio.TimeoutError:
                logger.error("Hepsiburada API request timed out")
                raise NetworkError("Hepsiburada API request timed out")
                
        except AuthenticationError as e:
            logger.error(f"Hepsiburada authentication error: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Hepsiburada network error: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Hepsiburada rate limit error: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error during Hepsiburada authentication: {str(e)}")
            raise AuthenticationError(f"Hepsiburada authentication failed: {str(e)}")

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from Hepsiburada
        
        Args:
            **kwargs: Optional filters
                - offset: Pagination offset (default: 0)
                - size: Page size (default: 100)
                - status: Product status (default: active)
                
        Returns:
            List of products
        """
        try:
            logger.info("Fetching products from Hepsiburada...")
            
            params = {
                'offset': kwargs.get('offset', 0),
                'limit': kwargs.get('size', 100),
                'status': kwargs.get('status', 'active')
            }
            
            response = await self._make_request(
                endpoint=f"{self.endpoints['listings']}",
                params=params
            )
            
            if not response or 'listings' not in response:
                logger.warning("Hepsiburada returned empty product list")
                return []
                
            products = []
            for item in response['listings']:
                product = self._format_product(item)
                if product:
                    products.append(product)
                    
            logger.info(f"Retrieved {len(products)} products from Hepsiburada")
            return products
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while fetching Hepsiburada products: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while fetching Hepsiburada products: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while fetching Hepsiburada products: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while fetching Hepsiburada products: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while fetching Hepsiburada products: {str(e)}")
            raise APIError(f"Failed to fetch Hepsiburada products: {str(e)}")

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data"""
        try:
            # Extract SKU
            sku = item.get('merchantSku', '')
            if not sku:
                logger.warning("Product missing SKU (merchantSku)")
                return None
                
            return {
                'sku': sku,
                'data': {
                    'id': item.get('id', ''),
                    'title': item.get('productName', ''),
                    'description': item.get('description', ''),
                    'price': float(item.get('price', {}).get('amount', 0)),
                    'sale_price': float(item.get('salePrice', {}).get('amount', 0) if item.get('salePrice') else 0),
                    'quantity': int(item.get('availableStock', 0)),
                    'category': item.get('categoryName', ''),
                    'images': [img.get('url', '') for img in item.get('images', [])],
                    'attributes': item.get('attributes', []),
                    'status': item.get('status', ''),
                    'barcode': item.get('barcode', ''),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error formatting Hepsiburada product: {str(e)}")
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on Hepsiburada
        
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
                'merchantSku': sku,
                'price': {
                    'amount': data.get('price', 0),
                    'currency': 'TRY'
                },
                'availableStock': data.get('quantity', 0)
            }
            
            # Add optional fields if present
            if 'sale_price' in data and data['sale_price'] > 0:
                update_data['salePrice'] = {
                    'amount': data['sale_price'],
                    'currency': 'TRY'
                }
            
            logger.info(f"Updating Hepsiburada product with SKU: {sku}")
            response = await self._make_request(
                endpoint=f"{self.endpoints['listings']}/{sku}",
                method="PUT",
                data=update_data
            )
            
            logger.info(f"Successfully updated Hepsiburada product with SKU: {sku}")
            return product_data
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while updating Hepsiburada product {sku}: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while updating Hepsiburada product {sku}: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while updating Hepsiburada product {sku}: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while updating Hepsiburada product {sku}: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while updating Hepsiburada product {sku}: {str(e)}")
            raise APIError(f"Failed to update Hepsiburada product: {str(e)}")

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make API request with retry mechanism"""
        url = f"{self.base_url}{endpoint}"
        
        # Disable SSL verification for development
        ssl_verify = os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true'
        
        # Log request details (without sensitive info)
        logger.debug(f"Hepsiburada API request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if data:
            logger.debug(f"Request data: {data}")
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.request_timeout),
                        ssl=False if ssl_verify else True
                    ) as response:
                        # Log response status
                        logger.debug(f"Hepsiburada API response status: {response.status}")
                        
                        if response.status == 429:  # Rate limit
                            wait_time = self.rate_limit_wait * (2 ** attempt)
                            logger.warning(f"Hepsiburada rate limit hit, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        elif response.status == 401 or response.status == 403:
                            response_text = await response.text()
                            logger.error(f"Hepsiburada authentication error: {response_text}")
                            raise AuthenticationError(f"Authentication failed: {response.status} - {response_text}")
                        
                        elif response.status >= 500:
                            response_text = await response.text()
                            logger.error(f"Hepsiburada server error: {response_text}")
                            
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.info(f"Hepsiburada server error, retrying in {wait_time} seconds")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise APIError(f"Server error after {self.max_retries} attempts: {response.status} - {response_text}")
                        
                        elif response.status >= 400:
                            response_text = await response.text()
                            logger.error(f"Hepsiburada client error: {response_text}")
                            raise APIError(f"Request failed: {response.status} - {response_text}")
                        
                        # Success case
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            response_text = await response.text()
                            logger.warning(f"Hepsiburada response not JSON: {response_text[:100]}...")
                            return {"text": response_text}
                        
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Hepsiburada connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Connection error after {self.max_retries} attempts: {str(e)}")
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Hepsiburada response error: {str(e)}")
                if e.status == 429:
                    if attempt < self.max_retries - 1:
                        wait_time = self.rate_limit_wait * (2 ** attempt)
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                        await asyncio.sleep(wait_time)
                    else:
                        raise RateLimitError(f"Rate limit exceeded after {self.max_retries} attempts")
                elif e.status in (401, 403):
                    raise AuthenticationError(f"Authentication failed: {str(e)}")
                else:
                    raise APIError(f"Request failed: {str(e)}")
                    
            except asyncio.TimeoutError:
                logger.error("Hepsiburada request timed out")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Request timed out after {self.max_retries} attempts")
                    
            except (AuthenticationError, RateLimitError, NetworkError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during Hepsiburada API request: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")

        # This should never be reached due to the raise statements above
        raise APIError(f"Request failed after {self.max_retries} attempts")

    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a single product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data if found, None otherwise
        """
        try:
            logger.info(f"Fetching Hepsiburada product with SKU: {sku}")
            
            response = await self._make_request(
                endpoint=f"{self.endpoints['listings']}/{sku}"
            )
            
            if not response:
                logger.warning(f"No product found with SKU: {sku}")
                return None
                
            product = self._format_product(response)
            if product:
                logger.info(f"Found Hepsiburada product with SKU: {sku}")
            else:
                logger.warning(f"Failed to format product with SKU: {sku}")
                
            return product
            
        except APIError as e:
            if "404" in str(e):
                logger.warning(f"Product with SKU {sku} not found")
                return None
            raise
            
        except Exception as e:
            logger.error(f"Error fetching Hepsiburada product with SKU {sku}: {str(e)}")
            raise APIError(f"Failed to fetch product with SKU {sku}: {str(e)}")