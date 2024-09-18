from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from api.trendyol_api import TrendyolAPI
from shared.database import get_db

app = FastAPI()
trendyol_api = TrendyolAPI()

class ProductUpdate(BaseModel):
    sku: str
    quantity: int
    price: float

@app.get("/products")
async def get_products(load_all: bool = False):
    try:
        products = trendyol_api.get_products(load_all)
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
def create_product(product: ProductCreate, db = Depends(get_db)):
    return create_item(db, Product, **product.dict())

@app.get("/products/{product_id}")
def read_product(product_id: int, db = Depends(get_db)):
    return get_item(db, Product, product_id)

@app.put("/products/{product_id}")
    return update_item(db, Product, product_id, **product.dict())

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db = Depends(get_db)):
    return delete_item(db, Product, product_id)