from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Generic, TypeVar

T = TypeVar('T')

class N11ProductAttributeSchema(BaseModel):
    attributeId: int
    attributeName: str
    attributeValue: str

    class Config:
        from_attributes = True

class N11ProductSchema(BaseModel):
    n11ProductId: int
    sellerId: int
    sellerNickname: str
    stockCode: str
    title: str
    description: str | None = None
    categoryId: int
    productMainId: str | None = None
    status: str
    saleStatus: str
    preparingDay: int
    shipmentTemplate: str | None = None
    maxPurchaseQuantity: int | None = None
    catalogId: int
    barcode: str | None = None
    groupId: int
    currencyType: str
    salePrice: float
    listPrice: float
    quantity: int

    attributes: Optional[List[N11ProductAttributeSchema]] = None

    class Config:
        from_attributes = True

class N11ProductCreateSchema(BaseModel):
    n11ProductId: int
    sellerId: int
    sellerNickname: str
    stockCode: str
    title: str
    description: str | None = None
    categoryId: int
    productMainId: str | None = None
    status: str
    saleStatus: str
    preparingDay: int
    shipmentTemplate: str | None = None
    maxPurchaseQuantity: int | None = None
    catalogId: int
    barcode: str | None = None
    groupId: int
    currencyType: str
    salePrice: float
    listPrice: float
    quantity: int
    attributes: List[N11ProductAttributeSchema]

class N11ProductUpdateSchema(BaseModel):
    stockCode: Optional[str] = None
    quantity: Optional[int] = None

class ResponseSchema(BaseModel, Generic[T]):
    status_code: int
    message: str
    data: Optional[T] = None
class N11ProductResponseSchema(ResponseSchema[N11ProductSchema]):
    pass

class N11ProductListResponseSchema(ResponseSchema[List[N11ProductSchema]]):
    pass
