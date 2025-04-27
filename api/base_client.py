from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import requests
import logging
from core.exceptions import APIError
from config.settings import Settings

class BaseAPIClient(ABC):
    def __init__(self):
        self.settings = Settings()
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuantityAutomationTool/1.0'
        })
        self.timeout = self.settings.get('api_timeout', 30)
        self.max_retries = self.settings.get('max_retries', 3)

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the API"""
        pass

    @abstractmethod
    def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Get products from the platform"""
        pass

    @abstractmethod
    def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a product on the platform"""
        pass

    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None, 
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an API request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=endpoint,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise APIError(f"API request failed after {self.max_retries} attempts: {str(e)}")
                continue

    def _validate_response(self, response: Dict[str, Any]) -> None:
        """Validate API response"""
        if not isinstance(response, dict):
            raise APIError("Invalid response format")
        if response.get('status') == 'error':
            raise APIError(response.get('message', 'Unknown error'))
