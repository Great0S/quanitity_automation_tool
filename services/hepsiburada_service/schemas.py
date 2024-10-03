from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from decimal import Decimal

class ProductImageSchema(BaseModel):
    imageUrl: HttpUrl
    order: int = 0

class ProductAttributeSchema(BaseModel):
    name: str
    value: str
    mandatory: bool = False

class HepsiburadaProductSchema(BaseModel):
    merchantSku: str
    barcode: str
    hbSku: str
    variantGroupId: Optional[str] = ""
    productName: str
    brand: str
    images: List[ProductImageSchema]
    categoryId: int
    categoryName: str
    tax: Decimal = Field(..., ge=0, le=100)
    price: Optional[Decimal] = Field(None, ge=0)
    description: str
    status: str
    baseAttributes: List[ProductAttributeSchema]
    stock: int = 0

    class Config:
        from_attributes = True

class HepsiburadaProductBasicSchema(BaseModel):
    merchantSku: str
    hbSku: str
    productName: str
    brand: str
    price: Optional[Decimal] = Field(None, ge=0)
    status: str
    stock: int = 0

    class Config:
        from_attributes = True


