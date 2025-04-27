"""
Handles product management and inventory operations with improved error handling and async support
"""

import base64
import os
import json
import asyncio
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import aiohttp
import requests
from circuitbreaker import CircuitBreaker
from core.logger import logger
from core.exceptions import (
    APIError,
    AuthenticationError,
    ValidationError,
    RateLimitError
)

class HepsiburadaClient:
    """Hepsiburada API Client"""

    def __init__(self):
        """Initialize the client with credentials and configuration"""
        self._setup_credentials()
        self._setup_endpoints()
        self._setup_cache()
        self.logger = logger

    def _setup_credentials(self) -> None:
        """Setup API credentials and authentication"""
        try:
            # Get credentials from environment
            merchant_id = os.getenv('HEPSIBURADA_MERCHANT_ID')
            username = os.getenv('HEPSIBURADA_USERNAME')
            password = os.getenv('HEPSIBURADA_PASSWORD')

            if not all([merchant_id, username, password]):
                raise AuthenticationError("Missing required credentials")

            # Create base64 authentication hash
            user_pass = f"{merchant_id}:{password}"
            user_pass_bytes = user_pass.encode('utf-8')
            base64_hash = base64.b64encode(user_pass_bytes).decode('utf-8')

            self.store_id = merchant_id
            self.username = username
            self.headers = {
                "User-Agent": username,
                "Content-Type": "application/json",
                "Authorization": f"Basic {base64_hash}",
            }

        except Exception as e:
            raise AuthenticationError(f"Failed to setup credentials: {str(e)}")

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        self.base_urls = {
            'mpop': "https://mpop.hepsiburada.com",
            'listing': f"https://listing-external.hepsiburada.com/Listings/merchantid/{self.store_id}"
        }

    def _setup_cache(self) -> None:
        """Setup category cache"""
        self.cache_file = Path("cache/hb_categories.json")
        self.cache_file.parent.mkdir(exist_ok=True)
        self.category_cache = {}
        self.cache_ttl = 24 * 60 * 60  # 24 hours

    @CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=APIError
    )
    async def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        subdomain: str = 'mpop',
        data: Any = None,
        params: Dict[str, Any] = None,
        retry_count: int = 3,
        base_delay: int = 1
    ) -> Any:
        """
        Make API request with retry mechanism and error handling
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            subdomain: API subdomain
            data: Request data
            params: Query parameters
            retry_count: Number of retries
            base_delay: Base delay for exponential backoff
            
        Returns:
            API response data
        """
        url = f"{self.base_urls[subdomain]}{endpoint}"
        attempt = 0

        while attempt < retry_count:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data if data else None,
                        params=params,
                        timeout=30
                    ) as response:
                        response_data = await response.text()
                        
                        # Log request details
                        self.logger.log_api_request(
                            method=method,
                            url=url,
                            status_code=response.status,
                            response_size=len(response_data)
                        )

                        if response.status == 200:
                            return json.loads(response_data) if response_data else None
                            
                        if response.status == 429:
                            raise RateLimitError("Rate limit exceeded")
                            
                        if response.status == 401:
                            raise AuthenticationError("Authentication failed")
                            
                        if response.status == 400:
                            error_data = json.loads(response_data)
                            raise ValidationError(f"Bad request: {error_data.get('message', 'Unknown error')}")
                            
                        raise APIError(f"Request failed with status {response.status}: {response_data}")

            except (APIError, RateLimitError) as e:
                attempt += 1
                if attempt == retry_count:
                    raise
                    
                delay = base_delay * (2 ** attempt)
                self.logger.warning(
                    f"Request failed, retrying in {delay}s",
                    attempt=attempt,
                    error=str(e)
                )
                await asyncio.sleep(delay)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from Hepsiburada
        
        Args:
            **kwargs: Optional filters
                - status: Product status
                - page: Page number
                - size: Items per page
                
        Returns:
            List of products
        """
        try:
            # Get current stock data
            stock_data = await self._make_request(
                endpoint="?limit=1000",
                subdomain='listing'
            )

            # Get detailed product data
            products = []
            page = 1
            
            while True:
                response = await self._make_request(
                    endpoint=f"/product/api/products/all-products-of-merchant/{self.store_id}/",
                    params={
                        'size': kwargs.get('size', 100),
                        'page': page
                    }
                )

                if not response or not response.get('data'):
                    break

                # Process products
                for item in response['data']:
                    product = await self._format_product(item, stock_data)
                    if product:
                        products.append(product)

                # Check pagination
                if page >= response['totalPages']:
                    break
                page += 1

            self.logger.info(f"Fetched {len(products)} products from Hepsiburada")
            return products

        except Exception as e:
            self.logger.error(f"Failed to fetch products: {str(e)}")
            raise APIError(f"Failed to fetch products: {str(e)}")

    async def _format_product(self, item: Dict[str, Any], 
                            stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data"""
        try:
            # Find matching stock data
            stock_info = next(
                (listing for listing in stock_data['listings']
                 if listing['merchantSku'] == item['merchantSku']),
                {}
            )

            return {
                'sku': item['merchantSku'],
                'data': {
                    'hbSku': item['hbSku'],
                    'title': item['name'],
                    'description': item.get('description', ''),
                    'price': float(stock_info.get('price', 0)),
                    'quantity': int(stock_info.get('availableStock', 0)),
                    'categoryName': item.get('categoryName', ''),
                    'brand': item.get('brand', ''),
                    'barcode': item.get('barcode', ''),
                    'images': item.get('images', []),
                    'attributes': item.get('attributes', []),
                    'status': item.get('status'),
                    'commission': item.get('commission'),
                    'lastUpdate': datetime.now().isoformat()
                }
            }

        except Exception as e:
            self.logger.error(
                f"Error formatting product {item.get('merchantSku')}: {str(e)}"
            )
            return None

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on Hepsiburada
        
        Args:
            product_data: Product data to update
            
        Returns:
            Updated product data
        """
        try:
            data = product_data['data']
            
            # Prepare update data
            update_data = {
                "merchantId": self.store_id,
                "items": [{
                    "hbSku": data['hbSku'],
                    "merchantSku": product_data['sku'],
                    "productName": data['title'],
                    "productDescription": data.get('description', ''),
                    "price": data['price'],
                    "availableStock": data['quantity'],
                    "images": [
                        {"url": img['url']} for img in data.get('images', [])
                    ],
                    "attributes": data.get('attributes', [])
                }]
            }

            # Create temporary file for update
            temp_file = Path("temp/update.json")
            temp_file.parent.mkdir(exist_ok=True)
            
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(update_data, f)

            # Submit update
            files = {
                "file": ("update.json", open(temp_file, "rb"), "application/json")
            }
            
            response = await self._make_request(
                endpoint="/ticket-api/api/integrator/import",
                method="POST",
                files=files
            )

            if not response.get('success'):
                raise APIError(f"Update failed: {response.get('message')}")

            # Monitor update status
            tracking_id = response['data']['trackingId']
            await self._monitor_update_status(tracking_id)

            return product_data

        except Exception as e:
            self.logger.error(
                f"Failed to update product {product_data['sku']}: {str(e)}"
            )
            raise APIError(f"Failed to update product: {str(e)}")
        finally:
            # Cleanup
            if temp_file.exists():
                temp_file.unlink()

    async def _monitor_update_status(self, tracking_id: str, 
                                   timeout: int = 300) -> None:
        """Monitor update status"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = await self._make_request(
                endpoint=f"/ticket-api/api/integrator/status/{tracking_id}"
            )

            if response['success']:
                self.logger.info(f"Update completed: {response['message']}")
                return

            if 'failed' in response.get('message', '').lower():
                raise APIError(f"Update failed: {response['message']}")

            await asyncio.sleep(5)

        raise APIError("Update status check timed out")

    async def get_categories(self) -> Dict[str, Any]:
        """Get category data with caching"""
        try:
            # Check cache
            if self.cache_file.exists():
                cache_age = time.time() - self.cache_file.stat().st_mtime
                
                if cache_age < self.cache_ttl:
                    with open(self.cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)

            # Fetch categories
            response = await self._make_request(
                endpoint="/product/api/categories/get-all-categories",
                params={'size': 10000}
            )

            categories = {}
            for category in response['data']:
                # Get category attributes
                attrs = await self._get_category_attributes(category['categoryId'])
                
                categories[category['name']] = {
                    'categoryId': category['categoryId'],
                    'baseAttributes': attrs.get('baseAttributes', []),
                    'attributes': attrs.get('attributes', []),
                    'variantAttributes': attrs.get('variantAttributes', [])
                }

            # Update cache
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(categories, f)

            return categories

        except Exception as e:
            self.logger.error(f"Failed to fetch categories: {str(e)}")
            raise APIError(f"Failed to fetch categories: {str(e)}")

    async def _get_category_attributes(self, category_id: str) -> Dict[str, Any]:
        """Get category attributes"""
        try:
            response = await self._make_request(
                endpoint=f"/product/api/categories/{category_id}/attributes"
            )
            return response.get('data', {})
        except Exception as e:
            self.logger.error(
                f"Failed to fetch attributes for category {category_id}: {str(e)}"
            )
            return {}

    async def prepare_product_data(self, items: List[Dict[str, Any]], 
                                 source: str = "", op: str = "") -> List[Dict[str, Any]]:
        """
        Prepare product data for API operations
        
        Args:
            items: Product data to prepare
            source: Source platform
            op: Operation type
            
        Returns:
            Prepared product data
        """
        try:
            ready_data = []
            categories = await self.get_categories()

            for item in items:
                prepared_item = await self._prepare_single_product(
                    item, categories, source, op
                )
                if prepared_item:
                    ready_data.append(prepared_item)

            return ready_data

        except Exception as e:
            self.logger.error(f"Failed to prepare product data: {str(e)}")
            raise APIError(f"Failed to prepare product data: {str(e)}")

    async def _prepare_single_product(
        self, 
        item: Dict[str, Any],
        categories: Dict[str, Any],
        source: str,
        op: str
    ) -> Optional[Dict[str, Any]]:
        """Prepare single product data"""
        try:
            # Extract product data
            data = item.get('data', {})
            if not data:
                return None

            # Find matching category
            category_data = await self._find_matching_category(
                data.get('title', ''),
                categories
            )

            if not category_data:
                self.logger.warning(
                    f"No matching category found for product {data.get('title')}"
                )
                return None

            # Prepare attributes
            attributes = await self._prepare_attributes(data, category_data)

            return {
                "categoryId": category_data['categoryId'],
                "merchant": self.store_id,
                "attributes": attributes
            }

        except Exception as e:
            self.logger.error(
                f"Failed to prepare product {item.get('sku')}: {str(e)}"
            )
            return None

    async def _find_matching_category(
        self,
        product_title: str,
        categories: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find matching category for product"""
        for category_name, category_data in categories.items():
            # Clean category name for matching
            clean_category = re.sub(
                r"(\bPaspas\b|\bPaspaslar\b)",
                "",
                category_name,
                flags=re.IGNORECASE
            ).strip()

            if re.search(clean_category, product_title, re.IGNORECASE):
                return category_data
        return None

    async def _prepare_attributes(
        self,
        data: Dict[str, Any],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare product attributes"""
        attributes = {
            "merchantSku": data.get("stockCode"),
            "VaryantGroupID": data.get("productMainId"),
            "Barcode": data.get("barcode"),
            "UrunAdi": data.get("title"),
            "UrunAciklamasi": data.get("description"),
            "Marka": data.get("brand", "Myfloor"),
            "GarantiSuresi": 24,
            "kg": "1",
            "tax_vat_rate": "8",
            "price": data.get("salePrice", 0),
            "stock": data.get("quantity", 0),
            "Video1": ""
        }

        # Add images
        for i, image in enumerate(data.get("images", []), 1):
            attributes[f"Image{i}"] = image['url']

        # Add category-specific attributes
        if "dip çubuğu" in data.get("title", "").lower():
            attributes.update({
                "renk_variant_property": data.get("color", ""),
                "secenek_variant_property": ""
            })
        elif "Bıçağ" in data.get("title", ""):
            attributes.update({
                "adet_variant_property": 1,
                "ebatlar_variant_property": data.get("size", "")
            })
        elif any(keyword in data.get("title", "")
                for keyword in ["Koko", "Kauçuk", "Halı", "Paspas"]):
            attributes.update({
                "00004LW9": data.get("style", ""),  # Desen / Tema
                "00005JUG": "Var",  # Kaymaz Taban
                "sekil": data.get("shape", "Dikdörtgen"),
                "renk_variant_property": data.get("color", ""),
                "00001CM1": data.get("size", "")  # Ebatlar
            })

        return attributes
