"""
Product service for managing products across platforms
"""

import asyncio
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import APIError
from utils.cache import get_cache
from data.repositories import get_product_repository
from api.platform_factory import get_platform_client
from services.unified_product_service import is_same_product, merge_products

async def get_platforms() -> List[str]:
    """
    Get available platforms
    
    Returns:
        List of platform names
    """
    # Get all available platform clients
    platforms = [
        "Magento",
        "WooCommerce",
        "Shopify",
        "Amazon",
        "eBay",
        "Trendyol",
        "Hepsiburada",
        "N11"
    ]
    
    # Filter out platforms that don't have credentials configured
    available_platforms = []
    for platform in platforms:
        try:
            client = get_platform_client(platform)
            available_platforms.append(platform)
        except Exception as e:
            logger.debug(f"Platform {platform} not available: {str(e)}")
    
    return available_platforms

async def get_products(platform: str, **kwargs) -> Dict[str, Any]:
    """
    Get products from a platform
    
    Args:
        platform: Platform name
        **kwargs: Additional arguments for the API client
        
    Returns:
        Dictionary with products and metadata
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate if needed
        if not client.authenticated:
            await client.authenticate()
        
        # Special handling for Hepsiburada to get all products
        if platform == "Hepsiburada" and not kwargs.get("page") and not kwargs.get("force_refresh"):
            # Use the get_all_products method if available
            if hasattr(client, "get_all_products"):
                logger.info("Using get_all_products method for Hepsiburada")
                all_products = await client.get_all_products()
                logger.info(f"Retrieved {len(all_products)} products from Hepsiburada")
                return {
                    "items": all_products,
                    "total": len(all_products),
                    "page": 1,
                    "size": len(all_products),
                    "totalPages": 1
                }
        
        # Get products from platform
        return await client.get_products(**kwargs)
    except Exception as e:
        logger.error(f"Error getting products from {platform}: {str(e)}")
        raise APIError(f"Failed to get products from {platform}: {str(e)}")

async def get_all_products(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get products from all platforms and combine them
    
    Args:
        force_refresh: Force refresh from API
        
    Returns:
        Dictionary with combined products and metadata
    """
    cache = get_cache()
    cache_key = "products:all"
    
    # Try to get from cache first
    if not force_refresh:
        cached_products = await cache.get(cache_key)
        if cached_products:
            logger.info("Using cached combined products")
            return cached_products
    
    # Get available platforms
    platforms = await get_platforms()
    
    # Fetch products from all platforms
    all_platform_products = {}
    tasks = []
    
    for platform in platforms:
        tasks.append(get_products(platform, force_refresh=force_refresh))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(results):
        platform = platforms[i]
        
        if isinstance(result, Exception):
            logger.error(f"Error fetching products from {platform}: {str(result)}")
            continue
            
        # Add platform name to each product
        if isinstance(result, dict) and "items" in result:
            products = result["items"]
            for product in products:
                product["platform"] = platform
            
            all_platform_products[platform] = products
    
    # Combine products from all platforms
    combined_products = []
    product_groups = {}
    
    # Group similar products
    for platform, products in all_platform_products.items():
        for product in products:
            found_match = False
            
            # Check if product matches any existing group
            for group_id, group in product_groups.items():
                if any(is_same_product(product, p) for p in group):
                    group.append(product)
                    found_match = True
                    break
            
            # If no match found, create a new group
            if not found_match:
                group_id = f"group_{len(product_groups)}"
                product_groups[group_id] = [product]
    
    # Merge products in each group
    for group_id, group in product_groups.items():
        merged_product = merge_products(group)
        combined_products.append(merged_product)
    
    # Sort products by title
    combined_products.sort(key=lambda p: p.get("data", {}).get("title", "").lower())
    
    # Create result
    result = {
        "items": combined_products,
        "total": len(combined_products),
        "page": 1,
        "size": len(combined_products),
        "totalPages": 1
    }
    
    # Cache result
    await cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
    
    return result

async def update_products(platform: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Update products on a platform
    
    Args:
        platform: Platform name
        products: List of products to update
        
    Returns:
        List of update results
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate if needed
        if not client.authenticated:
            await client.authenticate()
        
        # Update products
        results = []
        for product in products:
            try:
                result = await client.update_product(product)
                results.append({
                    "sku": product["sku"],
                    "status": "success",
                    "message": "Product updated successfully"
                })
            except Exception as e:
                logger.error(f"Error updating product {product['sku']} on {platform}: {str(e)}")
                results.append({
                    "sku": product["sku"],
                    "status": "error",
                    "message": str(e)
                })
        
        # Invalidate cache
        cache = get_cache()
        await cache.delete("products:all")
        await cache.delete(f"products:{platform}")
        
        return results
    except Exception as e:
        logger.error(f"Error updating products on {platform}: {str(e)}")
        raise APIError(f"Failed to update products on {platform}: {str(e)}")

async def update_product_across_platforms(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a product across all platforms where it exists
    
    Args:
        product_data: Product data to update
        
    Returns:
        Update results for each platform
    """
    platforms = product_data.get("platforms", [])
    results = {}
    
    for platform in platforms:
        try:
            # Create platform-specific product data
            platform_product = {
                "sku": product_data["sku"],
                "data": product_data.get("data", {})
            }
            
            # Get platform client
            client = get_platform_client(platform)
            
            # Authenticate if needed
            if not client.authenticated:
                await client.authenticate()
            
            # Update product
            result = await client.update_product(platform_product)
            results[platform] = {
                "status": "success",
                "message": "Product updated successfully"
            }
        except Exception as e:
            logger.error(f"Error updating product {product_data['sku']} on {platform}: {str(e)}")
            results[platform] = {
                "status": "error",
                "message": str(e)
            }
    
    # Invalidate cache
    cache = get_cache()
    await cache.delete("products:all")
    for platform in platforms:
        await cache.delete(f"products:{platform}")
    
    return {
        "sku": product_data["sku"],
        "results": results
    }

async def get_product(platform: str, sku: str) -> Optional[Dict[str, Any]]:
    """
    Get a product by SKU
    
    Args:
        platform: Platform name
        sku: Product SKU
        
    Returns:
        Product data or None if not found
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate if needed
        if not client.authenticated:
            await client.authenticate()
        
        # Get product
        products = await client.get_products(sku=sku)
        
        # Handle both dictionary with metadata and direct list of products
        if isinstance(products, dict) and "items" in products:
            items = products["items"]
        else:
            items = products if isinstance(products, list) else []
            
        if items:
            return items[0]
        
        return None
    except Exception as e:
        logger.error(f"Error getting product {sku} from {platform}: {str(e)}")
        raise APIError(f"Failed to get product {sku} from {platform}: {str(e)}")

async def update_product(platform: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a product
    
    Args:
        platform: Platform name
        product_data: Product data to update
        
    Returns:
        Update result
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate if needed
        if not client.authenticated:
            await client.authenticate()
        
        # Update product
        result = await client.update_product(product_data)
        
        # Invalidate cache
        cache = get_cache()
        await cache.delete("products:all")
        await cache.delete(f"products:{platform}")
        
        return result
    except Exception as e:
        logger.error(f"Error updating product {product_data.get('sku')} on {platform}: {str(e)}")
        raise APIError(f"Failed to update product: {str(e)}")

async def get_categories(platform: str) -> List[Dict[str, Any]]:
    """
    Get categories from a platform
    
    Args:
        platform: Platform name
        
    Returns:
        List of categories
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate if needed
        if not client.authenticated:
            await client.authenticate()
        
        # Get categories
        return await client.get_categories()
    except Exception as e:
        logger.error(f"Error getting categories from {platform}: {str(e)}")
        raise APIError(f"Failed to get categories from {platform}: {str(e)}")

async def health_check(platform: str) -> bool:
    """
    Check if a platform API is healthy
    
    Args:
        platform: Platform name
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Authenticate
        await client.authenticate()
        
        return True
    except Exception as e:
        logger.error(f"Health check failed for {platform}: {str(e)}")
        return False