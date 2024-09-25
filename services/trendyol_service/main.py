from enum import Enum
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Query

from services.trendyol_service.api.trendyol_api import TrendyolAPI
from services.trendyol_service.models import Product
from services.trendyol_service.database import DatabaseManager
from .schemas import ProductInDB, ProductPriceUpdate, ProductSchema, ProductStockUpdate, ProductUpdateSchema

router = APIRouter()
app = FastAPI()

trendyol_api = TrendyolAPI()
db_manager = DatabaseManager()

app.include_router(router)

class UpdateType(str, Enum):
    qty = "qty"
    price = "price"
    full = "full"

def get_update_schema(update_type: UpdateType = Query(default=UpdateType.full)):
    if update_type == UpdateType.qty:
        return ProductStockUpdate
    elif update_type == UpdateType.price:
        return ProductPriceUpdate
    else:
        return ProductUpdateSchema

@app.get("/products", response_model=str)
async def get_products(load_all: bool = False):
    try:
        await db_manager.init_db()
        products = await trendyol_api.get_products(load_all)
        db_products = []
        for product in products:
            db_product = await db_manager.create_product(product)
            db_products.append(db_product)
        return "Products loaded successfully"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/update", response_model=ProductInDB)
async def update_product_api(product: ProductUpdateSchema):
    try:
        result = await trendyol_api.update_product(product.model_dump(exclude_none=True, exclude_unset=True))
        updated_product = await db_manager.update_item(result["barcode"], result)
        return {"updated_product": updated_product, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/products/", response_model=ProductInDB)
async def create_product(product: ProductSchema):
    try:
        return await db_manager.create_product(product)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/products/{stock_code}", response_model=ProductInDB)
async def read_product(stock_code: str):
    product = await db_manager.get_item(Product, stock_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{stock_code}", response_model=Optional[ProductInDB])
async def update_product_by_id(
    stock_code: str,
    update_type: UpdateType = Query(default=UpdateType.full),
    product_update: Union[ProductStockUpdate, ProductPriceUpdate, ProductUpdateSchema] = Body(...)
):
    try:
        update_schema = get_update_schema(update_type)
        if not isinstance(product_update, update_schema):
            raise ValueError(f"Invalid update type. Expected {update_schema.__name__}, got {type(product_update).__name__}")

        updated_product = await db_manager.update_item(stock_code, product_update)

        if updated_product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductInDB.model_validate(updated_product)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from e


@app.delete("/products/{stock_code}", response_model=ProductInDB)
async def delete_product(stock_code: str):
    deleted_product = await db_manager.delete_product(Product, stock_code)
    if deleted_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return deleted_product
