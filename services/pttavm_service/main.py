from fastapi import APIRouter, Body, FastAPI, HTTPException

from services.pttavm_service.api.pttavm_api import PTTAVMAPI
from services.pttavm_service.schemas import PTTAVMProductSchema, PTTAVMProductUpdateSchema, PTTAVMProductResponseSchema
from services.pttavm_service.database import DatabaseManager

pttavm_api = PTTAVMAPI()
db_manager = DatabaseManager()

async def lifespan(app: FastAPI):
    await db_manager.init_db()
    yield

router = APIRouter()
app = FastAPI(lifespan=lifespan)    
app.include_router(router)


@app.post("/products/", response_model=PTTAVMProductResponseSchema)
async def create_product(product: PTTAVMProductSchema):
    
        try:
            new_product = await db_manager.create_product(product)
            return PTTAVMProductResponseSchema(
                status_code=201,
                message="Product created successfully",
                data=new_product
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.put("/products/{barkod}", response_model=PTTAVMProductResponseSchema)
async def update_product(barkod: str, product_update: PTTAVMProductUpdateSchema = Body(...)):
    try:
        updated_product = await db_manager.update_product(barkod, product_update)
        if updated_product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return PTTAVMProductResponseSchema(
            status_code=200,
            message="Product updated successfully",
            data=updated_product
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products/{barkod}", response_model=PTTAVMProductResponseSchema)
async def read_product(barkod: str):
    try:
        product = await db_manager.get_product(barkod)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return PTTAVMProductResponseSchema(
            status_code=200,
            message="Product retrieved successfully",
            data=product
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/products/{barkod}", response_model=PTTAVMProductResponseSchema)
async def delete_product(barkod: str):
    try:
        deleted = await db_manager.delete_product(barkod)
        if not deleted:
            raise HTTPException(status_code=404, detail="Product not found")
        return PTTAVMProductResponseSchema(
            status_code=200,
            message="Product deleted successfully",
            data=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync", response_model=PTTAVMProductResponseSchema)
async def sync_products(load_all: bool = False):
    try:
        # Fetch products from PTTAVM API
        pttavm_products = pttavm_api.getpttavm_procuctskdata(everyproduct=load_all)
        
        # Sync products with local database
        for product in pttavm_products:
            existing_product = await db_manager.get_product(product['a:Barkod'])
            for attr_key, attr_val in product.items():
                if isinstance(product[attr_key], dict):
                    product[attr_key] = 'N/A'

            if existing_product:
                # Update existing product
                await db_manager.update_product(product['a:Barkod'], PTTAVMProductUpdateSchema(**product))
            else:
                # Create new product
                await db_manager.create_product(PTTAVMProductSchema(**product))
        
        return PTTAVMProductResponseSchema(
            status_code=200,
            message=f"Successfully synced {len(pttavm_products)} products",
            data={"synced_count": len(pttavm_products)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during sync: {str(e)}") from e

