from box import Box
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from typing import List, Union, Optional
from enum import Enum

from .schemas import HepsiburadaProductSchema
from .models import HepsiburadaProduct
from .database import DatabaseManager
from .api.hepsiburada_api import HepsiburadaAPI
from shared.logging import logger

app = FastAPI()
db_manager = DatabaseManager()
hepsiburada_api = HepsiburadaAPI()


@app.on_event("startup")
async def startup():
    await db_manager.init_db()

@app.post("/products/", response_model=HepsiburadaProductSchema)
async def create_product(product: HepsiburadaProductSchema):
    try:
        # First, create the product on Hepsiburada
        api_response = await hepsiburada_api.create_product(product)
        if not api_response:
            raise HTTPException(status_code=400, detail="Failed to create product on Hepsiburada")
        
        # Then, create the product in our database
        db_product = await db_manager.create_item(HepsiburadaProduct, product)
        if db_product is None:
            raise HTTPException(status_code=400, detail="Failed to create product in database")
        return db_product
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{merchantSku}", response_model=HepsiburadaProductSchema)
async def read_product(merchantSku: str):
    db_product = await db_manager.get_product(merchantSku)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.put("/products/{merchantSku}", response_model=HepsiburadaProductSchema)
async def update_product(
    merchantSku: str,
    product_update: HepsiburadaProductSchema = Body(...)
):
    try:
        
        # First, update the product on Hepsiburada
        api_response = hepsiburada_api.update_listing(product_data=product_update.model_dump(exclude_unset=True))
        if not api_response:
            raise HTTPException(status_code=400, detail="Failed to update product on Hepsiburada")
        
        # Then, update the product in our database
        db_product = await db_manager.update_product(merchantSku, product_update)
        if db_product is None:
            raise HTTPException(status_code=404, detail="Product not found in database")
        return db_product
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/products/{merchantSku}", response_model=bool)
async def delete_product(merchantSku: str):
    try:
        # First, delete the product on Hepsiburada
        api_response = await hepsiburada_api.delete_product(merchantSku)
        if not api_response:
            raise HTTPException(status_code=400, detail="Failed to delete product on Hepsiburada")
        
        # Then, delete the product from our database
        success = await db_manager.delete_item(HepsiburadaProduct, merchantSku)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found in database")
        return True
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/", response_model=List[HepsiburadaProductSchema])
async def read_products(merchantSku: Optional[str] = None):
    products = await db_manager.get_product(merchantSku)   
    return products

@app.post("/sync-products/")
async def sync_products(load_all: bool = False):
    try:
        # Get products from Hepsiburada API
        api_products = await hepsiburada_api.get_listings(load_all)
        
        # Sync products with our database
        for api_product in api_products:
            product = Box(api_product)
            db_product = await db_manager.get_product(product.merchantSku)
            if db_product:
                # Update existing product
                await db_manager.update_product(product.merchantSku, product)
            else:
                # Create new product
                await db_manager.create_product(product)
        
        return {"message": "Products synchronized successfully"}
    except Exception as e:
        logger.error(f"Error syncing products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

