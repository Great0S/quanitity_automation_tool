from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from services.trendyol_service.models import Product
from shared.database import create_db_product
from .api.trendyol_api import TrendyolAPI
from .scheme import ProductDeleteScheme, ProductScheme, ProductUpdate
from shared import delete_products, get_db, get_item, update_item


router = APIRouter()
app = FastAPI()
trendyol_api = TrendyolAPI()

app.include_router(router)


@app.get("/products")
async def get_products(load_all: bool = False, db: Session = Depends(get_db)):
    try:
        products = trendyol_api.get_products(load_all)
        for product in products:
            create_db_product(product['data'])
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update")
async def update_product(product: ProductUpdate):
    try:
        result = trendyol_api.update_product(product.dict())
        return {"status": "updated", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/products/")
def create_product(product: ProductScheme, db: Session = Depends(get_db)):
    try:
        db_product = create_db_product(db, product)
        return "Done"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/products/{product_id}")
def read_product(product_id: str, db: Session = Depends(get_db)):
    return get_item(db, Product, product_id)


@app.put("/products/{product_id}")
def update_product_by_id(product_id: str, product: ProductUpdate, db: Session = Depends(get_db)):
    return update_item(db, ProductScheme, product_id, **product.dict())


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    return delete_products(Product, product_id)
