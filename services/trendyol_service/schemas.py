# Product Models
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class ImageSchema(BaseModel):
    url: Optional[HttpUrl]


class AttributeSchema(BaseModel):
    attributeId: Optional[int] = Field(
        ..., description="The unique identifier for the attribute")
    attributeValue: Optional[int] = Field(
        None, description="The value of the attribute")
    attributeName: Optional[str] = Field(None,
                                          description="Name of the attribute")

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    barcode: str
    title: str
    productMainId: str
    brandId: int
    pimCategoryId: int
    categoryName: str
    quantity: int
    stockCode: str
    dimensionalWeight: float
    description: Optional[str]
    brand: str
    listPrice: float
    salePrice: float
    vatRate: float

    def __str__(self):
        return (f"Product: {self.title}\n"
                f"Barcode: {self.barcode}\n"
                f"Main ID: {self.productMainId}\n"
                f"Price: {self.salePrice}\n"
                f"Quantity: {self.quantity}\n"
                f"Stock Code: {self.stockCode}\n")


class ProductInDB(ProductBase):
    id: int
    createDateTime: datetime
    lastUpdateDate: datetime

    class Config:
        from_attributes = True


class ProductSchema(ProductBase):
    hasActiveCampaign: Optional[bool] = False
    hasHtmlContent: Optional[bool] = False
    blacklisted: Optional[bool] = False
    images: Optional[List[ImageSchema]]
    attributes: Optional[List[AttributeSchema]]


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

    def __str__(self):
        base_info = (f"Product Update: {self.barcode}\n"
                     f"Quantity: {self.quantity}\n"
                     f"Sale Price: {self.salePrice}\n"
                     f"List Price: {self.listPrice}")

        if self.title:  # Check if it's a full update
            additional_info = (
                f"\nTitle: {self.title}\n"
                f"Main ID: {self.productMainId}\n"
                f"Stock Code: {self.stockCode}\n"
                f"Images: {len(self.images) if self.images else 0}\n"
                f"Attributes: {len(self.attributes) if self.attributes else 0}"
            )
            return base_info + additional_info

        return base_info


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
