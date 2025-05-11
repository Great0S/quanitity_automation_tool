"""
Handles WooCommerce product management
"""

import os
import asyncio
import time
import json
import requests
from typing import Dict, List, Any, Optional, cast
from datetime import datetime
from woocommerce import API
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
from core.error_handler import handle_exceptions, safe_execute, error_handler
from .base_client import BaseAPIClient
from dotenv import load_dotenv


load_dotenv()

class WordPressClient(BaseAPIClient):
    """WordPress/WooCommerce API Client"""
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self.logger = logger
        self.retry_delay = 2  # seconds

    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with WordPress/WooCommerce API using consumer credentials"""
        try:
            logger.info("Authenticating with WordPress/WooCommerce API...")
            
            # Create auth dict with explicit type casting
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            try:
                test_response = await self._make_request(
                    method="GET",
                    url=f"{self.base_url}/wp-json/wc/v3/products",
                    auth=auth,
                    params={'per_page': 1}
                )
                
                if not test_response:
                    raise AuthenticationError("WordPress/WooCommerce authentication failed: Empty response")
                    
                if not isinstance(test_response, list):
                    raise AuthenticationError("WordPress/WooCommerce authentication failed: Invalid response format")
                    
                logger.info("WordPress/WooCommerce authentication successful")
                
            except requests.exceptions.ConnectionError as e:
                error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'ConnectionError'}
                error_handler.log_error(e, error_context)
                raise NetworkError(f"WordPress/WooCommerce connection error: {str(e)}")
                
            except requests.exceptions.Timeout as e:
                error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'Timeout'}
                error_handler.log_error(e, error_context)
                raise NetworkError(f"WordPress/WooCommerce request timed out: {str(e)}")
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                error_context = {
                    'client': 'WordPress', 
                    'operation': 'authenticate', 
                    'error_type': 'HTTPError',
                    'status_code': str(status_code)
                }
                error_handler.log_error(e, error_context)
                
                if status_code == 401 or status_code == 403:
                    raise AuthenticationError(f"WordPress/WooCommerce authentication failed: Invalid credentials (status code: {status_code})")
                elif status_code == 429:
                    raise RateLimitError(f"WordPress/WooCommerce rate limit exceeded (status code: {status_code})")
                else:
                    raise APIError(f"WordPress/WooCommerce HTTP error: {str(e)} (status code: {status_code})")
                
        except AuthenticationError as e:
            error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'AuthenticationError'}
            error_handler.log_error(e, error_context)
            raise
            
        except NetworkError as e:
            error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'NetworkError'}
            error_handler.log_error(e, error_context)
            raise
            
        except RateLimitError as e:
            error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'RateLimitError'}
            error_handler.log_error(e, error_context)
            raise
            
        except Exception as e:
            error_context = {'client': 'WordPress', 'operation': 'authenticate', 'error_type': 'UnexpectedError'}
            error_handler.log_error(e, error_context)
            raise AuthenticationError(f"WordPress/WooCommerce authentication failed: {str(e)}")

    def _setup_credentials(self) -> None:
        """Setup WooCommerce API credentials"""
        try:
            self.site_url = os.getenv('WP_SITE_URL')
            self.consumer_key = os.getenv('WC_CONSUMER_KEY')
            self.consumer_secret = os.getenv('WC_CONSUMER_SECRET')
            
            if not self.site_url:
                error_context = {'client': 'WordPress', 'operation': '_setup_credentials', 'missing': 'WP_SITE_URL'}
                error_handler.log_error(AuthenticationError("WP_SITE_URL environment variable is not set"), error_context)
                self.logger.error("WP_SITE_URL environment variable is not set")
                
            if not self.consumer_key:
                error_context = {'client': 'WordPress', 'operation': '_setup_credentials', 'missing': 'WC_CONSUMER_KEY'}
                error_handler.log_error(AuthenticationError("WC_CONSUMER_KEY environment variable is not set"), error_context)
                self.logger.error("WC_CONSUMER_KEY environment variable is not set")
                
            if not self.consumer_secret:
                error_context = {'client': 'WordPress', 'operation': '_setup_credentials', 'missing': 'WC_CONSUMER_SECRET'}
                error_handler.log_error(AuthenticationError("WC_CONSUMER_SECRET environment variable is not set"), error_context)
                self.logger.error("WC_CONSUMER_SECRET environment variable is not set")
                
            if not all([self.site_url, self.consumer_key, self.consumer_secret]):
                raise AuthenticationError("Missing WordPress/WooCommerce API credentials")
                
            # Remove trailing slash from site URL if present
            self.base_url = self.site_url.rstrip('/') if self.site_url else None
            
            # Initialize WooCommerce API client
            self.wc_api = API(
                url=self.site_url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                version="wc/v3",
                timeout=30
            )
            
            # Log initialization (without sensitive data)
            logger.debug(f"WordPress/WooCommerce client initialized for site: {self.site_url}")
        except Exception as e:
            error_context = {'client': 'WordPress', 'operation': '_setup_credentials'}
            error_handler.log_error(e, error_context)
            raise

    @handle_exceptions
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from WooCommerce
        
        Args:
            **kwargs: Optional filters
                - page: Page number (default: 1)
                - size: Page size (default: 100)
                - status: Product status (default: publish)
                - category: Category ID
                - search: Search term
                
        Returns:
            List of products
        """
        try:
            logger.info("Fetching products from WordPress/WooCommerce...")
            
            # Prepare parameters
            params = {
                'page': kwargs.get('page', 1),
                'per_page': kwargs.get('size', 100),
                'status': kwargs.get('status', 'publish')
            }
            
            # Add optional filters
            if 'category' in kwargs:
                params['category'] = kwargs['category']
            if 'search' in kwargs:
                params['search'] = kwargs['search']
                
            # Create auth dict
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            # Make request
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/wp-json/wc/v3/products",
                auth=auth,
                params=params
            )
            
            if not response or not isinstance(response, list):
                logger.warning("WordPress/WooCommerce returned empty product list")
                return []
                
            # Format products
            products = []
            for item in response:
                try:
                    product = self._format_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    error_context = {
                        'client': 'WordPress',
                        'operation': 'get_products',
                        'product_id': str(item.get('id', 'unknown')),
                        'error_type': 'FormatError'
                    }
                    error_handler.log_error(e, error_context)
                    # Continue with other products
            
            logger.info(f"Retrieved {len(products)} products from WordPress/WooCommerce")
            return products
            
        except AuthenticationError as e:
            error_context = {'client': 'WordPress', 'operation': 'get_products', 'error_type': 'AuthenticationError'}
            error_handler.log_error(e, error_context)
            raise
            
        except NetworkError as e:
            error_context = {'client': 'WordPress', 'operation': 'get_products', 'error_type': 'NetworkError'}
            error_handler.log_error(e, error_context)
            raise
            
        except RateLimitError as e:
            error_context = {'client': 'WordPress', 'operation': 'get_products', 'error_type': 'RateLimitError'}
            error_handler.log_error(e, error_context)
            raise
            
        except APIError as e:
            error_context = {'client': 'WordPress', 'operation': 'get_products', 'error_type': 'APIError'}
            error_handler.log_error(e, error_context)
            raise
            
        except Exception as e:
            error_context = {'client': 'WordPress', 'operation': 'get_products', 'error_type': 'UnexpectedError'}
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch WordPress/WooCommerce products: {str(e)}")

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format WooCommerce product data to standard format"""
        try:
            # Extract SKU
            sku = item.get('sku')
            if not sku:
                logger.warning("Product missing SKU")
                return None
                
            # Extract images
            images = []
            for img in item.get('images', []):
                if 'src' in img:
                    images.append(img['src'])
            
            # Extract categories
            categories = []
            for cat in item.get('categories', []):
                if 'name' in cat:
                    categories.append(cat['name'])
            
            # Format product data
            return {
                'sku': sku,
                'data': {
                    'id': item.get('id', ''),
                    'title': item.get('name', ''),
                    'description': item.get('description', ''),
                    'price': float(item.get('regular_price', 0) or 0),
                    'salePrice': float(item.get('sale_price', 0) or 0),
                    'quantity': int(item.get('stock_quantity', 0) or 0),
                    'categoryName': ', '.join(categories),
                    'images': images,
                    'attributes': item.get('attributes', []),
                    'status': item.get('status', ''),
                    'permalink': item.get('permalink', ''),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            error_context = {
                'client': 'WordPress',
                'operation': '_format_product',
                'product_id': str(item.get('id', 'unknown')),
                'error_type': 'FormatError'
            }
            error_handler.log_error(e, error_context)
            return None

    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on WooCommerce
        
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
                    'client': 'WordPress',
                    'operation': 'update_product',
                    'error_type': 'ValidationError'
                }
                error_handler.log_error(error, error_context)
                raise error
                
            data = product_data.get('data', {})
            
            # First, get product ID by SKU
            product_id = await self._get_product_id_by_sku(sku)
            if not product_id:
                error = APIError(f"Product with SKU {sku} not found")
                error_context = {
                    'client': 'WordPress',
                    'operation': 'update_product',
                    'sku': sku,
                    'error_type': 'NotFound'
                }
                error_handler.log_error(error, error_context)
                raise error
                
            # Prepare update data
            update_data = {
                'regular_price': str(data.get('price', 0)),
                'stock_quantity': data.get('quantity', 0),
                'manage_stock': True
            }
            
            # Add sale price if present
            if 'salePrice' in data and data['salePrice'] > 0:
                update_data['sale_price'] = str(data['salePrice'])
            
            # Create auth dict
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            logger.info(f"Updating WordPress/WooCommerce product with SKU: {sku}")
            response = await self._make_request(
                method="PUT",
                url=f"{self.base_url}/wp-json/wc/v3/products/{product_id}",
                auth=auth,
                data=update_data
            )
            
            if not response or 'id' not in response:
                error = APIError(f"Failed to update product: Invalid response")
                error_context = {
                    'client': 'WordPress',
                    'operation': 'update_product',
                    'sku': sku,
                    'product_id': str(product_id),
                    'error_type': 'InvalidResponse'
                }
                error_handler.log_error(error, error_context)
                raise error
                
            logger.info(f"Successfully updated WordPress/WooCommerce product with SKU: {sku}")
            return product_data
            
        except AuthenticationError as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown'),
                'error_type': 'AuthenticationError'
            }
            error_handler.log_error(e, error_context)
            raise
            
        except NetworkError as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown'),
                'error_type': 'NetworkError'
            }
            error_handler.log_error(e, error_context)
            raise
            
        except RateLimitError as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown'),
                'error_type': 'RateLimitError'
            }
            error_handler.log_error(e, error_context)
            raise
            
        except APIError as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown'),
                'error_type': 'APIError'
            }
            error_handler.log_error(e, error_context)
            raise
            
        except Exception as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown'),
                'error_type': 'UnexpectedError'
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to update WordPress/WooCommerce product: {str(e)}")

    async def _get_product_id_by_sku(self, sku: str) -> Optional[int]:
        """
        Get product ID by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product ID if found, None otherwise
        """
        try:
            # Create auth dict
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            # Search for product by SKU
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/wp-json/wc/v3/products",
                auth=auth,
                params={'sku': sku}
            )
            
            if not response or not isinstance(response, list) or not response:
                logger.warning(f"No product found with SKU: {sku}")
                return None
                
            # Return first product ID
            return response[0].get('id')
            
        except Exception as e:
            error_context = {
                'client': 'WordPress',
                'operation': '_get_product_id_by_sku',
                'sku': sku,
                'error_type': 'LookupError'
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to get product ID by SKU: {str(e)}")

    async def _make_request(
        self,
        method: str,
        url: str,
        auth: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make API request to WordPress/WooCommerce
        
        Args:
            method: HTTP method
            url: Request URL
            auth: Authentication credentials
            params: Query parameters
            data: Request data
            
        Returns:
            API response
        """
        # Disable SSL verification for development
        ssl_verify = not (os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true')
        
        request_context = {
            'client': 'WordPress',
            'operation': '_make_request',
            'url': url,
            'method': method
        }
        
        # Log request details (without sensitive info)
        logger.debug(f"WordPress/WooCommerce API request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
            request_context['params'] = str(params)
        if data:
            logger.debug(f"Request data: {data}")
            request_context['data'] = str(data)
        
        for attempt in range(self.max_retries):
            request_context['attempt'] = str(attempt + 1)
            try:
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._sync_request(method, url, auth, params, data, ssl_verify)
                )
                
                # Log response status
                logger.debug(f"WordPress/WooCommerce API response received")
                
                return response
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 0
                request_context['status_code'] = str(status_code)
                request_context['error_type'] = 'HTTPError'
                
                if status_code == 429:  # Rate limit
                    wait_time = self.rate_limit_wait * (2 ** attempt)
                    logger.warning(f"WordPress/WooCommerce rate limit hit, waiting {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                    
                elif status_code in (401, 403):
                    response_text = e.response.text if hasattr(e, 'response') else ''
                    logger.error(f"WordPress/WooCommerce authentication error: {response_text}")
                    request_context['response_text'] = response_text
                    error = AuthenticationError(f"Authentication failed: {status_code} - {response_text}")
                    error_handler.log_error(error, request_context)
                    raise error
                
                elif status_code >= 500:
                    response_text = e.response.text if hasattr(e, 'response') else ''
                    logger.error(f"WordPress/WooCommerce server error: {response_text}")
                    request_context['response_text'] = response_text
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.info(f"WordPress/WooCommerce server error, retrying in {wait_time} seconds")
                        request_context['wait_time'] = str(wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error = APIError(f"Server error after {self.max_retries} attempts: {status_code} - {response_text}")
                        error_handler.log_error(error, request_context)
                        raise error
                
                else:
                    response_text = e.response.text if hasattr(e, 'response') else ''
                    logger.error(f"WordPress/WooCommerce client error: {response_text}")
                    request_context['response_text'] = response_text
                    error = APIError(f"Request failed: {status_code} - {response_text}")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except requests.exceptions.ConnectionError as e:
                logger.error(f"WordPress/WooCommerce connection error: {str(e)}")
                request_context['error_type'] = 'ConnectionError'
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = NetworkError(f"Connection error after {self.max_retries} attempts: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except requests.exceptions.Timeout as e:
                logger.error(f"WordPress/WooCommerce request timed out: {str(e)}")
                request_context['error_type'] = 'Timeout'
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = NetworkError(f"Request timed out after {self.max_retries} attempts: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except (AuthenticationError, RateLimitError, NetworkError, APIError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during WordPress/WooCommerce API request: {str(e)}")
                request_context['error_type'] = 'UnexpectedError'
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")
                    error_handler.log_error(error, request_context)
                    raise error

        # This should never be reached due to the raise statements above
        error = APIError(f"Request failed after {self.max_retries} attempts")
        error_handler.log_error(error, request_context)
        raise error

    def _sync_request(
        self,
        method: str,
        url: str,
        auth: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        verify: bool = True
    ) -> Any:
        """
        Make synchronous request to WordPress/WooCommerce API
        
        Args:
            method: HTTP method
            url: Request URL
            auth: Authentication credentials
            params: Query parameters
            data: Request data
            verify: Whether to verify SSL certificates
            
        Returns:
            API response
        """
        try:
            # Prepare request
            request_kwargs = {
                'auth': (auth['consumer_key'], auth['consumer_secret']),
                'params': params,
                'verify': verify,
                'timeout': self.request_timeout
            }
            
            # Add data if present
            if data:
                request_kwargs['json'] = data
            
            # Make request
            response = requests.request(method, url, **request_kwargs)
            
            # Raise for status
            response.raise_for_status()
            
            # Parse JSON response
            return response.json()
            
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Failed to parse WordPress/WooCommerce response as JSON: {str(e)}")
            return response.text
            
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout) as e:
            # Re-raise these exceptions for proper handling in _make_request
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in WordPress/WooCommerce sync request: {str(e)}")
            raise

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
            logger.info(f"Fetching WordPress/WooCommerce product with SKU: {sku}")
            
            # Create auth dict
            auth: Dict[str, str] = {
                'consumer_key': str(self.consumer_key),
                'consumer_secret': str(self.consumer_secret)
            }
            
            # Search for product by SKU
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/wp-json/wc/v3/products",
                auth=auth,
                params={'sku': sku}
            )
            
            if not response or not isinstance(response, list) or not response:
                logger.warning(f"No product found with SKU: {sku}")
                return None
                
            # Format product
            product = self._format_product(response[0])
            if product:
                logger.info(f"Found WordPress/WooCommerce product with SKU: {sku}")
            else:
                logger.warning(f"Failed to format product with SKU: {sku}")
                
            return product
            
        except Exception as e:
            error_context = {
                'client': 'WordPress',
                'operation': 'get_product_by_sku',
                'sku': sku,
                'error_type': 'LookupError'
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch product with SKU {sku}: {str(e)}")
