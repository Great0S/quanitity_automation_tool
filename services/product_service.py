from abc import ABC, abstractmethod
from typing import Dict, List, Any, Type, Optional
from api.base_client import BaseAPIClient
from core.exceptions import ValidationError, APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger

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
        
    @abstractmethod
    def validate_product_data(self, product_data: Dict[str, Any]) -> List[str]:
        """Validate product data"""
        pass
        
    @abstractmethod
    def format_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw product data to standard format"""
        pass

class ProductService(BaseProductService):
    """Concrete implementation of product service"""
    
    def __init__(self, api_client: BaseAPIClient):
        self.api_client = api_client
        self.logger = logger

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch products from the platform"""
        try:
            # Await the API client's get_products call
            products = await self.api_client.get_products(**kwargs)
            self.logger.info(f"Retrieved {len(products)} products from {self.api_client.__class__.__name__}")
            return products
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error while fetching products: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
            
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded while fetching products: {str(e)}")
            raise AuthenticationError(f"Rate limit exceeded: {str(e)}")
            
        except NetworkError as e:
            self.logger.error(f"Network error while fetching products: {str(e)}")
            raise AuthenticationError(f"Network error: {str(e)}")
            
        except APIError as e:
            self.logger.error(f"API error while fetching products: {str(e)}")
            raise AuthenticationError(f"API error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error while fetching products: {str(e)}")
            raise AuthenticationError(f"Failed to fetch products: {str(e)}")

    async def update_products(self, products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Update multiple products"""
        results = []
        errors = []
        skipped = []

        for product in products:
            try:
                # Validate product data before updating
                validation_errors = self.validate_product_data(product)
                if validation_errors:
                    skipped.append({
                        'sku': product.get('sku', 'unknown'),
                        'reason': f"Validation errors: {', '.join(validation_errors)}"
                    })
                    continue
                
                result = await self.api_client.update_product(product)
                results.append(result)
                self.logger.info(f"Updated product {product.get('sku')} successfully")
                
            except AuthenticationError as e:
                self.logger.error(f"Authentication error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Authentication failed: {str(e)}"
                })
                
            except RateLimitError as e:
                self.logger.error(f"Rate limit exceeded while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Rate limit exceeded: {str(e)}"
                })
                
            except NetworkError as e:
                self.logger.error(f"Network error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Network error: {str(e)}"
                })
                
            except APIError as e:
                self.logger.error(f"API error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"API error: {str(e)}"
                })
                
            except Exception as e:
                self.logger.error(f"Unexpected error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': str(e)
                })

        if errors:
            self.logger.warning(f"{len(errors)} products failed to update")
            
        if skipped:
            self.logger.warning(f"{len(skipped)} products were skipped due to validation errors")

        return {
            'updated': results,
            'errors': errors,
            'skipped': skipped
        }

    def validate_product_data(self, product_data: Dict[str, Any]) -> List[str]:
        """Validate product data"""
        errors = []
        
        # Check if product_data is a dictionary
        if not isinstance(product_data, dict):
            return ["Product data must be a dictionary"]
            
        # Check for required SKU
        if not product_data.get('sku'):
            errors.append("Missing required field: sku")
            
        # Check for data dictionary
        data = product_data.get('data')
        if not isinstance(data, dict):
            errors.append("Missing or invalid 'data' field")
            return errors
            
        # Check required fields in data
        required_fields = ['title', 'price', 'quantity']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
                
        # Validate numeric fields
        if 'price' in data and not isinstance(data['price'], (int, float)) or data.get('price', 0) < 0:
            errors.append("Price must be a non-negative number")
            
        if 'quantity' in data and not isinstance(data['quantity'], int) or data.get('quantity', 0) < 0:
            errors.append("Quantity must be a non-negative integer")

        if errors:
            self.logger.warning(f"Product validation errors for SKU {product_data.get('sku')}: {errors}")

        return errors

    def format_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw product data to standard format"""
        try:
            # Ensure SKU exists
            sku = raw_data.get('sku')
            if not sku:
                raise ValidationError("Missing required field: sku")
                
            # Create standardized product data structure
            return {
                'sku': sku,
                'data': {
                    'title': raw_data.get('title', ''),
                    'price': float(raw_data.get('price', 0)),
                    'salePrice': float(raw_data.get('salePrice', raw_data.get('price', 0))),
                    'listPrice': float(raw_data.get('listPrice', raw_data.get('price', 0))),
                    'quantity': int(raw_data.get('quantity', 0)),
                    'categoryName': raw_data.get('category', ''),
                    'description': raw_data.get('description', ''),
                    'images': raw_data.get('images', [])
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting product data: {str(e)}")
            raise ValidationError(f"Failed to format product data: {str(e)}")
            
    # async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
    #     """Get a single product by SKU"""
    #     try:
    #         # Check if the API client has this method
    #         if hasattr(self.api_client, 'get_product_by_sku'):
    #             product = await self.api_client.get_product_by_sku(sku)
    #             if product:
    #                 self.logger.info(f"Retrieved product with SKU {sku}")
    #             else:
    #                 self.logger.warning(f"Product with SKU {sku} not found")
    #             return product
    #         else:
    #             # Fallback: get all products and filter by SKU
    #             self.logger.info(f"API client doesn't support direct SKU lookup, fetching all products")
    #             products = await self.get_products()
    #             for product in products:
    #                 if product.get('sku') == sku:
    #                     return product
    #             self.logger.warning(f"Product with SKU {sku} not found")
    #             return None
    #             
    #     except Exception as e:
    #         self.logger.error(f"Error retrieving product with SKU {sku}: {str(e)}")
    #         raise ServiceError(f"Failed to retrieve product with SKU {sku}: {str(e)}")