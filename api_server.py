"""
FastAPI server for the Quantity Automation Tool
"""

import os
import asyncio
import uvicorn
from typing import Dict, List, Any, Optional
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
from api.pttavm_client import PTTAVMClient
from api.pazarama_client import PazaramaClient
from api.hepsiburada_client import HepsiburadaClient
from api.trendyol_client import TrendyolClient
from api.n11_client import N11Client
from services.unified_product_service import UnifiedProductService
from services.unified_sync_service import UnifiedSyncService
from services.export_service import ExportService
from utils.helpers import retry_async, CircuitBreaker
from utils.background_tasks import get_task_manager, TaskStatus
from utils.cache import get_cache
from data.database import get_db
from data.repositories import get_product_repository

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Quantity Automation API",
    description="API for managing product inventory across multiple e-commerce platforms",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours

# Pydantic models for request/response
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class ProductData(BaseModel):
    sku: str
    data: Dict[str, Any]

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
    fields: Optional[List[str]] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None

# In-memory user database (replace with real DB in production)
users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": "admin",  # In production, use proper password hashing
        "disabled": False,
    }
}

# Global variables
clients = {}
initialization_errors = {}
task_manager = get_task_manager()
product_repo = get_product_repository()

# Authentication functions
def verify_password(plain_password, hashed_password):
    # In production, use proper password verification
    return plain_password == hashed_password

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    if token_data.username is None:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Initialize API clients
async def initialize_clients():
    global clients, initialization_errors
    
    try:
        # Initialize clients dictionary
        clients = {}
        initialization_errors = {}

        # N11
        if all([os.getenv("N11_APP_KEY"), os.getenv("N11_APP_SECRET")]):
            try:
                n11_client = N11Client()
                
                # Use circuit breaker
                circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
                
                try:
                    await n11_client.authenticate()
                except Exception as e:
                    logger.error(f"Error authenticating N11 client: {str(e)}", exc_info=True)
                    raise AuthenticationError(f"N11 authentication failed: {str(e)}")
                
                clients["N11"] = UnifiedProductService(n11_client, "N11")
                logger.info("N11 client initialized successfully")
            except AuthenticationError as e:
                error_msg = f"N11 authentication failed: {str(e)}"
                logger.error(error_msg)
                initialization_errors["N11"] = error_msg
            except NetworkError as e:
                error_msg = f"N11 network error: {str(e)}"
                logger.error(error_msg)
                initialization_errors["N11"] = error_msg
            except RateLimitError as e:
                error_msg = f"N11 rate limit exceeded: {str(e)}"
                logger.error(error_msg)
                initialization_errors["N11"] = error_msg
            except Exception as e:
                error_msg = f"Failed to initialize N11 client: {str(e)}"
                logger.error(error_msg)
                initialization_errors["N11"] = error_msg

        # Trendyol
        if all([os.getenv("TRENDYOL_API_KEY"), os.getenv("TRENDYOL_API_SECRET")]):
            try:
                trendyol_client = TrendyolClient()
                
                # Use circuit breaker
                circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
                
                try:
                    await trendyol_client.authenticate()
                except Exception as e:
                    logger.error(f"Error authenticating Trendyol client: {str(e)}", exc_info=True)
                    raise AuthenticationError(f"Trendyol authentication failed: {str(e)}")
                
                clients["Trendyol"] = UnifiedProductService(trendyol_client, "Trendyol")
                logger.info("Trendyol client initialized successfully")
            except AuthenticationError as e:
                error_msg = f"Trendyol authentication failed: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Trendyol"] = error_msg
            except NetworkError as e:
                error_msg = f"Trendyol network error: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Trendyol"] = error_msg
            except RateLimitError as e:
                error_msg = f"Trendyol rate limit exceeded: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Trendyol"] = error_msg
            except Exception as e:
                error_msg = f"Failed to initialize Trendyol client: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Trendyol"] = error_msg

        # Hepsiburada
        if all([os.getenv("HEPSIBURADA_USERNAME"), os.getenv("HEPSIBURADA_PASSWORD")]):
            try:
                # Always use the real client since we removed the mock client
                logger.info("Initializing Hepsiburada client")
                hepsiburada_client = HepsiburadaClient()
                
                # Use circuit breaker
                circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
                
                try:
                    await hepsiburada_client.authenticate()
                except Exception as e:
                    logger.error(f"Error authenticating Hepsiburada client: {str(e)}", exc_info=True)
                    raise AuthenticationError(f"Hepsiburada authentication failed: {str(e)}")
                
                clients["Hepsiburada"] = UnifiedProductService(hepsiburada_client, "Hepsiburada")
                logger.info("Hepsiburada client initialized successfully")
            except AuthenticationError as e:
                error_msg = f"Hepsiburada authentication failed: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Hepsiburada"] = error_msg
            except NetworkError as e:
                error_msg = f"Hepsiburada network error: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Hepsiburada"] = error_msg
            except RateLimitError as e:
                error_msg = f"Hepsiburada rate limit exceeded: {str(e)}"
                logger.error(error_msg)
                initialization_errors["Hepsiburada"] = error_msg
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
        batch_size=sync_request.batch_size,
        fields=sync_request.fields
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
    history = sync_service.get_sync_history(limit)
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
    details = sync_service.get_sync_details(sync_id)
    
    if "error" in details:
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

@app.on_event("startup")
async def startup_event():
    """Initialize API clients on startup"""
    await initialize_clients()

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)