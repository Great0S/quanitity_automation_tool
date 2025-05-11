from typing import Dict, List, Any, Optional
import os
import json
import requests
from datetime import datetime
import time
from core.exceptions import APIError, AuthenticationError, RateLimitError, NetworkError
from core.logger import logger
from .base_client import BaseAPIClient

class N11Client(BaseAPIClient):
    """
    N11 API Client
    Handles product management and inventory operations
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logger
        self._setup_credentials()
        # Base URL for N11 API
        self.base_url = "https://api.n11.com"
        
        # API endpoints
        self.endpoints = {
            'product_query': '/ms/product-query',
            'product_update': '/ms/product-update',
            'categories': '/cdn/categories',
            'orders': '/ms/order-service',
            'shipping': '/ms/shipping-service'
        }
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def authenticate(self) -> None:
        """
        Authenticate with N11 API
        N11 uses API key in headers for authentication
        """
        try:
            # Print credentials for debugging
            if self.app_key:
                print(f"N11 APP_KEY: {self.app_key[:5]}...")
            else:
                raise AuthenticationError("N11 APP_KEY is not set")
                
            if self.app_secret:
                print(f"N11 APP_SECRET: {self.app_secret[:5]}...")
            else:
                raise AuthenticationError("N11 APP_SECRET is not set")
                
            # Test authentication by getting categories
            try:
                test_response = self._make_request(
                    endpoint=self.endpoints['categories'],
                    method="GET"
                )
                
                # Print response for debugging
                print(f"N11 authentication response type: {type(test_response)}")
                
                # Categories endpoint returns a list of categories
                if not test_response:
                    raise AuthenticationError("N11 authentication failed: Empty response")
                    
                if not isinstance(test_response, list):
                    raise AuthenticationError(f"N11 authentication failed: Unexpected response type {type(test_response)}")
                    
                self.logger.info(f"N11 authentication successful, retrieved {len(test_response)} categories")
                
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(f"N11 connection error: {str(e)}")
                
            except requests.exceptions.Timeout as e:
                raise NetworkError(f"N11 request timed out: {str(e)}")
                
            except requests.exceptions.TooManyRedirects as e:
                raise NetworkError(f"N11 too many redirects: {str(e)}")
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                if status_code == 401 or status_code == 403:
                    raise AuthenticationError(f"N11 authentication failed: Invalid credentials (status code: {status_code})")
                elif status_code == 429:
                    raise RateLimitError(f"N11 rate limit exceeded (status code: {status_code})")
                else:
                    raise APIError(f"N11 HTTP error: {str(e)} (status code: {status_code})")
            
        except AuthenticationError as e:
            self.logger.error(f"N11 authentication error: {str(e)}")
            raise
            
        except RateLimitError as e:
            self.logger.error(f"N11 rate limit error: {str(e)}")
            raise
            
        except NetworkError as e:
            self.logger.error(f"N11 network error: {str(e)}")
            raise
            
        except APIError as e:
            self.logger.error(f"N11 API error: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"N11 unexpected error during authentication: {str(e)}")
            raise AuthenticationError(f"N11 authentication failed: {str(e)}")

    def _setup_credentials(self) -> None:
        """Set up N11 API credentials"""
        self.app_key = os.getenv('N11_APP_KEY')
        self.app_secret = os.getenv('N11_APP_SECRET')
        
        if not self.app_key:
            self.logger.error("N11_APP_KEY environment variable is not set")
        if not self.app_secret:
            self.logger.error("N11_APP_SECRET environment variable is not set")
            
        if not all([self.app_key, self.app_secret]):
            raise AuthenticationError("N11 API credentials are missing")
            
        # According to N11 documentation, appKey and appSecret are added to headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "appKey": self.app_key,
            "appSecret": self.app_secret
        }
        
        # Print debug info
        print(f"N11 headers: {self.headers}")

    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Make API request to N11
        """
        url = f"{self.base_url}{endpoint}"
        
        # Print debug info
        print(f"N11 request URL: {url}")
        print(f"N11 request method: {method}")
        if params:
            print(f"N11 request params: {params}")
        if data:
            print(f"N11 request data: {data}")
        
        # Disable SSL verification for development
        ssl_verify = not (os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true')
        
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=data,
                    timeout=30,
                    verify=ssl_verify
                )
                
                # Print debug info
                print(f"N11 response status: {response.status_code}")
                
                # Handle different status codes
                if response.status_code == 200:
                    # Success
                    try:
                        return response.json()
                    except json.JSONDecodeError as e:
                        print(f"JSON Parse Error: {str(e)}")
                        print(f"Response text: {response.text[:500]}...")  # Print first 500 chars
                        raise APIError(f"Failed to parse N11 response as JSON: {str(e)}")
                        
                elif response.status_code == 401 or response.status_code == 403:
                    # Authentication error
                    error_msg = f"N11 authentication failed: {response.text}"
                    print(error_msg)
                    raise AuthenticationError(error_msg)
                    
                elif response.status_code == 429:
                    # Rate limit error
                    error_msg = f"N11 rate limit exceeded: {response.text}"
                    print(error_msg)
                    
                    # If this is not the last attempt, wait and retry
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Waiting {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError(error_msg)
                        
                else:
                    # Other API errors
                    error_msg = f"N11 API request failed with status {response.status_code}: {response.text}"
                    print(error_msg)
                    raise APIError(error_msg)
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"N11 connection error: {str(e)}"
                print(error_msg)
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise NetworkError(error_msg)
                    
            except requests.exceptions.Timeout as e:
                error_msg = f"N11 request timed out: {str(e)}"
                print(error_msg)
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise NetworkError(error_msg)
                    
            except (AuthenticationError, RateLimitError, NetworkError, APIError):
                # Re-raise these exceptions without wrapping
                raise
                
            except Exception as e:
                error_msg = f"Unexpected error during N11 API request: {str(e)}"
                print(error_msg)
                raise APIError(error_msg)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from N11
        """
        try:
            # According to N11 documentation
            params = {
                'page': kwargs.get('page', 0),  # Page starts from 0
                'size': kwargs.get('size', 20),  # Default 20, max 250
                'saleStatus': kwargs.get('saleStatus', None),  # On_Sale or Out_Of_Stock
                'productStatus': kwargs.get('productStatus', None),  # Active, InCatalogApproval, etc.
                'stockCode': kwargs.get('sku', None)  # Filter by specific SKU
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Use GET for product listing according to documentation
            response = self._make_request(
                endpoint=self.endpoints['product_query'],
                method="GET",
                params=params
            )
            
            # Extract products from the content field
            products = response.get('content', [])
            if not isinstance(products, list):
                products = [products] if products else []
            
            self.logger.info(f"Retrieved {len(products)} products from N11")
            return [self._format_product(product) for product in products]
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error while fetching N11 products: {str(e)}")
            raise
            
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded while fetching N11 products: {str(e)}")
            raise
            
        except NetworkError as e:
            self.logger.error(f"Network error while fetching N11 products: {str(e)}")
            raise
            
        except APIError as e:
            self.logger.error(f"API error while fetching N11 products: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"Unexpected error while fetching N11 products: {str(e)}")
            raise APIError(f"Failed to fetch N11 products: {str(e)}")

    def _format_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format N11 product data
        """
        try:
            return {
                'sku': product.get('stockCode', ''),
                'data': {
                    'id': product.get('n11ProductId', ''),
                    'title': product.get('title', ''),
                    'description': product.get('description', ''),
                    'price': float(product.get('salePrice', 0)),
                    'listPrice': float(product.get('listPrice', 0)),
                    'quantity': int(product.get('quantity', 0)),
                    'category': product.get('categoryId', ''),
                    'images': product.get('imageUrls', []),
                    'attributes': product.get('attributes', []),
                    'status': product.get('status', ''),
                    'saleStatus': product.get('saleStatus', ''),
                    'barcode': product.get('barcode', ''),
                    'vatRate': product.get('vatRate', 0),
                    'commissionRate': product.get('commissionRate', 0),
                    'preparingDay': product.get('preparingDay', 0),
                    'shipmentTemplate': product.get('shipmentTemplate', '')
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting N11 product: {str(e)}")
            # Return a minimal product to avoid breaking the flow
            return {
                'sku': product.get('stockCode', 'unknown'),
                'data': {
                    'title': product.get('title', 'Unknown Product'),
                    'price': 0,
                    'quantity': 0
                }
            }

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on N11
        """
        try:
            sku = product_data.get('sku', '')
            if not sku:
                raise APIError("Cannot update product: SKU is missing")
                
            data = product_data.get('data', {})
            
            # According to N11 documentation for product updates
            update_data = {
                'stockCode': sku,
                'quantity': data.get('quantity', 0),
                'salePrice': data.get('price', 0),
                'listPrice': data.get('listPrice', data.get('price', 0)),
                'preparingDay': data.get('preparingDay', 3)
            }
            
            # Make the update request
            response = self._make_request(
                endpoint=f"{self.endpoints['product_update']}/inventory",
                method="POST",
                data=update_data
            )
            
            # Check response
            if not response.get('success', False):
                error_message = response.get('errorMessage', 'Unknown error')
                raise APIError(f"Failed to update product: {error_message}")
            
            self.logger.info(f"Successfully updated N11 product with SKU: {sku}")
            return product_data
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error while updating N11 product: {str(e)}")
            raise
            
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded while updating N11 product: {str(e)}")
            raise
            
        except NetworkError as e:
            self.logger.error(f"Network error while updating N11 product: {str(e)}")
            raise
            
        except APIError as e:
            self.logger.error(f"API error while updating N11 product: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"Unexpected error while updating N11 product: {str(e)}")
            raise APIError(f"Failed to update N11 product: {str(e)}")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get N11 categories
        """
        try:
            response = self._make_request(
                endpoint=self.endpoints['categories'],
                method="GET"
            )
            
            if not response or not isinstance(response, list):
                raise APIError("Failed to retrieve N11 categories: Invalid response format")
            
            # Process the category tree
            categories = self._process_categories(response)
            self.logger.info(f"Retrieved {len(categories)} categories from N11")
            return categories
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error while fetching N11 categories: {str(e)}")
            raise
            
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded while fetching N11 categories: {str(e)}")
            raise
            
        except NetworkError as e:
            self.logger.error(f"Network error while fetching N11 categories: {str(e)}")
            raise
            
        except APIError as e:
            self.logger.error(f"API error while fetching N11 categories: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"Unexpected error while fetching N11 categories: {str(e)}")
            raise APIError(f"Failed to fetch N11 categories: {str(e)}")
    
    def _process_categories(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process category tree to identify leaf categories
        """
        result = []
        
        def process_category(category, path=""):
            try:
                category_name = category.get('name', '')
                category_id = category.get('id', '')
                new_path = f"{path} > {category_name}" if path else category_name
                
                # Add to result
                result.append({
                    'id': category_id,
                    'name': category_name,
                    'path': new_path,
                    'is_leaf': category.get('subCategories') is None
                })
                
                # Process subcategories
                subcategories = category.get('subCategories', [])
                if subcategories:
                    for subcategory in subcategories:
                        process_category(subcategory, new_path)
            except Exception as e:
                self.logger.error(f"Error processing category: {str(e)}")
        
        # Process each top-level category
        for category in categories:
            process_category(category)
            
        return result