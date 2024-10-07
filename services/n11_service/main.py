from enum import Enum
from typing import List
from fastapi import APIRouter, Body, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from services.n11_service.api.n11_rest_api import N11RestAPI
from services.n11_service.models import N11Product
from services.n11_service.database import DatabaseManager
from services.n11_service.schemas import (
    N11ProductSchema,
    N11ProductCreateSchema,
    N11ProductUpdateSchema,
    N11ProductResponseSchema,
    N11ProductListResponseSchema,
)

from shared.logging import logger

router = APIRouter()
n11_api = N11RestAPI()
db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router)

class UpdateType(str, Enum):
    qty = "qty"
    price = "price"
    full = "full"

def get_update_schema(update_type: UpdateType = Query(default=UpdateType.full)):
    return N11ProductUpdateSchema

@app.get("/products", response_model=N11ProductListResponseSchema)
async def get_products(limit: int = 100):
    try:
        db_products = await db_manager.get_n11_products(limit=limit)
        return N11ProductListResponseSchema(
            status_code=200,
            message="Products retrieved successfully",
            data=db_products
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/products", response_model=N11ProductResponseSchema)
async def create_product(product: N11ProductCreateSchema):
    try:
        api_product = await n11_api.create_product(product)
        created_product = await db_manager.create_n11_product(api_product)
        return N11ProductResponseSchema(
            status_code=201,
            message="Product created successfully",
            data=N11ProductSchema.model_validate(created_product)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/products/{stock_code}", response_model=N11ProductResponseSchema)
async def read_product_by_stock_code(stock_code: str):
    db_product = await db_manager.get_n11_product(stock_code)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return N11ProductResponseSchema(
        status_code=200,
        message="Product retrieved successfully",
        data=N11ProductSchema.model_validate(db_product)
    )

@app.put("/products/{stock_code}", response_model=N11ProductResponseSchema)
async def update_product_by_stock_code(
    stock_code: str,
    update_type: UpdateType = Query(default=UpdateType.full),
    product_update: N11ProductUpdateSchema = Body(...)
):
    try:
        update_schema = get_update_schema(update_type)
        if not isinstance(product_update, update_schema):
            raise ValueError(f"Invalid update type. Expected {update_schema.__name__}, got {type(product_update).__name__}")

        api_updated_product = n11_api.update_product(product_update)
        if api_updated_product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        updated_product = await db_manager.update_n11_product(stock_code, product_update)

        return N11ProductResponseSchema(
            status_code=200,
            message="Product updated successfully",
            data=N11ProductSchema.model_validate(updated_product)
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from e

@app.delete("/products/{stock_code}", response_model=N11ProductResponseSchema)
async def delete_product_by_stock_code(stock_code: str):
    api_deleted = await n11_api.delete_product(stock_code)
    if not api_deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    deleted_product = await db_manager.delete_n11_product(stock_code)
    return N11ProductResponseSchema(
        status_code=200,
        message="Product deleted successfully",
        data=N11ProductSchema.model_validate(deleted_product)
    )

@app.post("/products/sync", response_model=N11ProductListResponseSchema)
async def sync_products(skip: int = 1, limit: int = 50, raw_data: bool = False):
    try:
        api_products = await n11_api.get_products(page=skip, page_size=limit, raw_data=raw_data)
        db_products = []
        for product in api_products:
            db_product = await db_manager.create_n11_product(product)
            db_products.append(db_product)
        return N11ProductListResponseSchema(
            status_code=200,
            message="Products synchronized successfully",
            data=[N11ProductSchema.model_validate(p) for p in db_products]
        )
    except Exception as e:
        logger.error(f"Error syncing products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": [{"code": str(exc.status_code), "message": exc.detail}]}
    )
