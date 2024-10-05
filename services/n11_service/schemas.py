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
    n11ProductId: Optional[int] = None
    sellerId: Optional[int] = None
    sellerNickname: Optional[str] = None
    stockCode: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    categoryId: Optional[int] = None
    productMainId: Optional[str] = None
    status: Optional[str] = None
    saleStatus: Optional[str] = None
    preparingDay: Optional[int] = None
    shipmentTemplate: Optional[str] = None
    maxPurchaseQuantity: Optional[int] = None
    catalogId: Optional[int] = None
    barcode: Optional[str] = None
    groupId: Optional[int] = None
    currencyType: Optional[str] = None
    salePrice: Optional[float] = None
    listPrice: Optional[float] = None
    quantity: Optional[int] = None
    attributes: Optional[List[N11ProductAttributeSchema]] = None

class ResponseSchema(BaseModel, Generic[T]):
    status_code: int
    message: str
    data: Optional[T] = None
class N11ProductResponseSchema(ResponseSchema[N11ProductSchema]):
    pass

class N11ProductListResponseSchema(ResponseSchema[List[N11ProductSchema]]):
    pass
