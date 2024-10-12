from typing import List
from fastapi import APIRouter, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.wordpress_service.api.wordpress_api import WordPressAPI
from services.wordpress_service.database import DatabaseManager
from services.wordpress_service.schemas import ProductCreate, ProductUpdate, UpdateStockSchema, ProductResponse



wordpress_api = WordPressAPI()
db_manager = DatabaseManager()

async def lifespan(app: FastAPI):
    await db_manager.init_db()
    yield

router = APIRouter()
app = FastAPI(lifespan=lifespan)    
app.include_router(router)

# CORS middleware (optional, configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/products/", response_model=ProductResponse)
async def create_product(product: ProductCreate):
    try:
        new_product = await db_manager.create_product(product)
        return new_product
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products/{product_id}", response_model=ProductResponse)
async def read_product(product_id: int):
    try:
        product = await db_manager.get_product(product_id)
        return product
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.put("/products/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(product_id: int, stock_data: UpdateStockSchema):
    try:
        updated_product = await db_manager.update_product_stock(product_id, stock_data)
        return updated_product
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/products/{product_id}", response_model=dict)
async def delete_product(product_id: int):
    try:
        await db_manager.delete_product(product_id)
        return {"message": f"Product with ID {product_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/products/", response_model=List[ProductResponse])
async def list_products():
    try:
        products = await db_manager.get_all_products()  # Assuming you have a method to get all products
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products/sync", response_model=dict)
async def sync_products(load_all: bool = False):
    try:
        # Fetch products from WordPress API
        wordpress_products = wordpress_api.get_wordpress_products(load_all)  # Assuming you have a method to get all products
        
        synced_count = 0
        for item in wordpress_products:
            existing_product = await db_manager.get_product(item['sku'])  # Assuming SKU is the unique identifier
            
            if existing_product:
                # Update existing product
                await db_manager.update_product(existing_product.id, ProductUpdate(**item))
            else:
                # Create new product
                await db_manager.create_product(ProductCreate(**item))
            
            synced_count += 1
        
        return {
            "status_code": 200,
            "message": f"Successfully synced {synced_count} products",
            "synced_count": synced_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during sync: {str(e)}")
