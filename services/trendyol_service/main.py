from typing import Dict, List
from fastapi import APIRouter, FastAPI, HTTPException, Query

from services.trendyol_service.api.trendyol_api import TrendyolAPI
from services.trendyol_service.models import Product
from shared.database import DatabaseManager
from .schemas import ProductInDB, ProductPriceUpdate, ProductSchema, ProductStockUpdate, ProductUpdateSchema

router = APIRouter()
app = FastAPI()

trendyol_api = TrendyolAPI()
db_manager = DatabaseManager()

app.include_router(router)


@app.get("/products", response_model=List[ProductInDB])
async def get_products(load_all: bool = False):
    try:
        await db_manager.init_db()
        products = await trendyol_api.get_products(load_all)
        db_products = []
        for product in products:
            db_product = await db_manager.create_product(product)
            db_products.append(db_product)
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/update", response_model=ProductInDB)
async def update_product_api(product: ProductUpdateSchema):
    try:
        result = await trendyol_api.update_product(product.model_dump())
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


@app.get("/products/{product_id}", response_model=ProductInDB)
async def read_product(product_id: str):
    product = await db_manager.get_item(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{product_id}", response_model=Dict[str, int])
async def update_product_by_id(
    product_id: str,
    product_update_type: List[str] = Query(
        default=["qty", "price", "full"],  # Default list of choices
        description="Choose the update type:",
        title="My Param"
    )
):
    try:
        product_update = ProductUpdateSchema()
        if "qty" in product_update_type:
            product_update = ProductStockUpdate()
        elif "price" in product_update_type:
            product_update = ProductPriceUpdate()

        updated_product = await db_manager.update_item(product_id, product_update.model_dump(exclude_none=True, exclude_unset=True))

        if updated_product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        return updated_product
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from e


@app.delete("/products/{product_id}", response_model=ProductInDB)
async def delete_product(product_id: str):
    deleted_product = await db_manager.delete_product(Product, product_id)
    if deleted_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return deleted_product
