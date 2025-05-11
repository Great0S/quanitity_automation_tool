"""
Unified Product Service for managing products across platforms
"""

import asyncio
from typing import Dict, List, Any, Optional, Union, cast
from datetime import datetime
import json
import os
from core.logger import logger
from core.exceptions import APIError
from utils.cache import get_cache
from data.repositories import get_product_repository

class UnifiedProductService:
    """Service for managing products across platforms"""
    
    def __init__(self, api_client: Any, platform_name: str):
        """
        Initialize the product service
        
        Args:
            api_client: API client for the platform
            platform_name: Platform name
        """
        self.api_client = api_client
        self.platform_name = platform_name
        self.cache = get_cache()
        self.product_repo = get_product_repository()
        
    async def get_products(self, force_refresh: bool = False, save_to_db: bool = True, batch_size: int = 50, **kwargs) -> Dict[str, Any]:
        """
        Get products from the platform
        
        Args:
            force_refresh: Force refresh from API
            save_to_db: Whether to save products to database
            batch_size: Number of products to save in each database batch
            **kwargs: Additional arguments for the API client
            
        Returns:
            Dictionary with products and metadata or list of products
        """
        cache_key = f"products:{self.platform_name}"
        
        # Try to get from cache first
        if not force_refresh:
            cached_products = await self.cache.get(cache_key)
            if cached_products:
                logger.info(f"Using cached products for {self.platform_name}")
                return cached_products
        
        # Fetch from API
        logger.info(f"Fetching products from {self.platform_name} API")
        try:
            response = await self.api_client.get_products(**kwargs)
            
            # Handle both dictionary with metadata and direct list of products
            if isinstance(response, dict) and "items" in response:
                products = response["items"]
                metadata = {
                    "total": response.get("total", len(products)),
                    "page": response.get("page", 1),
                    "size": response.get("size", len(products)),
                    "totalPages": response.get("totalPages", 1)
                }
            else:
                # If response is a list or doesn't have 'items' key
                products = response if isinstance(response, list) else []
                metadata = {
                    "total": len(products),
                    "page": 1,
                    "size": len(products),
                    "totalPages": 1
                }
            
            # Cache products with metadata
            result = {
                "items": products,
                **metadata
            }
            await self.cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
            
            # Save to database in batches if requested
            if save_to_db and products:
                logger.info(f"Saving {len(products)} products to database in batches of {batch_size}")
                await self.product_repo.save_products_batch(products, self.platform_name, batch_size)
            
            return result
        except Exception as e:
            logger.error(f"Error fetching products from {self.platform_name}: {str(e)}")
            
            # Try to get from database as fallback
            logger.info(f"Trying to get products from database for {self.platform_name}")
            db_products = await self.product_repo.get_products(self.platform_name)
            
            if db_products:
                logger.info(f"Using database products for {self.platform_name}")
                return {
                    "items": db_products,
                    "total": len(db_products),
                    "page": 1,
                    "size": len(db_products),
                    "totalPages": 1
                }
            
            # Re-raise the exception if no fallback
            raise
    
    async def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data or None if not found
        """
        # Try to get from database first
        product = await self.product_repo.get_product(sku, self.platform_name)
        if product:
            return {
                "sku": sku,
                "data": product
            }
        
        # Fetch from API
        try:
            response = await self.api_client.get_products(sku=sku)
            
            # Handle both dictionary with metadata and direct list of products
            if isinstance(response, dict) and "items" in response:
                products = response["items"]
            else:
                products = response if isinstance(response, list) else []
                
            if products:
                return products[0]
        except Exception as e:
            logger.error(f"Error fetching product {sku} from {self.platform_name}: {str(e)}")
        
        return None
    
    async def update_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update multiple products
        
        Args:
            products: List of products to update
            
        Returns:
            List of update results
        """
        results = []
        
        for product in products:
            try:
                result = await self.update_product(product)
                results.append({
                    "sku": product["sku"],
                    "status": "success",
                    "message": "Product updated successfully"
                })
            except Exception as e:
                logger.error(f"Error updating product {product['sku']} on {self.platform_name}: {str(e)}")
                results.append({
                    "sku": product["sku"],
                    "status": "error",
                    "message": str(e)
                })
        
        return results
    
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product
        
        Args:
            product_data: Product data to update
            
        Returns:
            Update result
        """
        try:
            # Update product via API client
            result = await self.api_client.update_product(product_data)
            
            # Update cache
            cache_key = f"products:{self.platform_name}"
            cached_data = await self.cache.get(cache_key)
            
            if cached_data and isinstance(cached_data, dict) and "items" in cached_data:
                # Update product in cache
                sku = product_data["sku"]
                cached_products = cached_data["items"]
                
                for i, product in enumerate(cached_products):
                    if product["sku"] == sku:
                        # Update product data
                        for key, value in product_data.get("data", {}).items():
                            cached_products[i]["data"][key] = value
                        break
                
                # Update cache
                await self.cache.set(cache_key, cached_data, ttl=3600)
            
            # Update database
            existing_product = await self.product_repo.get_product(
                product_data["sku"], 
                self.platform_name
            )
            
            if existing_product:
                # Update existing product
                for key, value in product_data.get("data", {}).items():
                    existing_product[key] = value
                
                await self.product_repo.save_product(
                    sku=product_data["sku"],
                    platform=self.platform_name,
                    data=existing_product
                )
            
            return result
        except Exception as e:
            logger.error(f"Error updating product {product_data.get('sku')} on {self.platform_name}: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get categories from the platform
        
        Returns:
            List of categories
        """
        try:
            return await self.api_client.get_categories()
        except Exception as e:
            logger.error(f"Error fetching categories from {self.platform_name}: {str(e)}")
            raise APIError(f"Failed to fetch categories: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if the platform API is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.api_client.authenticate()
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.platform_name}: {str(e)}")
            return False