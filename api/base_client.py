import asyncio
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import aiohttp
from core.exceptions import APIError
from core.logger import logger

class BaseAPIClient(ABC):
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated: bool = False
        self.rate_limit_wait: int = 60
        self.request_timeout: int = 30
        self.max_retries: int = 3

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

        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout),
                    **kwargs
                ) as response:
                    if response.status == 429:  # Rate limit
                        await asyncio.sleep(self.rate_limit_wait)
                        continue
                    
                    response.raise_for_status()
                    return await response.json()
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def _validate_response(self, response: Dict[str, Any]) -> None:
        """Validate API response"""
        if not isinstance(response, dict):
            raise APIError("Invalid response format")
