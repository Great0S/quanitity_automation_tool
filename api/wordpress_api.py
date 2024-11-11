from typing import List, Dict, Optional, Union, Any
import logging
import re
import json
from woocommerce import API
from dataclasses import dataclass
import os
from typing_extensions import TypedDict





class ProductData(TypedDict):
    id: int
    sku: str
    price: float
    quantity: int

class WooCommerceProduct(TypedDict):
    name: str
    type: str
    sku: str
    manage_stock: bool
    stock_quantity: int
    stock_status: str
    tax_status: str
    sale_price: str
    regular_price: str
    description: str
    short_description: str
    categories: List[Dict[str, int]]
    images: List[Dict[str, str]]

@dataclass
class WooCommerceAPIConfig:
    url: str = "https://www.emanzemin.com"
    consumer_key: str = os.environ.get("EMANZEMIN_KEY")
    consumer_secret: str = os.environ.get("EMANZEMIN_SECRET")
    version: str = "wc/v3"
    timeout: int = 3000

class WooCommerceAPIClient:
    def __init__(self, config: WooCommerceAPIConfig = WooCommerceAPIConfig()):
        """Initialize WooCommerce API client with configuration."""
        self.logger = logging.getLogger(__name__)
        self.wcapi = API(
            url=config.url,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            version=config.version,
            timeout=config.timeout
        )
        self._categories_cache: Optional[List[Dict[str, Any]]] = None

    def _handle_api_response(self, response, operation: str) -> Optional[Any]:
        """Handle API response and logging."""
        try:
            if response.ok:
                return response.json()
            self.logger.error(f"{operation} failed: Status {response.status_code}, Message: {response.text}")
            return None
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON response for {operation}")
            return None

    def get_all_products(self, every_product: bool = False) -> List[Dict[str, Any]]:
        """Fetch all products with pagination."""
        products: List[Dict[str, Any]] = []
        page = 1
        
        while True:
            response = self.wcapi.get('products', params={"per_page": 100, "page": page})
            current_products = self._handle_api_response(response, "Products fetch")
            
            if not current_products:
                break
                
            products.extend(current_products)
            
            if len(current_products) < 100:
                break
                
            page += 1

        filtered_products = self._filter_products(products, every_product)
        self.logger.info(f"Fetched {len(filtered_products)} products from WordPress")
        return filtered_products

    def _filter_products(self, products: List[Dict[str, Any]], every_product: bool) -> List[Dict[str, Any]]:
        """Filter products based on specified criteria."""
        filtered_products = []
        
        for item in products:
            qty = item.get('stock_quantity', 0)
            
            if every_product:
                filtered_products.append({
                    'sku': item['sku'],
                    'data': item
                })
            else:
                filtered_products.append({
                    'id': item['id'],
                    'sku': item['sku'],
                    'price': float(item.get('price', 0)),
                    'quantity': qty
                })
                
        return filtered_products

    def update_product(self, product_data: ProductData) -> bool:
        """Update a single product's stock and price information."""
        stock_status = 'instock' if int(product_data['quantity']) > 0 else 'outofstock'
        
        update_data = {
            "price": str(product_data['price']),
            'stock_quantity': str(product_data['quantity']),
            'stock_status': stock_status,
            "manage_stock": True
        }
        
        response = self.wcapi.put(f"products/{product_data['id']}", update_data)
        result = self._handle_api_response(response, "Product update")
        
        if result and str(result['stock_quantity']) == str(product_data['quantity']):
            self.logger.info(
                f"Product updated successfully - SKU: {product_data['sku']}, "
                f"New stock: {product_data['quantity']}, New price: {product_data['price']}"
            )
            return True
            
        self.logger.error(f"Failed to update product - SKU: {product_data['sku']}")
        return False

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get product categories with caching."""
        if self._categories_cache is None:
            response = self.wcapi.get("products/categories")
            categories = self._handle_api_response(response, "Categories fetch")
            if categories:
                self._categories_cache = [{'id': cat['id'], 'name': cat['name']} for cat in categories]
            else:
                self._categories_cache = []
        return self._categories_cache

    def create_product(self, product_data: Dict[str, Any]) -> bool:
        """Create a new product with comprehensive data."""
        try:
            category = self._determine_category(product_data['title'])
            attrs = self._format_attributes(product_data.get('attributes', []))
            images = self._format_images(product_data)
            
            new_product_data: WooCommerceProduct = {
                "name": product_data['title'],
                "type": "simple",
                "sku": product_data['stockCode'],
                "manage_stock": product_data['quantity'] > 0,
                "stock_quantity": product_data['quantity'],
                "stock_status": 'instock' if product_data['quantity'] > 0 else 'outofstock',
                "tax_status": "taxable",
                "sale_price": str(product_data['salePrice']),
                "regular_price": str(product_data['listPrice']),
                "description": re.sub(r"[?]", '', product_data['description']) + attrs,
                "short_description": product_data['title'],
                "categories": category,
                "images": images
            }

            response = self.wcapi.post("products", new_product_data)
            
            if response.status_code == 201:
                self.logger.info(f"Created new product successfully - SKU: {product_data['stockCode']}")
                return True
                
            error = self._handle_api_response(response, "Product creation")
            self.logger.error(
                f"Failed to create product - SKU: {product_data['stockCode']}, "
                f"Error: {error.get('message') if error else 'Unknown error'}"
            )
            return False
            
        except Exception as e:
            self.logger.error(f"Exception while creating product: {str(e)}")
            return False

    def _determine_category(self, title: str) -> List[Dict[str, int]]:
        """Determine product category based on title."""
        category_mapping = {
            r'Merdiven': [{'id': 24}, {'id': 17}],
            r'Çim|çim': [{'id': 24}, {'id': 23}],
            r'Renkli&Kapı|kapı|Kapı': [{'id': 24}, {'id': 29}],
            r'Minder|Tatami': [{'id': 24}, {'id': 20}],
            r'Bıçak|Yapıştır': [{'id': 18}],
        }

        for pattern, category in category_mapping.items():
            if re.search(pattern, title):
                return category
        return [{'id': 6}]  # Default category

    def _format_attributes(self, attributes: List[Dict[str, str]]) -> str:
        """Format product attributes as string."""
        attrs = "\n\nÜrün özellikleri: \n"
        for attr in attributes:
            if not re.search('NoColor', attr['attributeValue']):
                attrs += f"{attr['attributeName']}: {attr['attributeValue']}\n"
        return attrs

    def _format_images(self, product_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Format product images for API."""
        return [{
            'src': img['url'],
            'name': product_data['title'],
            'alt': product_data['title']
        } for img in product_data['images']]