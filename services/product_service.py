from abc import ABC, abstractmethod
from typing import Dict, List, Any, Type
from api.base_client import BaseAPIClient
from core.exceptions import ServiceError
import logging

class BaseProductService(ABC):
    """Abstract base class for product services"""
    
    @abstractmethod
    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from the platform"""
        pass

    @abstractmethod
    async def update_products(self, products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Update multiple products"""
        pass

class ProductService(BaseProductService):
    """Concrete implementation of product service"""
    
    def __init__(self, api_client: BaseAPIClient):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from the platform"""
        try:
            # Await the API client's get_products call
            products = await self.api_client.get_products(**kwargs)
            return products
        except Exception as e:
            self.logger.error(f"Error fetching products: {str(e)}")
            raise ServiceError(f"Failed to fetch products: {str(e)}")

    async def update_products(self, products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Update multiple products"""
        results = []
        errors = []

        for product in products:
            try:
                result = await self.api_client.update_product(product)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku'),
                    'error': str(e)
                })

        if errors:
            self.logger.warning(f"Some products failed to update: {errors}")

        return {
            'updated': results,
            'errors': errors
        }

    def validate_product_data(self, product_data: Dict[str, Any]) -> List[str]:
        """Validate product data"""
        errors = []
        required_fields = ['sku', 'title', 'price', 'quantity']
        
        for field in required_fields:
            if not product_data.get(field):
                errors.append(f"Missing required field: {field}")

        if errors:
            self.logger.warning(f"Product validation errors: {errors}")

        return errors

    def format_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw product data to standard format"""
        return {
            'sku': raw_data.get('sku'),
            'data': {
                'title': raw_data.get('title'),
                'price': float(raw_data.get('price', 0)),
                'salePrice': float(raw_data.get('price', 0)),
                'listPrice': float(raw_data.get('price', 0)),
                'quantity': int(raw_data.get('quantity', 0)),
                'categoryName': raw_data.get('category', ''),
                'description': raw_data.get('description', ''),
                'images': raw_data.get('images', [])
            }
        }
