"""
Products API routes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.auth import get_current_user
from services import product_service
from utils.background_tasks import TaskManager

router = APIRouter()
task_manager = TaskManager()

@router.get("/platforms")
async def get_platforms(current_user: Dict = Depends(get_current_user)):
    """
    Get available platforms
    
    Returns:
        List of platform names
    """
    platforms = await product_service.get_platforms()
    return {"platforms": platforms}

@router.get("/all")
async def get_all_products(
    force_refresh: bool = False,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get products from all platforms
    
    Args:
        force_refresh: Force refresh from API
        
    Returns:
        Task ID for background task
    """
    # Create background task
    task_id = task_manager.create_task(
        name="Get All Products",
        description=f"Fetching products from all platforms"
    )
    
    # Submit task
    task_manager.submit_async_task(
        product_service.get_all_products,
        task_id=task_id,
        force_refresh=force_refresh
    )
    
    return {"task_id": task_id}

@router.get("/{platform}")
async def get_products(
    platform: str,
    page: int = 1,
    size: int = 20,
    force_refresh: bool = False,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get products from a platform
    
    Args:
        platform: Platform name
        page: Page number
        size: Page size
        force_refresh: Force refresh from API
        
    Returns:
        Task ID for background task
    """
    # Create background task
    task_id = task_manager.create_task(
        name=f"Get {platform} Products",
        description=f"Fetching products from {platform}"
    )
    
    # Submit task
    task_manager.submit_async_task(
        product_service.get_products,
        task_id=task_id,
        platform=platform,
        page=page,
        size=size,
        force_refresh=force_refresh
    )
    
    return {"task_id": task_id}

@router.post("/{platform}")
async def update_products(
    platform: str,
    products: List[Dict[str, Any]],
    current_user: Dict = Depends(get_current_user)
):
    """
    Update products on a platform
    
    Args:
        platform: Platform name
        products: List of products to update
        
    Returns:
        Task ID for background task
    """
    # Create background task
    task_id = task_manager.create_task(
        name=f"Update {platform} Products",
        description=f"Updating {len(products)} products on {platform}"
    )
    
    # Submit task
    task_manager.submit_async_task(
        product_service.update_products,
        task_id=task_id,
        platform=platform,
        products=products
    )
    
    return {"task_id": task_id}

@router.post("/update/across-platforms")
async def update_product_across_platforms(
    product: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Update a product across all platforms where it exists
    
    Args:
        product: Product data to update
        
    Returns:
        Task ID for background task
    """
    # Create background task
    task_id = task_manager.create_task(
        name=f"Update Product Across Platforms",
        description=f"Updating product {product.get('sku')} across platforms"
    )
    
    # Submit task
    task_manager.submit_async_task(
        product_service.update_product_across_platforms,
        task_id=task_id,
        product_data=product
    )
    
    return {"task_id": task_id}

@router.get("/{platform}/{sku}")
async def get_product(
    platform: str,
    sku: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a product by SKU
    
    Args:
        platform: Platform name
        sku: Product SKU
        
    Returns:
        Product data
    """
    product = await product_service.get_product(platform, sku)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found on {platform}")
    return product

@router.get("/{platform}/categories")
async def get_categories(
    platform: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get categories from a platform
    
    Args:
        platform: Platform name
        
    Returns:
        List of categories
    """
    categories = await product_service.get_categories(platform)
    return {"categories": categories}

@router.get("/{platform}/health")
async def health_check(
    platform: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Check if a platform API is healthy
    
    Args:
        platform: Platform name
        
    Returns:
        Health status
    """
    is_healthy = await product_service.health_check(platform)
    return {"platform": platform, "healthy": is_healthy}