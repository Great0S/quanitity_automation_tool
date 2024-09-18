from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api.trendyol_api import TrendyolAPI

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