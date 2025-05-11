# api/trendyol_client.py
import asyncio
import os
import base64
from typing import Dict, List, Any, Optional
import aiohttp
from datetime import datetime
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
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
                logger.error(f"Trendyol connection error: {str(e)}")
                raise NetworkError(f"Trendyol connection error: {str(e)}")
                
            except aiohttp.ClientResponseError as e:
                if e.status == 401 or e.status == 403:
                    logger.error(f"Trendyol authentication failed: Invalid credentials")
                    raise AuthenticationError("Trendyol authentication failed: Invalid credentials")
                elif e.status == 429:
                    logger.error(f"Trendyol rate limit exceeded")
                    raise RateLimitError("Trendyol rate limit exceeded")
                else:
                    logger.error(f"Trendyol API error: {str(e)}")
                    raise APIError(f"Trendyol API error: {str(e)}")
                    
            except asyncio.TimeoutError:
                logger.error("Trendyol API request timed out")
                raise NetworkError("Trendyol API request timed out")
                
        except AuthenticationError as e:
            logger.error(f"Trendyol authentication error: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Trendyol network error: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Trendyol rate limit error: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error during Trendyol authentication: {str(e)}")
            raise AuthenticationError(f"Trendyol authentication failed: {str(e)}")

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
                'approved': kwargs.get('approved', True)
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
            formatted_products = [self._format_product(product) for product in products]
            return [p for p in formatted_products if p]  # Filter out None values
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while fetching Trendyol products: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while fetching Trendyol products: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while fetching Trendyol products: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while fetching Trendyol products: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while fetching Trendyol products: {str(e)}")
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
            logger.error(f"Error formatting Trendyol product: {str(e)}")
            return None

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
                raise APIError("Cannot update product: SKU is missing")
                
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
                raise APIError(f"Failed to update product: Invalid response")
                
            # Get batch ID
            batch_id = response['batchRequestId']
            logger.info(f"Trendyol update batch ID: {batch_id}")
            
            # Wait for batch completion
            batch_result = await self._wait_for_batch_completion(batch_id)
            
            # Check for errors
            if batch_result.get('status') != 'COMPLETED':
                error_message = batch_result.get('errorMessage', 'Unknown error')
                raise APIError(f"Failed to update product: {error_message}")
                
            logger.info(f"Successfully updated Trendyol product with SKU: {sku}")
            return product_data
            
        except AuthenticationError as e:
            logger.error(f"Authentication error while updating Trendyol product: {str(e)}")
            raise
            
        except NetworkError as e:
            logger.error(f"Network error while updating Trendyol product: {str(e)}")
            raise
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded while updating Trendyol product: {str(e)}")
            raise
            
        except APIError as e:
            logger.error(f"API error while updating Trendyol product: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error while updating Trendyol product: {str(e)}")
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
        
        # Disable SSL verification for development
        ssl_verify = not (os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true')
        
        # Log request details (without sensitive info)
        logger.debug(f"Trendyol API request: {method} {url}")
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
                        logger.debug(f"Trendyol API response status: {response.status}")
                        
                        if response.status == 429:  # Rate limit
                            wait_time = self.rate_limit_wait * (2 ** attempt)
                            logger.warning(f"Trendyol rate limit hit, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        elif response.status == 401 or response.status == 403:
                            response_text = await response.text()
                            logger.error(f"Trendyol authentication error: {response_text}")
                            raise AuthenticationError(f"Authentication failed: {response.status} - {response_text}")
                        
                        elif response.status >= 500:
                            response_text = await response.text()
                            logger.error(f"Trendyol server error: {response_text}")
                            
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.info(f"Trendyol server error, retrying in {wait_time} seconds")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise APIError(f"Server error after {self.max_retries} attempts: {response.status} - {response_text}")
                        
                        elif response.status >= 400:
                            response_text = await response.text()
                            logger.error(f"Trendyol client error: {response_text}")
                            raise APIError(f"Request failed: {response.status} - {response_text}")
                        
                        # Success case
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            response_text = await response.text()
                            logger.warning(f"Trendyol response not JSON: {response_text[:100]}...")
                            return {"text": response_text}
                        
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Trendyol connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Connection error after {self.max_retries} attempts: {str(e)}")
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Trendyol response error: {str(e)}")
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
                logger.error("Trendyol request timed out")
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
                logger.error(f"Unexpected error during Trendyol API request: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")

        # This should never be reached due to the raise statements above
        raise APIError(f"Request failed after {self.max_retries} attempts")

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
                    raise APIError(f"Batch operation failed: {error_message}")
                    
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
                    raise APIError(f"Failed to check batch status: {str(e)}")
                logger.warning(f"Unexpected error checking batch status: {str(e)}, retrying...")
                await asyncio.sleep(wait_time)
                
        raise APIError(f"Batch operation timed out after {max_attempts} attempts")