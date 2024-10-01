from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal
from datetime import datetime

from services.amazon_service.models import IssueType, PatchOperationType, ProductType, Status

class PatchOperation(BaseModel):
    op: PatchOperationType
    path: str
    value: Optional[Any] = None

class Issue(BaseModel):
    code: str
    message: str
    severity: IssueType
    attributeName: Optional[str] = None

class ListingsPatchRequest(BaseModel):
    productType: ProductType
    patches: List[PatchOperation]
    issueLocale: Optional[str] = None

class ListingsPatchResponse(BaseModel):
    sku: str
    status: Status
    submissionId: str
    issues: Optional[List[Issue]] = None

class Money(BaseModel):
    currencyCode: str
    amount: float

class Points(BaseModel):
    pointsNumber: int

class ListingsOfferPriceType(BaseModel):
    schedule: List[Dict[str, Any]]
    minimumAdvertisedPrice: Optional[Money] = None

class ListingsOfferType(BaseModel):
    
    offerType: str
    price: ListingsOfferPriceType
    points: Optional[Points] = None

class FulfillmentAvailability(BaseModel):
    fulfillmentChannelCode: str
    quantity: int

class Procurement(BaseModel):
    costPrice: Money

class AttributeValue(BaseModel):
    value: Any

class ListingsItemPutRequest(BaseModel):
    productType: ProductType
    requirements: str
    attributes: Dict[str, List[AttributeValue]]
    offers: Optional[List[ListingsOfferType]] = None
    fulfillmentAvailability: Optional[List[FulfillmentAvailability]] = None
    procurement: Optional[Procurement] = None

class ListingsItemPutResponse(BaseModel):
    sku: str
    status: Status
    submissionId: str
    issues: Optional[List[Issue]] = None

class ListingsItemDeleteResponse(BaseModel):
    sku: str
    status: Status
    submissionId: str
    issues: Optional[List[Issue]] = None

class ListingsSummaries(BaseModel):
    status: str
    itemName: str
    createdDate: datetime
    lastUpdatedDate: datetime
    productType: Optional[str] = None

class AmazonProductSchema(BaseModel):
    id: Optional[int] = None
    sku: str
    listing_id: str
    quantity: int
    asin: str
    productTypes: Optional[ProductType] = None
    browseClassification: Optional[Dict[str, Any]] = None
    color: Optional[str] = None
    size: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AmazonProductAttributeSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    
    name: str
    value: Any

class AmazonProductIdentifierSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    identifier_type: str
    identifier: str

class AmazonProductImageSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    variant: str
    link: str
    height: int
    width: int

class BrowseClassificationSchema(BaseModel):
    display_name: str
    classification_id: str

class AmazonProductSummarySchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    
    adult_product: bool
    autographed: bool
    brand: str
    browse_classification: BrowseClassificationSchema
    color: str
    item_classification: str
    item_name: str
    memorabilia: bool
    size: str
    trade_in_eligible: bool
    website_display_group: str
    website_display_group_name: str

class AmazonPatchRequestSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    patch_data: Dict[str, Any]
    status: Status
    submission_id: str
    created_at: Optional[datetime] = None

class AmazonPutRequestSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    put_data: Dict[str, Any]
    status: Status
    submission_id: str
    created_at: Optional[datetime] = None

class AmazonDeleteRequestSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    status: Status
    submission_id: str
    created_at: Optional[datetime] = None

class AmazonProductIssueSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    code: str
    message: str
    severity: IssueType
    attribute_name: Optional[str] = None

class AmazonOfferSchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    
    price: Dict[str, Any]
    points: Optional[Dict[str, Any]] = None

class AmazonFulfillmentAvailabilitySchema(BaseModel):
    id: Optional[int] = None
    product_id: int
    fulfillment_channel_code: str
    quantity: int

class ErrorList(BaseModel):
    errors: List[Issue]

# Request and Response models for each operation
class GetListingsItemRequest(BaseModel):
    marketplaceIds: List[str]
    issueLocale: Optional[str] = None
    includedData: Optional[List[str]] = None

class GetListingsItemResponse(BaseModel):
    sku: str
    listing_id: str
    quantity: int
    asin: str
    browseClassification: Optional[BrowseClassificationSchema] = None
    attributes: Optional[Dict[str, List[Any]]] = None
    images: Optional[List[Dict[str, Union[str, List[Dict[str, Union[str, int]]]]]]] = None  
    summaries: Optional[Dict[str, Any]] = None
    productTypes: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None

class PutListingsItemRequest(ListingsItemPutRequest):
    pass

class PutListingsItemResponse(ListingsItemPutResponse):
    pass

class PatchListingsItemRequest(ListingsPatchRequest):
    pass

class PatchListingsItemResponse(ListingsPatchResponse):
    pass

class DeleteListingsItemResponse(ListingsItemDeleteResponse):
    pass