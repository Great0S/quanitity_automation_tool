import asyncio
import time
from typing import Dict, Any, List, Optional, Union, TypeVar
from abc import ABC, abstractmethod
import aiohttp
from core.exceptions import APIError, AuthenticationError, RateLimitError, NetworkError
from core.logger import logger

# Type variable for generic return types
T = TypeVar('T')

class BaseAPIClient(ABC):
    """Base API client with common functionality for all API clients"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated: bool = False
        self.rate_limit_wait: int = 60
        self.request_timeout: int = 30  # Store as simple integer instead of ClientTimeout object
        self.max_retries: int = 3
        self.retry_delay: int = 2  # seconds
        self._loop = None  # Store the event loop used to create the session

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()

    async def _ensure_session(self) -> None:
        """Ensure a valid session exists in the current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
            
            # If session doesn't exist or was created in a different loop, create a new one
            if (self.session is None or 
                getattr(self.session, 'closed', True) or  # Use getattr to safely check closed attribute
                self._loop is not current_loop):
                
                # Close existing session if it exists
                await self._close_session()
                
                # Create new session in current loop
                connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for development
                self.session = aiohttp.ClientSession(connector=connector)
                self._loop = current_loop
                logger.debug("Created new aiohttp ClientSession")
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            # Make sure we don't have a partially initialized session
            self.session = None
            self._loop = None
            raise

    async def _close_session(self) -> None:
        """Close the session if it exists"""
        if self.session is not None:
            try:
                if not getattr(self.session, 'closed', False):
                    await self.session.close()
                    logger.debug("Closed aiohttp ClientSession")
            except Exception as e:
                logger.warning(f"Error closing session: {str(e)}")
            finally:
                self.session = None
                self._loop = None

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the API"""
        pass

    @abstractmethod
    async def get_products(self, **kwargs) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get products from the API"""
        pass

    @abstractmethod
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product in the API"""
        pass

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
) ->     Any:
        """Make HTTP request with retry mechanism"""
        await self._ensure_session()

        if self.session is None:
            raise NetworkError("Failed to create a valid HTTP session")

        logger.debug(f"API request: {method} {url}")
        if 'params' in kwargs:
            logger.debug(f"Request params: {kwargs['params']}")
        if 'json' in kwargs:
            logger.debug(f"Request data: {kwargs['json']}")
        if 'headers' in kwargs:
            safe_headers = {k: v for k, v in kwargs['headers'].items()
                            if k.lower() not in ('authorization', 'appkey', 'appsecret')}
            logger.debug(f"Request headers: {safe_headers}")

        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.request_timeout

        for attempt in range(self.max_retries):
            try:
                if self.session is None or getattr(self.session, 'closed', True):
                    logger.warning("Session is None or closed, recreating...")
                    await self._ensure_session()
                    if self.session is None:
                        raise NetworkError("Failed to create a valid HTTP session")

                async with self.session.request(
                    method=method,
                    url=url,
                    **kwargs
                ) as response:
                    logger.debug(f"Response status: {response.status}")

                    if response.status == 429:
                        wait_time = self.rate_limit_wait * (2 ** attempt)
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                        await asyncio.sleep(wait_time)
                        continue

                    elif response.status == 401 or response.status == 403:
                        response_text = await response.text()
                        logger.error(f"Authentication error: {response_text}")
                        raise AuthenticationError(f"Authentication failed: {response.status} - {response_text}")

                    elif response.status >= 500:
                        response_text = await response.text()
                        logger.error(f"Server error: {response_text}")
                        if attempt < self.max_retries - 1:
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.info(f"Server error, retrying in {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise APIError(f"Server error after {self.max_retries} attempts: {response.status} - {response_text}")

                    elif response.status >= 400:
                        response_text = await response.text()
                        logger.error(f"Client error: {response_text}")
                        raise APIError(f"Request failed: {response.status} - {response_text}")

                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        return await response.text()

            except aiohttp.ClientConnectorError as e:
                logger.error(f"Connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Connection error after {self.max_retries} attempts: {str(e)}")

            except asyncio.TimeoutError:
                logger.error("Request timed out")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Timeout, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Request timed out after {self.max_retries} attempts")

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")

        raise APIError(f"Request failed after {self.max_retries} attempts")
    
    def _validate_response(self, response: Any) -> None:
        """Validate API response"""
        if response is None:
            raise APIError("Empty response received")
            
        if isinstance(response, dict):
            # Check for common error indicators in response
            if 'error' in response:
                error_msg = response.get('error', {}).get('message', str(response['error']))
                raise APIError(f"API error: {error_msg}")
                
            if 'errors' in response and response['errors']:
                error_msg = str(response['errors'])
                raise APIError(f"API errors: {error_msg}")
                
        elif isinstance(response, str) and response.strip() == '':
            raise APIError("Empty response received")
    
    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data or None if not found
        """
        # Default implementation - override in subclasses for more efficient implementation
        response = await self.get_products(sku=sku)
        
        # Handle both dictionary with metadata and direct list of products
        if isinstance(response, dict) and "items" in response:
            products = response["items"]
        else:
            products = response if isinstance(response, list) else []
            
        return products[0] if products else None
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get categories from the API
        
        Returns:
            List of categories
        """
        # Default implementation - override in subclasses
        raise NotImplementedError("get_categories method not implemented")
    
    async def health_check(self) -> bool:
        """
        Check if the API is healthy
        
        Returns:
            True if the API is healthy, False otherwise
        """
        try:
            await self.authenticate()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False