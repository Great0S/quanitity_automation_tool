from contextlib import asynccontextmanager
from enum import Enum
from typing import List, Optional, Union
from fastapi import APIRouter, Body, FastAPI, HTTPException

from .api.pazarama_api import PazaramaAPI
from .models import PazaramaProduct
from .database import DatabaseManager
from .schemas import PazaramaProductCreateSchema, PazaramaProductResponseSchema, PazaramaProductSchema, PazaramaProductUpdateSchema, ResponseSchema, PazaramaProductBaseSchema


pazarama_api = PazaramaAPI()
db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.init_db()
    yield

router = APIRouter()
app = FastAPI(lifespan=lifespan)    
app.include_router(router)


@app.get("/products", response_model=List[PazaramaProductSchema])
async def get_products(stock_code: Optional[str] = None):
    try:
        db_products = await db_manager.get_product(stock_code)
        return db_products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/update", response_model=ResponseSchema)
async def update_product_by_bulk(
    product_update: List[PazaramaProductUpdateSchema] = Body(...)
):
    try:
        result = await pazarama_api.update_product(product_update.model_dump(exclude_none=True, exclude_unset=True))
        await db_manager.update_product(product_update=product_update)
        return "Products has been updated successfully " + str(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/products/", response_model=ResponseSchema)
async def create_product(product: PazaramaProductBaseSchema):
    try:
        await pazarama_api.create_product(product)
        return await db_manager.create_product(product)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/products/{stock_code}", response_model=ResponseSchema)
async def read_product_by_stock_code(stock_code: str):
    product = await db_manager.get_item(PazaramaProduct, stock_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{code}", response_model=PazaramaProductResponseSchema)
async def update_product_by_stock_code(
    code: str,
    product_update: PazaramaProductUpdateSchema = Body(...)
):
    try:
        # Update product on Pazarama API
        api_result = pazarama_api.update_product(product_update.model_dump(exclude_none=True, exclude_unset=True))
        
        if not api_result:
            raise HTTPException(status_code=400, detail="Failed to update product on Pazarama API")

        # Fetch the existing product from the database
        existing_product = await db_manager.get_product(code)
        if existing_product is None:
            raise HTTPException(status_code=404, detail="Product not found in database")

        # Update the existing product with new data
        updated_product = await db_manager.update_product(code, product_update)

        if not updated_product.code or updated_product.stockCount is None:
            raise ValueError("Both code and stockCount must be provided and valid")
        
        return PazaramaProductResponseSchema(
            status_code=200,
            message=f"Product with code {code} has been updated successfully",
            data=PazaramaProductSchema.model_validate(updated_product).model_dump()
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from e


@app.delete("/products/{code}", response_model=ResponseSchema)
async def delete_product_by_stock_code(code: str):
    deleted_product = await db_manager.delete_product(PazaramaProduct, code)
    if deleted_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return deleted_product


@app.post("/sync")
async def sync_products(load_all: bool = False):
    try:
        # Fetch products from Pazarama API
        pazarama_products = pazarama_api.get_products(load_all)
        
        # Sync products with local database
        for product in pazarama_products:
            existing_product = await db_manager.get_product(product["stockCode"])
            if existing_product:
                # Update existing product
                await db_manager.update_product(product["stockCode"], PazaramaProductBaseSchema(**product))
            else:
                # Create new product
                await db_manager.create_product(PazaramaProductCreateSchema(**product))
        
        return ResponseSchema(
            status_code=200,
            message=f"Successfully synced {len(pazarama_products)} products",
            data={"synced_count": len(pazarama_products)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during sync: {str(e)}") from e
