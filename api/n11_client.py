from typing import Dict, List, Any, Optional
import os
import hashlib
import base64
import hmac
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from core.exceptions import APIError, AuthenticationError
from core.logger import logger
from .base_client import BaseAPIClient

class N11Client(BaseAPIClient):
    """
    N11 API Client
    Handles product management and inventory operations
    """
    
    def __init__(self):
        super().__init__()
        self._setup_credentials()
        self.base_url = "https://api.n11.com/ws"
        self.endpoints = {
            'products': '/ProductService/',
            'orders': '/OrderService/',
            'categories': '/CategoryService/',
            'cities': '/CityService/'
        }

    async def authenticate(self) -> None:
        """
        Authenticate with N11 API
        No explicit authentication needed for N11 as it uses API key/secret for each request
        """
        try:
            # Test authentication by making a simple API call
            test_response = await self._make_request(
                endpoint=f"{self.endpoints['products']}GetProductList",
                params={'currentPage': 1, 'pageSize': 1}
            )
            
            if test_response.get('result', {}).get('status') != 'success':
                raise AuthenticationError("N11 authentication failed")
                
            self.logger.info("N11 authentication successful")
            
        except Exception as e:
            self.logger.error(f"N11 authentication failed: {str(e)}")
            raise AuthenticationError(f"N11 authentication failed: {str(e)}")

    def _setup_credentials(self) -> None:
        """Set up N11 API credentials"""
        self.app_key = os.getenv('N11_APP_KEY')
        self.app_secret = os.getenv('N11_APP_SECRET')
        
        if not all([self.app_key, self.app_secret]):
            raise AuthenticationError("N11 API credentials are missing")
            
        self.auth_params = {
            'appKey': self.app_key,
            'appSecret': self.app_secret
        }
    
    def _setup_endpoints(self) -> None:
        """Setup N11 API endpoints"""
        self.base_url = "https://api.n11.com/ws"
        self.endpoints = {
            'products': '/ProductService/',
            'orders': '/OrderService/',
            'categories': '/CategoryService/',
            'cities': '/CityService/'
        }

    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make API request to N11
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Request parameters
            
        Returns:
            API response data
        """
        try:
            url = f"{self.base_url}{endpoint}"
            auth_params = self.auth_params
            
            if params:
                params.update(auth_params)
            else:
                params = auth_params

            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                raise APIError(f"N11 API request failed: {response.text}")

            return self._parse_response(response.text)
            
        except requests.RequestException as e:
            logger.error(f"N11 API request error: {str(e)}")
            raise APIError(f"N11 API request failed: {str(e)}")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse XML response to dictionary
        
        Args:
            response_text: XML response text
            
        Returns:
            Parsed response data
        """
        try:
            root = ET.fromstring(response_text)
            return self._xml_to_dict(root)
        except ET.ParseError as e:
            logger.error(f"Failed to parse N11 response: {str(e)}")
            raise APIError(f"Failed to parse N11 response: {str(e)}")

    def _xml_to_dict(self, element: ET.Element) -> Any:
        """Convert XML element to dictionary"""
        result = {}
        
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(self._xml_to_dict(child))
                else:
                    result[child.tag] = self._xml_to_dict(child)
                    
        return result

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from N11
        
        Args:
            **kwargs: Optional filters
                - page: Page number
                - size: Items per page
                - status: Product status
                
        Returns:
            List of products
        """
        try:
            params = {
                'currentPage': kwargs.get('page', 1),
                'pageSize': kwargs.get('size', 100),
                'status': kwargs.get('status', 'Active')
            }
            
            response = self._make_request(
                endpoint=f"{self.endpoints['products']}GetProductList",
                params=params
            )
            
            if response.get('result', {}).get('status') != 'success':
                raise APIError(f"Failed to fetch products: {response.get('result', {}).get('errorMessage')}")
            
            products = response.get('products', {}).get('product', [])
            if not isinstance(products, list):
                products = [products] if products else []
            
            return [self._format_product(product) for product in products]
            
        except Exception as e:
            logger.error(f"Error fetching N11 products: {str(e)}")
            raise APIError(f"Failed to fetch N11 products: {str(e)}")

    def _format_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format N11 product data
        
        Args:
            product: Raw product data
            
        Returns:
            Formatted product data
        """
        return {
            'sku': product.get('stockCode'),
            'data': {
                'id': product.get('id'),
                'title': product.get('title'),
                'subtitle': product.get('subtitle'),
                'price': float(product.get('price', 0)),
                'salePrice': float(product.get('salePrice', 0)),
                'description': product.get('description'),
                'category': product.get('category', {}).get('name'),
                'quantity': int(product.get('stockItems', {}).get('stockItem', {}).get('quantity', 0)),
                'images': self._extract_images(product.get('images', {})),
                'attributes': product.get('attributes', {}).get('attribute', []),
                'status': product.get('approvalStatus'),
                'shipping': product.get('shipmentTemplate'),
                'lastUpdate': product.get('lastUpdateDate')
            }
        }

    def _extract_images(self, images: Dict[str, Any]) -> List[str]:
        """Extract image URLs from product data"""
        if not images:
            return []
            
        image_list = images.get('image', [])
        if not isinstance(image_list, list):
            image_list = [image_list] if image_list else []
            
        return [img.get('url') for img in image_list if img.get('url')]

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on N11
        
        Args:
            product_data: Product data to update
            
        Returns:
            Updated product data
        """
        try:
            data = product_data['data']
            params = {
                'productSellerCode': product_data['sku'],
                'price': str(data['price']),
                'quantity': str(data['quantity']),
                'stockItems': {
                    'stockItem': {
                        'quantity': str(data['quantity'])
                    }
                }
            }
            
            # Add optional fields if present
            if 'title' in data:
                params['title'] = data['title']
            if 'description' in data:
                params['description'] = data['description']
            if 'attributes' in data:
                params['attributes'] = data['attributes']
            
            response = self._make_request(
                endpoint=f"{self.endpoints['products']}UpdateProduct",
                method='POST',
                params=params
            )
            
            if response.get('result', {}).get('status') != 'success':
                raise APIError(f"Failed to update product: {response.get('result', {}).get('errorMessage')}")
            
            return product_data
            
        except Exception as e:
            logger.error(f"Error updating N11 product: {str(e)}")
            raise APIError(f"Failed to update N11 product: {str(e)}")

    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get single product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data if found
        """
        try:
            response = self._make_request(
                endpoint=f"{self.endpoints['products']}GetProductBySellerCode",
                params={'sellerCode': sku}
            )
            
            if response.get('result', {}).get('status') != 'success':
                return None
                
            product = response.get('product')
            return self._format_product(product) if product else None
            
        except Exception as e:
            logger.error(f"Error getting N11 product {sku}: {str(e)}")
            return None

    async def delete_product(self, sku: str) -> bool:
        """
        Delete product from N11
        
        Args:
            sku: Product SKU
            
        Returns:
            True if successful
        """
        try:
            response = self._make_request(
                endpoint=f"{self.endpoints['products']}DeleteProductBySellerCode",
                method='POST',
                params={'sellerCode': sku}
            )
            
            return response.get('result', {}).get('status') == 'success'
            
        except Exception as e:
            logger.error(f"Error deleting N11 product {sku}: {str(e)}")
            raise APIError(f"Failed to delete N11 product: {str(e)}")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get N11 categories"""
        try:
            response = self._make_request(
                endpoint=f"{self.endpoints['categories']}GetTopLevelCategories"
            )
            
            if response.get('result', {}).get('status') != 'success':
                raise APIError("Failed to fetch categories")
                
            categories = response.get('categories', {}).get('category', [])
            if not isinstance(categories, list):
                categories = [categories] if categories else []
                
            return categories
            
        except Exception as e:
            logger.error(f"Error fetching N11 categories: {str(e)}")
            raise APIError(f"Failed to fetch N11 categories: {str(e)}")
