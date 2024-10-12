# schemas/product.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ProductBase(BaseModel):
    name: str
    slug: str
    permalink: str
    date_created: str  # Consider using datetime for actual date objects
    date_modified: str
    type: str
    status: str
    featured: bool
    catalog_visibility: str
    description: str
    short_description: str
    sku: str
    price: float
    regular_price: float
    sale_price: Optional[float]
    on_sale: bool
    purchasable: bool
    stock_quantity: int
    manage_stock: bool
    stock_status: str
    categories: List[Dict[str, Any]]  # List of category dictionaries
    images: List[Dict[str, Any]]  # List of image dictionaries
    attributes: List[Dict[str, Any]]  # List of attribute dictionaries

class ProductCreate(ProductBase):
    pass  # You can add additional validation or fields if needed

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    slug: Optional[str] = None
    permalink: Optional[str] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    featured: Optional[bool] = None
    catalog_visibility: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    on_sale: Optional[bool] = None
    purchasable: Optional[bool] = None
    stock_quantity: Optional[int] = None
    manage_stock: Optional[bool] = None
    stock_status: Optional[str] = None
    categories: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[Dict[str, Any]]] = None
    attributes: Optional[List[Dict[str, Any]]] = None

    
class ProductResponse(ProductBase):
    id: int  # Include the ID for the response schema

    class Config:
        from_attributes = True  # Enable ORM mode to read data from SQLAlchemy models

class UpdateStockSchema(BaseModel):
    stock_quantity: Optional[int] = Field(None, description="The quantity of the product in stock.")
    stock_status: Optional[str] = Field(None, description="The status of the stock (e.g., 'instock', 'outofstock').")
