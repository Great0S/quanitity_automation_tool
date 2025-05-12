"""
Main API entry point
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.auth import get_current_user, create_access_token
from api.routes.products import router as products_router
from api.routes.tasks import router as tasks_router
from api.routes.auth import router as auth_router

app = FastAPI(title="Quantity Automation Tool API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

@app.get("/")
async def root():
    """
    Root endpoint
    
    Returns:
        Welcome message
    """
    return {"message": "Welcome to Quantity Automation Tool API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Health status
    """
    return {"status": "healthy"}