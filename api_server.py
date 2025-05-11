"""
FastAPI server for the Quantity Automation Tool
"""

import os
import asyncio
import uvicorn
from typing import Dict, List, Any, Optional, cast
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
import jwt
from dotenv import load_dotenv

from core.logger import logger
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from api.wordpress_client import WordPressClient
from api.opencart_client import OpenCartClient
from api.magento import MagentoClient
from api.trendyol_client import TrendyolClient
from api.hepsiburada_client import HepsiburadaClient
from api.n11_client import N11Client
from api.pazarama_client import PazaramaClient
from api.pttavm_client import PTTAVMClient
from api.amazon_client import AmazonClient
from auth.simple_auth import (
    User,
    Token,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user,
    users_db,
)
from utils.background_tasks import TaskManager, get_task_manager
from services.unified_product_service import UnifiedProductService
from services.unified_sync_service import UnifiedSyncService

# Load environment variables
load_dotenv()

# Constants
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours

# Initialize FastAPI app
app = FastAPI(
    title="Quantity Automation Tool API",
    description="API for managing product quantities across multiple platforms",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Type", "Authorization"]
)

# Initialize task manager
task_manager = get_task_manager()

# Initialize API clients
clients: Dict[str, UnifiedProductService] = {}
initialization_errors: Dict[str, str] = {}

# Request models
class ProductUpdate(BaseModel):
    sku: str
    price: Optional[float] = None
    quantity: Optional[int] = None
    status: Optional[str] = None

class SyncRequest(BaseModel):
    source_platform: str
    target_platforms: List[str]
    filter_skus: Optional[List[str]] = None
    batch_size: Optional[int] = 50
    fields: Optional[List[str]] = ["price", "quantity", "status"]

class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Initialize API clients
@app.on_event("startup")
async def startup_event():
    """Initialize API clients on startup"""
    try:
        # Initialize WordPress client
        try:
            if os.getenv("WP_URL") and os.getenv("WP_USERNAME") and os.getenv("WP_PASSWORD"):
                wp_client = WordPressClient()
                await wp_client.authenticate()
                clients["WordPress"] = UnifiedProductService(wp_client, "WordPress")
                logger.info("WordPress client initialized")
            else:
                logger.warning("WordPress credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize WordPress client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["WordPress"] = error_msg

        # Initialize OpenCart client
        try:
            if os.getenv("OC_URL") and os.getenv("OC_API_KEY"):
                oc_client = OpenCartClient()
                await oc_client.authenticate()
                clients["OpenCart"] = UnifiedProductService(oc_client, "OpenCart")
                logger.info("OpenCart client initialized")
            else:
                logger.warning("OpenCart credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize OpenCart client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["OpenCart"] = error_msg

        # Initialize Magento client
        try:
            if os.getenv("MAGENTO_URL") and os.getenv("MAGENTO_ACCESS_TOKEN"):
                magento_client = MagentoClient()
                await magento_client.authenticate()
                clients["Magento"] = UnifiedProductService(magento_client, "Magento")
                logger.info("Magento client initialized")
            else:
                logger.warning("Magento credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize Magento client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["Magento"] = error_msg

        # Initialize Trendyol client
        try:
            if os.getenv("TRENDYOL_API_KEY") and os.getenv("TRENDYOL_API_SECRET"):
                trendyol_client = TrendyolClient()
                await trendyol_client.authenticate()
                clients["Trendyol"] = UnifiedProductService(trendyol_client, "Trendyol")
                logger.info("Trendyol client initialized")
            else:
                logger.warning("Trendyol credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize Trendyol client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["Trendyol"] = error_msg

        # Initialize N11 client
        try:
            if os.getenv("N11_APP_KEY") and os.getenv("N11_APP_SECRET"):
                n11_client = N11Client()
                await n11_client.authenticate()
                clients["N11"] = UnifiedProductService(n11_client, "N11")
                logger.info("N11 client initialized")
            else:
                logger.warning("N11 credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize N11 client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["N11"] = error_msg

        # Initialize Pazarama client
        try:
            if os.getenv("PAZARAMA_API_KEY") and os.getenv("PAZARAMA_API_SECRET"):
                pazarama_client = PazaramaClient()
                await pazarama_client.authenticate()
                clients["Pazarama"] = UnifiedProductService(pazarama_client, "Pazarama")
                logger.info("Pazarama client initialized")
            else:
                logger.warning("Pazarama credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize Pazarama client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["Pazarama"] = error_msg

        # Initialize PTTAVM client
        try:
            if os.getenv("PTTAVM_API_KEY") and os.getenv("PTTAVM_API_SECRET"):
                pttavm_client = PTTAVMClient()
                await pttavm_client.authenticate()
                clients["PTTAVM"] = UnifiedProductService(pttavm_client, "PTTAVM")
                logger.info("PTTAVM client initialized")
            else:
                logger.warning("PTTAVM credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize PTTAVM client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["PTTAVM"] = error_msg

        # Initialize Amazon client
        try:
            if os.getenv("AMAZON_ACCESS_KEY") and os.getenv("AMAZON_SECRET_KEY"):
                amazon_client = AmazonClient()
                await amazon_client.authenticate()
                clients["Amazon"] = UnifiedProductService(amazon_client, "Amazon")
                logger.info("Amazon client initialized")
            else:
                logger.warning("Amazon credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize Amazon client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["Amazon"] = error_msg

        # Initialize Hepsiburada client
        try:
            if os.getenv("HEPSIBURADA_USERNAME") and os.getenv("HEPSIBURADA_PASSWORD"):
                hepsiburada_client = HepsiburadaClient()
                await hepsiburada_client.authenticate()
                clients["Hepsiburada"] = UnifiedProductService(hepsiburada_client, "Hepsiburada")
                logger.info("Hepsiburada client initialized")
            else:
                logger.warning("Hepsiburada credentials not found, skipping initialization")
        except Exception as e:
            error_msg = f"Failed to initialize Hepsiburada client: {str(e)}"
            logger.error(error_msg)
            initialization_errors["Hepsiburada"] = error_msg

    except Exception as e:
        error_msg = f"Failed to initialize API clients: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# API endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(hours=JWT_EXPIRATION)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/platforms", response_model=Dict[str, Any])
async def get_platforms(current_user: User = Depends(get_current_active_user)):
    """Get available platforms and their status"""
    return {
        "platforms": list(clients.keys()),
        "errors": initialization_errors
    }

@app.get("/products/{platform}", response_model=TaskResponse)
async def get_products(
    platform: str = Path(..., description="Platform name"),
    force_refresh: bool = Query(False, description="Force refresh from API"),
    current_user: User = Depends(get_current_active_user)
):
    """Get products from a platform (async)"""
    if platform not in clients:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Create a background task
    task_id = task_manager.submit_async_task(
        clients[platform].get_products,
        name=f"Get {platform} products",
        description=f"Fetching products from {platform}",
        force_refresh=force_refresh
    )
    
    return {"task_id": task_id, "status": "running", "progress": 0}

@app.post("/products/{platform}", response_model=TaskResponse)
async def update_products(
    platform: str,
    products: List[ProductUpdate],
    current_user: User = Depends(get_current_active_user)
):
    """Update products on a platform (async)"""
    if platform not in clients:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Convert to the format expected by the API client
    formatted_products = []
    for product in products:
        product_data = {"sku": product.sku, "data": {}}
        if product.price is not None:
            product_data["data"]["price"] = product.price
        if product.quantity is not None:
            product_data["data"]["quantity"] = product.quantity
        if product.status is not None:
            product_data["data"]["status"] = product.status
        formatted_products.append(product_data)
    
    # Create a background task
    task_id = task_manager.submit_async_task(
        clients[platform].update_products,
        name=f"Update {platform} products",
        description=f"Updating {len(formatted_products)} products on {platform}",
        products=formatted_products
    )
    
    return {"task_id": task_id, "status": "running", "progress": 0}

@app.post("/sync", response_model=TaskResponse)
async def sync_products(
    sync_request: SyncRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Synchronize products between platforms (async)"""
    # Validate platforms
    if sync_request.source_platform not in clients:
        raise HTTPException(status_code=404, detail=f"Source platform {sync_request.source_platform} not found")
    
    for platform in sync_request.target_platforms:
        if platform not in clients:
            raise HTTPException(status_code=404, detail=f"Target platform {platform} not found")
    
    # Create sync service
    source_service = clients[sync_request.source_platform]
    target_services = [clients[platform] for platform in sync_request.target_platforms]
    sync_service = UnifiedSyncService(source_service, target_services)
    
    # Start sync
    task_id = sync_service.start_sync(
        filter_skus=sync_request.filter_skus,
        batch_size=sync_request.batch_size if sync_request.batch_size is not None else 50,
        fields=sync_request.fields
    )
    
    return {"task_id": task_id, "status": "running", "progress": 0}

class BulkUpdateRequest(BaseModel):
    filter_skus: Optional[List[str]] = None

@app.post("/sync/bulk-update-lowest-stock", response_model=TaskResponse)
async def bulk_update_lowest_stock(
    request: BulkUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update all products with the lowest stock quantity across platforms (async)"""
    # Need at least two platforms to compare stock
    if len(clients) < 2:
        raise HTTPException(status_code=400, detail="Need at least two platforms to compare stock")
    
    # Create sync service with any platform as source
    source_platform = list(clients.keys())[0]
    target_platforms = [p for p in clients.keys() if p != source_platform]
    
    source_service = clients[source_platform]
    target_services = [clients[platform] for platform in target_platforms]
    sync_service = UnifiedSyncService(source_service, target_services)
    
    # Start bulk update
    task_id = sync_service.bulk_update_lowest_stock(
        filter_skus=request.filter_skus
    )
    
    return {"task_id": task_id, "status": "running", "progress": 0}

class SingleProductUpdateRequest(BaseModel):
    sku: str
    data: Dict[str, Any]
    target_platforms: Optional[List[str]] = None

@app.post("/sync/update-product", response_model=Dict[str, Any])
async def update_single_product(
    request: SingleProductUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update a single product across platforms"""
    # Validate target platforms
    if request.target_platforms:
        for platform in request.target_platforms:
            if platform not in clients:
                raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Create sync service with any platform as source
    source_platform = list(clients.keys())[0]
    target_platforms = [p for p in clients.keys() if p != source_platform]
    
    source_service = clients[source_platform]
    target_services = [clients[platform] for platform in target_platforms]
    sync_service = UnifiedSyncService(source_service, target_services)
    
    # Update product
    result = await sync_service.update_single_product(
        sku=request.sku,
        data=request.data,
        target_platforms=request.target_platforms
    )
    
    return result

class MultiProductUpdateRequest(BaseModel):
    products: List[Dict[str, Any]]
    target_platforms: Optional[List[str]] = None

@app.post("/sync/update-products", response_model=TaskResponse)
async def update_multiple_products(
    request: MultiProductUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update multiple products across platforms (async)"""
    # Validate target platforms
    if request.target_platforms:
        for platform in request.target_platforms:
            if platform not in clients:
                raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Create sync service with any platform as source
    source_platform = list(clients.keys())[0]
    target_platforms = [p for p in clients.keys() if p != source_platform]
    
    source_service = clients[source_platform]
    target_services = [clients[platform] for platform in target_platforms]
    sync_service = UnifiedSyncService(source_service, target_services)
    
    # Update products
    task_id = sync_service.update_multiple_products(
        products=request.products,
        target_platforms=request.target_platforms
    )
    
    return {"task_id": task_id, "status": "running", "progress": 0}

@app.get("/sync/history", response_model=List[Dict[str, Any]])
async def get_sync_history(
    limit: int = Query(10, description="Maximum number of history entries to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Get sync history"""
    # Create a sync service with any platform as source (we'll only use it to access history)
    if not clients:
        return []
    
    source_platform = list(clients.keys())[0]
    sync_service = UnifiedSyncService(clients[source_platform], [])
    
    # Get sync history
    history = await sync_service.get_sync_history(limit)
    return history

@app.get("/sync/history/{sync_id}", response_model=Dict[str, Any])
async def get_sync_details(
    sync_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed sync results"""
    # Create a sync service with any platform as source (we'll only use it to access history)
    if not clients:
        raise HTTPException(status_code=404, detail="No platforms available")
    
    source_platform = list(clients.keys())[0]
    sync_service = UnifiedSyncService(clients[source_platform], [])
    
    # Get sync details
    details = await sync_service.get_sync_details(sync_id)
    
    if isinstance(details, dict) and "error" in details:
        raise HTTPException(status_code=404, detail=details["error"])
    
    return details

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get task status"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return task

@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    limit: int = Query(10, description="Maximum number of tasks to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Get recent tasks"""
    tasks = task_manager.get_recent_tasks(limit)
    return tasks

@app.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a task"""
    success = task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {"status": "success", "message": f"Task {task_id} cancelled"}

# Run the server
if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)