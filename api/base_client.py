import asyncio
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import aiohttp
from core.exceptions import APIError, AuthenticationError, RateLimitError, NetworkError
from core.logger import logger

class BaseAPIClient(ABC):
    """Base API client with common functionality for all API clients"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated: bool = False
        self.rate_limit_wait: int = 60
        self.request_timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: int = 2  # seconds

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the API"""
        pass

    @abstractmethod
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
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
        **kwargs
    ) -> Any:
        """Make HTTP request with retry mechanism"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Print debug info
        logger.debug(f"API request: {method} {url}")
        if 'params' in kwargs:
            logger.debug(f"Request params: {kwargs['params']}")
        if 'json' in kwargs:
            logger.debug(f"Request data: {kwargs['json']}")
        if 'headers' in kwargs:
            # Don't log sensitive headers like Authorization
            safe_headers = {k: v for k, v in kwargs['headers'].items() 
                           if k.lower() not in ('authorization', 'appkey', 'appsecret')}
            logger.debug(f"Request headers: {safe_headers}")

        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout),
                    **kwargs
                ) as response:
                    # Log response status
                    logger.debug(f"Response status: {response.status}")
                    
                    if response.status == 429:  # Rate limit
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
                    
                    # Success case
                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        # If not JSON, return text
                        return await response.text()
                    
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise NetworkError(f"Connection error after {self.max_retries} attempts: {str(e)}")
                    
            except aiohttp.ClientResponseError as e:
                logger.error(f"Response error: {str(e)}")
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
                logger.error("Request timed out")
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
                logger.error(f"Unexpected error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Unexpected error, retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")

        # This should never be reached due to the raise statements above
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