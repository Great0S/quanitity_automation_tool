from fastapi import APIRouter, FastAPI, HTTPException

from services.trendyol_service.models import Product
from shared import delete_products, get_item, update_item
from shared.database import create_db_product
from .api.trendyol_api import TrendyolAPI
from .scheme import ProductScheme, ProductUpdate


router = APIRouter()
app = FastAPI()
trendyol_api = TrendyolAPI()

app.include_router(router)


@app.get("/products")
async def get_products(load_all: bool = False):
    try:
        products = trendyol_api.get_products(load_all)
        for product in products:
            create_db_product(product["data"])
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/update")
async def update_product(product: ProductUpdate):
    try:
        result = trendyol_api.update_product(product.model_dump())
        return {"status": "updated", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/products/")
def create_product(product: ProductScheme):
    try:
        db_product = create_db_product(product)
        return "Done"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/products/{product_id}")
def read_product(product_id: str):
    return get_item(Product, product_id)


@app.put("/products/{product_id}")
def update_product_by_id(product_id: str,
                         product: ProductUpdate):
    return update_item(product_id, product.model_dump())


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    return delete_products(Product, product_id)
