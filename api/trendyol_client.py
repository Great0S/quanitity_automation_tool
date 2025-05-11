# api/trendyol_client.py
import asyncio
import os
import json
import base64
import time
from typing import Dict, List, Any, Optional
import aiohttp
from datetime import datetime
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
from core.error_handler import handle_exceptions, safe_execute, error_handler
from .base_client import BaseAPIClient

class TrendyolClient(BaseAPIClient):
    """Trendyol API Client implementation"""
    
    def __init__(self):
        super().__init__()
        # Initialize credentials
        self.api_key = os.getenv('TRENDYOL_API_KEY')
        self.api_secret = os.getenv('TRENDYOL_API_SECRET')
        self.store_id = os.getenv('TRENDYOL_STORE_ID')
        self.auth_hash = os.getenv('TRENDYOL_AUTH_HASH')
        
        # If auth_hash is not provided, generate it from API key and secret
        if not self.auth_hash and self.api_key and self.api_secret:
            auth_string = f"{self.api_key}:{self.api_secret}"
            self.auth_hash = base64.b64encode(auth_string.encode()).decode()
        
        if not all([self.store_id, self.auth_hash]):
            raise AuthenticationError("Missing Trendyol API credentials")
            
        # API configuration
        self.base_url = "https://api.trendyol.com/sapigw/suppliers"
        self.batch_size = 100
        self.max_retries = 3
        self.rate_limit_wait = 15
        self.request_timeout = 30
        self.retry_delay = 2  # seconds
        
        # Set headers
        self.headers = {
            'User-Agent': f'{self.store_id} - Integration',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.auth_hash}'
        }
        
        # Debug info
        logger.debug(f"Trendyol client initialized for store ID: {self.store_id}")

    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Trendyol API"""
        try:
            logger.info("Authenticating with Trendyol API...")
            
            # Test authentication with a simple request
            try:
                test_response = await self._make_request(
                    endpoint="/products",
                    params={'page': 0, 'size': 1}
                )
                
                if not test_response:
                    raise AuthenticationError("Trendyol authentication failed: Empty response")
                    
                if 'totalElements' not in test_response:
                    raise AuthenticationError("Trendyol authentication failed: Invalid response format")
                    
                logger.info(f"Trendyol authentication successful. Found {test_response.get('totalElements', 0)} products.")
                
            except aiohttp.ClientConnectorError as e:
                error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'ConnectionError'}
                error_handler.log_error(e, error_context)
                raise NetworkError(f"Trendyol connection error: {str(e)}")
                
            except aiohttp.ClientResponseError as e:
                error_context = {
                    'client': 'Trendyol', 
                    'operation': 'authenticate', 
                    'error_type': 'ResponseError',
                    'status_code': str(e.status)
                }
                error_handler.log_error(e, error_context)
                
                if e.status == 401 or e.status == 403:
                    raise AuthenticationError("Trendyol authentication failed: Invalid credentials")
                elif e.status == 429:
                    raise RateLimitError("Trendyol rate limit exceeded")
                else:
                    raise APIError(f"Trendyol API error: {str(e)}")
                    
            except asyncio.TimeoutError as e:
                error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'Timeout'}
                error_handler.log_error(e, error_context)
                raise NetworkError("Trendyol API request timed out")
                
        except AuthenticationError as e:
            error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'AuthenticationError'}
            error_handler.log_error(e, error_context)
            raise
            
        except NetworkError as e:
            error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'NetworkError'}
            error_handler.log_error(e, error_context)
            raise
            
        except RateLimitError as e:
            error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'RateLimitError'}
            error_handler.log_error(e, error_context)
            raise
            
        except Exception as e:
            error_context = {'client': 'Trendyol', 'operation': 'authenticate', 'error_type': 'UnexpectedError'}
            error_handler.log_error(e, error_context)
            raise AuthenticationError(f"Trendyol authentication failed: {str(e)}")

    @handle_exceptions
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from Trendyol
        
        Args:
            **kwargs: Optional parameters
                - page: Page number (default: 0)
                - size: Page size (default: 100)
                - approved: Filter by approval status (default: True)
                - barcode: Filter by barcode
                - startDate: Filter by start date
                - endDate: Filter by end date
                
        Returns:
            List of products
        """
        try:
            logger.info("Fetching products from Trendyol...")
            
            # Prepare parameters
            params = {
                'page': kwargs.get('page', 0),
                'size': kwargs.get('size', self.batch_size),
                'approved': str(kwargs.get('approved', True)).lower()  # Convert to string "true" or "false"
}
            
            # Add optional filters
            if 'barcode' in kwargs:
                params['barcode'] = kwargs['barcode']
            if 'startDate' in kwargs:
                params['startDate'] = kwargs['startDate']
            if 'endDate' in kwargs:
                params['endDate'] = kwargs['endDate']
                
            # Make request
            response = await self._make_request(
                endpoint="/products",
                params=params
            )
            
            # Check response
            if not response or 'content' not in response:
                logger.warning("Trendyol returned empty product list")
                return []
                
            # Extract products
            products = response.get('content', [])
            logger.info(f"Retrieved {len(products)} products from Trendyol")
            
            # Format products
            formatted_products = []
            for product in products:
                try:
                    formatted = self._format_product(product)
                    if formatted:
                        formatted_products.append(formatted)
                except Exception as e:
                    error_context = {
                        'client': 'Trendyol',
                        'operation': 'get_products',
                        'product_id': str(product.get('id', 'unknown')),
                        'error_type': 'FormatError'
                    }
                    error_handler.log_error(e, error_context)
                    # Continue with other products
            
            return formatted_products
            
        except Exception as e:
            error_context = {
                'client': 'Trendyol',
                'operation': 'get_products',
                'kwargs': str(kwargs)
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch Trendyol products: {str(e)}")

    def _format_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format Trendyol product data to standard format"""
        try:
            # Extract SKU (barcode or stockCode)
            sku = product.get('barcode') or product.get('stockCode')
            if not sku:
                logger.warning("Product missing SKU (barcode or stockCode)")
                return None
                
            # Extract price
            price = 0
            if 'price' in product:
                price = float(product['price'])
            
            # Extract quantity
            quantity = 0
            if 'quantity' in product:
                quantity = int(product['quantity'])
                
            # Format product data
            return {
                'sku': sku,
                'data': {
                    'id': product.get('id', ''),
                    'title': product.get('title', ''),
                    'description': product.get('description', ''),
                    'price': price,
                    'listPrice': price,  # Same as price if no sale price
                    'salePrice': price,  # Same as price if no sale price
                    'quantity': quantity,
                    'categoryName': product.get('categoryName', ''),
                    'brand': product.get('brand', ''),
                    'images': product.get('images', []),
                    'attributes': product.get('attributes', {}),
                    'approved': product.get('approved', False),
                    'onSale': product.get('onSale', False),
                    'lastUpdate': datetime.now().isoformat()
                }
            }
        except Exception as e:
            error_context = {
                'client': 'Trendyol',
                'operation': '_format_product',
                'product_id': str(product.get('id', 'unknown')),
                'error_type': 'FormatError'
            }
            error_handler.log_error(e, error_context)
            return None

    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on Trendyol
        
        Args:
            product_data: Product data to update
            
        Returns:
            Updated product data
        """
        try:
            # Extract SKU and data
            sku = product_data.get('sku')
            if not sku:
                error = APIError("Cannot update product: SKU is missing")
                error_context = {
                    'client': 'Trendyol',
                    'operation': 'update_product',
                    'error_type': 'ValidationError'
                }
                error_handler.log_error(error, error_context)
                raise error
                
            data = product_data.get('data', {})
            
            # Prepare update data
            update_data = {
                'barcode': sku,
                'quantity': data.get('quantity', 0),
                'salePrice': data.get('price', 0),
                'listPrice': data.get('listPrice', data.get('price', 0))
            }
            
            # Make request
            logger.info(f"Updating Trendyol product with SKU: {sku}")
            response = await self._make_request(
                endpoint="/products/price-and-inventory",
                method="POST",
                data={'items': [update_data]}
            )
            
            # Check response
            if not response or 'batchRequestId' not in response:
                error = APIError(f"Failed to update product: Invalid response")
                error_context = {
                    'client': 'Trendyol',
                    'operation': 'update_product',
                    'sku': sku,
                    'error_type': 'InvalidResponse',
                    'response': str(response)
                }
                error_handler.log_error(error, error_context)
                raise error
                
            # Get batch ID
            batch_id = response['batchRequestId']
            logger.info(f"Trendyol update batch ID: {batch_id}")
            
            # Wait for batch completion
            batch_result = await self._wait_for_batch_completion(batch_id)
            
            # Check for errors
            if batch_result.get('status') != 'COMPLETED':
                error_message = batch_result.get('errorMessage', 'Unknown error')
                error = APIError(f"Failed to update product: {error_message}")
                error_context = {
                    'client': 'Trendyol',
                    'operation': 'update_product',
                    'sku': sku,
                    'batch_id': batch_id,
                    'error_type': 'BatchError',
                    'batch_status': batch_result.get('status')
                }
                error_handler.log_error(error, error_context)
                raise error
                
            logger.info(f"Successfully updated Trendyol product with SKU: {sku}")
            return product_data
            
        except Exception as e:
            error_context = {
                'client': 'Trendyol',
                'operation': 'update_product',
                'sku': product_data.get('sku', 'unknown')
            }
            error_handler.log_error(e, error_context)
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
        request_context = {
            'client': 'Trendyol',
            'operation': '_make_request',
            'url': url,
            'method': method
        }
        
        # Always disable SSL verification to avoid certificate issues
        ssl_verify = False
        
        # Log request details (without sensitive info)
        logger.debug(f"Trendyol API request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
            request_context['params'] = str(params)
        if data:
            logger.debug(f"Request data: {data}")
            request_context['data'] = str(data)
        
        for attempt in range(self.max_retries):
            request_context['attempt'] = str(attempt + 1)
            try:
                # Create a connector with SSL verification disabled
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                    ) as response:
                        # Log response status
                        logger.debug(f"Trendyol API response status: {response.status}")
                        request_context['status_code'] = str(response.status)
                        
                        if response.status == 429:  # Rate limit
                            wait_time = self.rate_limit_wait * (2 ** attempt)
                            logger.warning(f"Trendyol rate limit hit, waiting {wait_time} seconds")
                            request_context['wait_time'] = str(wait_time)
                            await asyncio.sleep(wait_time)
                            continue
                            
                        elif response.status == 401 or response.status == 403:
                            response_text = await response.text()
                            logger.error(f"Trendyol authentication error: {response_text}")
                            request_context['response_text'] = response_text
                            error = AuthenticationError(f"Authentication failed: {response.status} - {response_text}")
                            error_handler.log_error(error, request_context)
                            raise error
                        
                        elif response.status >= 500:
                            response_text = await response.text()
                            logger.error(f"Trendyol server error: {response_text}")
                            request_context['response_text'] = response_text
                            
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.info(f"Trendyol server error, retrying in {wait_time} seconds")
                                request_context['wait_time'] = str(wait_time)
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                error = APIError(f"Server error after {self.max_retries} attempts: {response.status} - {response_text}")
                                error_handler.log_error(error, request_context)
                                raise error
                        
                        elif response.status >= 400:
                            response_text = await response.text()
                            logger.error(f"Trendyol client error: {response_text}")
                            request_context['response_text'] = response_text
                            error = APIError(f"Request failed: {response.status} - {response_text}")
                            error_handler.log_error(error, request_context)
                            raise error
                        
                        # Success case
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            response_text = await response.text()
                            logger.warning(f"Trendyol response not JSON: {response_text[:100]}...")
                            return {"text": response_text}
                        
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Trendyol connection error: {str(e)}")
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
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Trendyol response error: {str(e)}")
                request_context['error_type'] = 'ResponseError'
                request_context['status_code'] = str(getattr(e, 'status', 'unknown'))
                
                if getattr(e, 'status', 0) == 429:
                    if attempt < self.max_retries - 1:
                        wait_time = self.rate_limit_wait * (2 ** attempt)
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                        request_context['wait_time'] = str(wait_time)
                        await asyncio.sleep(wait_time)
                    else:
                        error = RateLimitError(f"Rate limit exceeded after {self.max_retries} attempts")
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
                logger.error("Trendyol request timed out")
                request_context['error_type'] = 'Timeout'
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    request_context['wait_time'] = str(wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    error = NetworkError(f"Request timed out after {self.max_retries} attempts")
                    error_handler.log_error(error, request_context)
                    raise error
                    
            except (AuthenticationError, RateLimitError, NetworkError, APIError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during Trendyol API request: {str(e)}")
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

    async def _wait_for_batch_completion(self, batch_id: str) -> Dict[str, Any]:
        """
        Wait for batch operation to complete
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            Batch status response
        """
        max_attempts = 10
        wait_time = 2  # seconds
        
        for attempt in range(max_attempts):
            try:
                # Get batch status
                response = await self._make_request(
                    endpoint=f"/batch-requests/{batch_id}"
                )
                
                # Check if completed
                status = response.get('status')
                if status == 'COMPLETED':
                    return response
                    
                if status == 'FAILED':
                    error_message = response.get('errorMessage', 'Unknown error')
                    error = APIError(f"Batch operation failed: {error_message}")
                    error_context = {
                        'client': 'Trendyol',
                        'operation': '_wait_for_batch_completion',
                        'batch_id': batch_id,
                        'status': status,
                        'error_message': error_message
                    }
                    error_handler.log_error(error, error_context)
                    raise error
                    
                # Wait and retry
                logger.info(f"Batch {batch_id} status: {status}, waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                wait_time *= 1.5  # Increase wait time
                
            except (AuthenticationError, NetworkError, RateLimitError):
                # Re-raise these exceptions
                raise
                
            except APIError as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f"Error checking batch status: {str(e)}, retrying...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    error = APIError(f"Failed to check batch status: {str(e)}")
                    error_context = {
                        'client': 'Trendyol',
                        'operation': '_wait_for_batch_completion',
                        'batch_id': batch_id,
                        'attempt': str(attempt + 1)
                    }
                    error_handler.log_error(error, error_context)
                    raise error
                logger.warning(f"Unexpected error checking batch status: {str(e)}, retrying...")
                await asyncio.sleep(wait_time)
                
        error = APIError(f"Batch operation timed out after {max_attempts} attempts")
        error_context = {
            'client': 'Trendyol',
            'operation': '_wait_for_batch_completion',
            'batch_id': batch_id,
            'attempts': str(max_attempts)
        }
        error_handler.log_error(error, error_context)
        raise error
