# Product Models
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ImageScheme(BaseModel):
    url: HttpUrl


class AttributeScheme(BaseModel):
    attribute_id: int = Field(..., description="The unique identifier for the attribute")
    attribute_value: Optional[int] = Field(None, description="The value of the attribute, if applicable")
    attribute_name: Optional[str] = Field(None, description="Name of the attribute, if applicable")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "attribute_id": 1,
                "attribute_value": 100,
                "attribute_name": "Custom Value"
            }
        }


class ProductScheme(BaseModel):
    barcode: str
    title: str
    product_main_id: str
    brand_id: int
    category_id: int
    category_name: str
    quantity: int
    stock_code: str
    dimensional_weight: float
    description: str
    brand: str
    list_price: Decimal
    sale_price: Decimal
    vat_rate: int
    has_active_campaign: bool
    has_html_content: bool
    created_date: int
    last_update_date: int
    blacklisted: bool
    images: List[ImageScheme]
    attributes: List[AttributeScheme]

    class Config:
        from_attributes = True

    def __str__(self):
        return (
            f"Product: {self.title}\n"
            f"Barcode: {self.barcode}\n"
            f"Main ID: {self.product_main_id}\n"
            f"Price: {self.sale_price} {self.currency_type}\n"
            f"Quantity: {self.quantity}\n"
            f"Stock Code: {self.stock_code}\n"
            f"Delivery: {self.delivery_option}\n"
            f"Images: {len(self.images)}\n"
            f"Attributes: {len(self.attributes)}"
        )


class ProductUpdate(BaseModel):
    barcode: str
    quantity: int
    sale_price: Decimal = Field(..., decimal_places=2)
    list_price: Decimal = Field(..., decimal_places=2)
    title: Optional[str] = None
    product_main_id: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    stock_code: Optional[str] = None
    dimensional_weight: Optional[float] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    vat_rate: Optional[int] = None
    blacklisted: Optional[bool] = None
    has_active_campaign: Optional[bool] = None
    has_html_content: Optional[bool] = None
    created_date: Optional[int] = None
    last_update_date: Optional[int] = None
    images: Optional[List[ImageScheme]] = None
    attributes: Optional[List[AttributeScheme]] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    def __str__(self):
        base_info = (f"Product Update: {self.barcode}\n"
                     f"Quantity: {self.quantity}\n"
                     f"Sale Price: {self.sale_price}\n"
                     f"List Price: {self.list_price}")

        if self.title:  # Check if it's a full update
            additional_info = (f"\nTitle: {self.title}\n"
                               f"Main ID: {self.product_main_id}\n"
                               f"Stock Code: {self.stock_code}\n"
                               f"Images: {len(self.images) if self.images else 0}\n"
                               f"Attributes: {len(self.attributes) if self.attributes else 0}")
            return base_info + additional_info
        else:
            return base_info


class ProductUpdateBatch(BaseModel):
    items: List[ProductUpdate]

    def __str__(self):
        return f"Product Update Batch: {len(self.items)} items"


class ProductDeleteScheme:
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
        self.supplier_id: Optional[int] = None
        self.stock_code: Optional[str] = None
        self.archived: Optional[bool] = None
        self.product_main_id: Optional[str] = None
        self.on_sale: Optional[bool] = None
        self.rejected: Optional[bool] = None
        self.blacklisted: Optional[bool] = None
        self.brand_ids: Optional[List[int]] = None

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
        if self.supplier_id is not None:
            params["supplierId"] = self.supplier_id
        if self.stock_code:
            params["stockCode"] = self.stock_code
        if self.archived is not None:
            params["archived"] = self.archived
        if self.product_main_id:
            params["productMainId"] = self.product_main_id
        if self.on_sale is not None:
            params["onSale"] = self.on_sale
        if self.rejected is not None:
            params["rejected"] = self.rejected
        if self.blacklisted is not None:
            params["blacklisted"] = self.blacklisted
        if self.brand_ids:
            params["brandIds"] = self.brand_ids
        return params
