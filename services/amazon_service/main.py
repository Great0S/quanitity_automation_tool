from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from services.amazon_service.api.amazon_seller_api import AmazonListingManager
from services.amazon_service.database import DatabaseManager
from services.amazon_service.schemas import (
    GetListingsItemRequest, GetListingsItemResponse,
    ListingsItemPutRequest, ListingsItemPutResponse,
    ListingsPatchRequest, ListingsPatchResponse,
    DeleteListingsItemResponse, ErrorList
)
from services.amazon_service.models import ProductType
from shared.logging import logger

db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.init_db()
    yield
    # Shutdown
    # Add any cleanup code here if needed
    # No need to close the database connection explicitly
    pass

app = FastAPI(lifespan=lifespan)
router = APIRouter()
app.include_router(router)

@app.get("/listings/2021-08-01/items/{sku}", response_model=GetListingsItemResponse)
async def get_listings_item(
    sku: str,
    marketplaceIds: List[str] = Query(...),
    issueLocale: str = Query(None),
    includedData: List[str] = Query(None),
    db_manager: DatabaseManager = Depends(DatabaseManager)
):
    try:
        request = GetListingsItemRequest(
            marketplaceIds=marketplaceIds,
            issueLocale=issueLocale,
            includedData=includedData
        )
        async with db_manager.get_db() as session:
            item = await db_manager.get_product(sku, request)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Product with SKU {sku} not found")
        return item
    except Exception as e:
        logger.error(f"Error getting listings item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/listings/2021-08-01/items/{sku}", response_model=ListingsItemPutResponse)
async def put_listings_item(
    sku: str,
    item: ListingsItemPutRequest,
    marketplaceIds: List[str] = Query(...),
    issueLocale: str = Query(None),
    db_manager: DatabaseManager = Depends(DatabaseManager)
):
    try:
        async with db_manager.get_db() as session:
            product = await db_manager.create_product(item)
        return ListingsItemPutResponse(
            sku=product.sku,
            status="ACCEPTED",
            submissionId=f"submission_{product.id}"
        )
    except Exception as e:
        logger.error(f"Error creating listings item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/listings/2021-08-01/items/{sku}", response_model=ListingsPatchResponse)
async def patch_listings_item(
    sku: str,
    patch_request: ListingsPatchRequest,
    marketplaceIds: List[str] = Query(...),
    issueLocale: str = Query(None),
    db_manager: DatabaseManager = Depends(DatabaseManager)
):
    try:
        async with db_manager.get_db() as session:
            patch_response = await db_manager.update_product(sku, patch_request)
        return ListingsPatchResponse(
            sku=sku,
            status=patch_response.status,
            submissionId=patch_response.submission_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error patching listings item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/listings/2021-08-01/items/{sku}", response_model=DeleteListingsItemResponse)
async def delete_listings_item(
    sku: str,
    marketplaceIds: List[str] = Query(...),
    issueLocale: str = Query(None),
    db_manager: DatabaseManager = Depends(DatabaseManager)
):
    try:
        async with db_manager.get_db() as session:
            delete_response = await db_manager.delete_product(sku)
        return DeleteListingsItemResponse(
            sku=sku,
            status=delete_response.status,
            submissionId=delete_response.submission_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error deleting listings item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings/2021-08-01/items", response_model=List[GetListingsItemResponse])
async def get_listings_items(
    marketplaceIds: Optional[List[str]] = Query(None),
    sellerId: Optional[str] = Query(None),
    issueLocale: Optional[str] = Query(None),
    includedData: Optional[List[str]] = Query(None),
    sku: Optional[str] = Query(None),
    load_all: bool = Query(False, description="If True, load all products data"),
    db_manager: DatabaseManager = Depends(DatabaseManager),
    amazon_api: AmazonListingManager = Depends(AmazonListingManager)
):
    try:
        # First, try to get the listings from the database
        async with db_manager.get_db() as session:
            db_listings = await db_manager.get_products(sku=sku)
        
        if db_listings:
            # If listings are found in the database, return them
            return [
                GetListingsItemResponse(**listing) for listing in db_listings
            ]
        else:
            # If no listings found in the database, fetch from SP API
            sp_api_listings = await amazon_api.get_listings(load_all=load_all)
            
            if sp_api_listings:
                # Filter listings if skus were provided
                if sku:
                    sp_api_listings = [listing for listing in sp_api_listings if listing['sku'] in sku]
                
                # Save the retrieved listings to the database
                async with db_manager.get_db() as session:
                    await db_manager.create_product(sp_api_listings)
                
                # Return the listings from SP API
                return [
                    GetListingsItemResponse(
                        sku=listing['sku'],
                        listing_id=listing['listing-id'],
                        quantity=int(listing['quantity']),
                        asin=listing['asin'],
                        attributes=listing.get('attributes', {}),
                        images=listing.get('images', []),
                        productTypes=ProductType(listing.get('productTypes')) if listing.get('productTypes') else "OTHER",  # Convert to ProductType enum or None if not present
                        browseClassification=listing.get('summaries', {}).get('browseClassification', None),
                        color=listing.get('summaries', {}).get('color', None),
                        size=listing.get('summaries', {}).get('size', None),                           
                    ) for listing in sp_api_listings
                ]
            else:
                # If no listings found in SP API, return an empty list
                return []
    except ValueError as ve:
        logger.error(f"Error retrieving listings items: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(ve)}")
    except Exception as e:
        logger.error(f"Error retrieving listings items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": [{"code": str(exc.status_code), "message": exc.detail}]}
    )