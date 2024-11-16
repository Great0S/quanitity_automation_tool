import os
import json
import time
import re
from box import Box
import requests
from typing import Optional, List, Dict, Union
from dataclasses import dataclass
from enum import Enum
from app.config.logging_init import logger
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


@dataclass
class ProductData:
    """Data class for product information"""
    sku: str
    barcode: Optional[str]
    quantity: int
    price: float
    title: Optional[str] = None
    product_main_id: Optional[str] = None
    raw_data: Optional[Dict] = None

class RequestType(Enum):
    """Enum for HTTP request types"""
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"

class TrendyolAPIError(Exception):
    """Custom exception for Trendyol API errors"""
    pass

class TrendyolClient:
    """
    A client for interacting with the Trendyol API.
    
    This class provides methods for fetching, updating, and deleting product data
    from Trendyol's e-commerce platform.
    """
    
    BASE_URL = "https://api.trendyol.com/sapigw/suppliers"
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    RATE_LIMIT_WAIT = 15
    REQUEST_TIMEOUT = 3000

    def __init__(self, store_id: Optional[str] = None, auth_hash: Optional[str] = None, logger=None):
        """
        Initialize the Trendyol client.
        
        Args:
            store_id: The store ID for Trendyol API
            auth_hash: The authentication hash for Trendyol API
            logger: Optional custom logger instance
        """
        self.store_id = store_id or os.getenv('TRENDYOLSTOREID')
        self.auth_hash = auth_hash or os.getenv('TRENDYOLAUTHHASH')
        
        if not self.store_id or not self.auth_hash:
            raise ValueError("Store ID and Auth Hash must be provided either directly or through environment variables")
        
        self.headers = {
            'User-Agent': f'{self.store_id} - SelfIntegration',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.auth_hash}'
        }

    def _make_request(
        self, 
        endpoint: str, 
        request_type: RequestType, 
        payload: Optional[Dict] = None,
        retries: int = MAX_RETRIES
    ) -> requests.Response:
        """
        Make an HTTP request to the Trendyol API with retry logic.
        
        Args:
            endpoint: API endpoint to call
            request_type: Type of HTTP request
            payload: Optional request payload
            retries: Number of retries for failed requests
            
        Returns:
            Response object from the API
            
        Raises:
            TrendyolAPIError: If the request fails after all retries
        """
        url = f"{self.BASE_URL}/{self.store_id}{endpoint}"
        payload_data = json.dumps(payload) if payload else {}
        
        for attempt in range(retries):
            try:
                response = requests.request(
                    request_type.value,
                    url,
                    headers=self.headers,
                    data=payload_data,
                    timeout=self.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 400:
                    raise TrendyolAPIError(f"Malformed request: {response.text}")
                elif response.status_code == 429:
                    logger.warning("Rate limit reached, waiting...")
                    time.sleep(self.RATE_LIMIT_WAIT)
                    continue
                    
                response.raise_for_status()
                
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise TrendyolAPIError(f"Request failed after {retries} attempts: {str(e)}")
                    
                logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
        raise TrendyolAPIError(f"Request failed after {retries} attempts")

    def _wait_for_batch_completion(self, batch_request_id: str) -> Dict:
        """
        Wait for a batch request to complete and return the result.
        
        Args:
            batch_request_id: The ID of the batch request to monitor
            
        Returns:
            Dict containing the batch request results
        """
        while True:
            response = self._make_request(
                f'/products//batch-requests/{batch_request_id}',
                RequestType.GET
            )
            batch_status = response.json()
            
            if len(batch_status['items']) > 0 and batch_status['items'][0].get('status') == 'SUCCESS':
                return batch_status
            
            time.sleep(5)

    def get_stock_data(
        self, 
        include_full_data: bool = False, 
        filters: str = '',
        page_size: int = BATCH_SIZE
    ) -> List[ProductData]:
        """
        Fetch product stock data from Trendyol.
        
        Args:
            include_full_data: Whether to include complete product data
            filters: Additional filters for the API request
            page_size: Number of items per page
            
        Returns:
            List of ProductData objects
        """
        
        page = 0
        products = []
        
        while True:
            uri_addon = f"?page={page}&size={page_size}{filters}"
            response = self._make_request(f"/products{uri_addon}", RequestType.GET)
            data = response.json()
            
            if not data['content']:
                break
                
            for item in data['content']:
                # product = ProductData(
                #     sku=item.get('stockCode') or item.get('productMainId'),
                #     barcode=item.get('barcode'),
                #     quantity=item.get('quantity', 0),
                #     price=item.get('salePrice', 0.0),
                #     title=item.get('title'),
                #     product_main_id=item.get('productMainId'),
                #     raw_data=item if include_full_data else None
                # )
                if include_full_data:
                    product = {'sku': item.get('stockCode') or item.get('productMainId'), "data": item, "platform": "trendyol"}
                else:
                    product = {"sku": item.get('stockCode') or item.get('productMainId'),
                               "id": item.get('barcode'),
                               "quantity": item.get('quantity', 0),
                               "price": item.get('salePrice', 0.0),
                               "title": item.get('title'),
                               "product_main_id": item.get('productMainId')}
                products.append(product)
            
            if page >= int(data['totalPages']) - 1:
                break
                
            page += 1
            
        logger.info(f"Retrieved {len(products)} products from Trendyol")
        return products

    def update_product(self, product: ProductData) -> bool:
        """
        Update a product's price and inventory on Trendyol.
        
        Args:
            product: ProductData object containing the update information
            
        Returns:
            bool indicating success or failure
        """
        product = Box(product)
        payload = {
            "items": [{
                "barcode": product.id,
                "quantity": int(product.quantity),
                "salePrice": float(product.price)
            }]
        }
        
        try:
            response = self._make_request(
                "/products/price-and-inventory",
                RequestType.POST,
                payload
            )
            
            batch_status = self._wait_for_batch_completion(
                response.json()['batchRequestId']
            )
            
            if not batch_status['items']:
                return False
                
            status = batch_status['items'][0]['status']
            
            if status == 'SUCCESS':
                logger.info(
                    f'Product {product.sku} updated: '
                    f'quantity={product.quantity}, price={product.price}'
                )
                return True
            else:
                logger.error(
                    f'Failed to update product {product.sku}: '
                    f'{batch_status["items"][0].get("failureReasons")}'
                )
                return False
                
        except TrendyolAPIError as e:
            logger.error(f"Error updating product {product.sku}: {str(e)}")
            return False

    def delete_products(
        self, 
        products: List[ProductData], 
        include_pattern: str,
        exclude_pattern: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Delete multiple products from Trendyol based on title patterns.
        
        Args:
            products: List of ProductData objects to potentially delete
            include_pattern: Regex pattern for titles to include
            exclude_pattern: Optional regex pattern for titles to exclude
            
        Returns:
            Dict containing counts of successful and failed deletions
        """
        items_to_delete = []
        
        for product in products:
            if not product.title or not product.barcode:
                continue
                
            if re.search(include_pattern, product.title):
                if exclude_pattern and re.search(exclude_pattern, product.title):
                    continue
                    
                items_to_delete.append({"barcode": product.barcode})
        
        if not items_to_delete:
            return {"successful": 0, "failed": 0}
            
        try:
            response = self._make_request(
                "/v2/products",
                RequestType.DELETE,
                {"items": items_to_delete}
            )
            
            batch_status = self._wait_for_batch_completion(
                response.json()['batchRequestId']
            )
            
            failed_items = [
                item for item in batch_status['items']
                if item['status'] == 'FAILED'
            ]
            
            for failed in failed_items:
                logger.error(
                    f"Failed to delete {failed['requestItem']['barcode']}: "
                    f"{failed['failureReasons'][0]}"
                )
            
            successful = batch_status['itemCount'] - len(failed_items)
            logger.info(
                f"Deleted {successful} products, {len(failed_items)} failed"
            )
            
            return {
                "successful": successful,
                "failed": len(failed_items)
            }
            
        except TrendyolAPIError as e:
            logger.error(f"Error in batch deletion: {str(e)}")
            return {"successful": 0, "failed": len(items_to_delete)}