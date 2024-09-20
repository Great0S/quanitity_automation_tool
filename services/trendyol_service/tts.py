from fastapi import APIRouter, FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

from .models import Product
from .schemas import ProductScheme, ProductUpdate, ProductInDB
from .api.trendyol_api import TrendyolAPI
from .database import get_db, DatabaseService

router = APIRouter()
app = FastAPI()

def get_trendyol_api():
    return TrendyolAPI()

def get_db_service(db: Session = Depends(get_db)):
    return DatabaseService(db)

app.include_router(router)

@app.get("/products", response_model=List[ProductInDB])
async def get_products(
    load_all: bool = False,
    trendyol_api: TrendyolAPI = Depends(get_trendyol_api),
    db_service: DatabaseService = Depends(get_db_service)
):
    try:
        products = trendyol_api.get_products(load_all)
        db_products = []
        for product in products:
            db_products.append(db_product)
        return db_products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/update", response_model=ProductInDB)
async def update_product(
    product: ProductUpdate,
    trendyol_api: TrendyolAPI = Depends(get_trendyol_api),
    db_service: DatabaseService = Depends(get_db_service)
):
    try:
        result = trendyol_api.update_product(product.dict())
        updated_product = db_service.update_product(result["barcode"], result)
        return updated_product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/products/", response_model=ProductInDB)
def create_product(
    product: ProductScheme,
    db_service: DatabaseService = Depends(get_db_service)
):
    try:
        return db_service.create_product(product.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/products/{product_id}", response_model=ProductInDB)
    product = db_service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductInDB)
def update_product_by_id(
    product_id: str,
    product: ProductUpdate,
    db_service: DatabaseService = Depends(get_db_service)
):

    if updated_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product

@app.delete("/products/{product_id}", response_model=ProductInDB)
    deleted_product = db_service.delete_product(product_id)
    if deleted_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return deleted_product
