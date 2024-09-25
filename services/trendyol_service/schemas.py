# Product Models
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class ImageSchema(BaseModel):
    url: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(url=value)
        return value


class AttributeSchema(BaseModel):
    attributeId: Optional[int] 
    attributeValue: Optional[Union[int, str]] 
    attributeName: Optional[str] 

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    barcode: Optional[str]
    title: Optional[str]
    productMainId: Optional[str]
    brandId: Optional[int]
    pimCategoryId: Optional[int]
    categoryName: Optional[str]
    quantity: Optional[int]
    stockCode: Optional[str]
    dimensionalWeight: Optional[float]
    description: Optional[str]
    brand: Optional[str]
    listPrice: Optional[float]
    salePrice: Optional[float]
    vatRate: Optional[float]


class ProductInDB(ProductBase):
    id: int
    createDateTime: Optional[datetime]
    lastUpdateDate: Optional[datetime]

    class Config:
        from_attributes = True


class ProductSchema(ProductBase):
    hasActiveCampaign: Optional[bool] = False
    hasHtmlContent: Optional[bool] = False
    blacklisted: Optional[bool] = False
    images: Optional[List[ImageSchema]]
    attributes: Optional[List[AttributeSchema]]

    class Config:
        from_attributes = True


class ProductUpdateSchema(BaseModel):
    quantity: int
    listPrice: Optional[float]
    salePrice: Optional[float]
    title: Optional[str]
    productMainId: Optional[str]
    brandId: Optional[int]
    pimCategoryId: Optional[int]
    stockCode: Optional[str]
    dimensionalWeight: Optional[float]
    description: Optional[str]
    vatRate: Optional[float]
    images: Optional[List[ImageSchema]]
    attributes: Optional[List[AttributeSchema]]

    class Config:
        from_attributes = True
        populate_by_name = True


class ProductStockUpdate(BaseModel):
    quantity: int


class ProductPriceUpdate(BaseModel):
    salePrice: Optional[float]
    listPrice: Optional[float]


class ProductFullUpdate(ProductBase):
    pass


class ProductUpdateBatch(BaseModel):
    ids: List[str]  # List of barcodes or productMainIds
    data: Union[ProductPriceUpdate, ProductPriceUpdate, ProductFullUpdate]


class ProductDeleteSchema:

    def __init__(self, items):
        self.items = items

    def __str__(self):
        return f"Products to delete: {len(self.items)}"

    def add_item(self, barcode):
        self.items.append({"barcode": barcode})

    def to_dict(self):
        return {"items": self.items}

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("items", []))


class ProductGet:

    def __init__(self, code: str):
        self.code = code
        self.approved: Optional[bool] = None
        self.barcode: Optional[str] = None
        self.start_date: Optional[int] = None
        self.end_date: Optional[int] = None
        self.page: Optional[int] = None
        self.date_query_type: Optional[str] = None
        self.size: Optional[int] = None
        self.supplierId: Optional[int] = None
        self.stockCode: Optional[str] = None
        self.archived: Optional[bool] = None
        self.productMainId: Optional[str] = None
        self.onSale: Optional[bool] = None
        self.rejected: Optional[bool] = None
        self.blacklisted: Optional[bool] = None
        self.brandIds: Optional[List[int]] = None

    def __str__(self):
        return f"Product Code: {self.code}"

    def prepare_request_params(self) -> dict:
        params = {}
        if self.approved is not None:
            params["approved"] = self.approved
        if self.barcode:
            params["barcode"] = self.barcode
        if self.start_date:
            params["startDate"] = self.start_date
        if self.end_date:
            params["endDate"] = self.end_date
        if self.page is not None:
            params["page"] = self.page
        if self.date_query_type:
            params["dateQueryType"] = self.date_query_type
        if self.size is not None:
            params["size"] = self.size
        if self.supplierId is not None:
            params["supplierId"] = self.supplierId
        if self.stockCode:
            params["stockCode"] = self.stockCode
        if self.archived is not None:
            params["archived"] = self.archived
        if self.productMainId:
            params["productMainId"] = self.productMainId
        if self.onSale is not None:
            params["onSale"] = self.onSale
        if self.rejected is not None:
            params["rejected"] = self.rejected
        if self.blacklisted is not None:
            params["blacklisted"] = self.blacklisted
        if self.brandIds:
            params["brandIds"] = self.brandIds
        return params
