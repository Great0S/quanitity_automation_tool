# Product Models
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class ProductAttributeSchema(BaseModel):
    name: str
    value: str

class ProductImageSchema(BaseModel):
    url: HttpUrl

class DeliveryTypeSchema(BaseModel):
    type: str

class PazaramaProductBaseSchema(BaseModel):
    name: str
    displayName: str
    description: Optional[str] = None
    brandName: str
    code: str
    groupCode: str = ""
    stockCount: int
    stockCode: str
    priorityRank: int = 0
    listPrice: float
    salePrice: float
    vatRate: int
    categoryName: str
    categoryId: str
    state: int
    status: Optional[str] = None
    waitingApproveExp: Optional[str] = None

class PazaramaProductCreateSchema(PazaramaProductBaseSchema):
    attributes: Optional[List[ProductAttributeSchema]] = None
    images: Optional[List[ProductImageSchema]] = None
    deliveryTypes: Optional[List[DeliveryTypeSchema]] = None

class PazaramaProductSchema(PazaramaProductBaseSchema):
    id: int
    attributes: List[ProductAttributeSchema] = []
    images: List[ProductImageSchema] = []
    deliveryTypes: List[DeliveryTypeSchema] = []

    class Config:
        from_attributes = True

class PazaramaProductUpdateSchema(BaseModel):
    code: Optional[str] = None
    stockCount: Optional[int] = None

class ResponseSchema(BaseModel):
    status_code: int
    message: str
    data: Optional[dict] = None

class PazaramaProductResponseSchema(ResponseSchema):
    data: Optional[PazaramaProductSchema] = None

class PazaramaProductListResponseSchema(ResponseSchema):
    data: Optional[List[PazaramaProductSchema]] = None

