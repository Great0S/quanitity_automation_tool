from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
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
    marketplaceId: str
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
    marketplace_id: Optional[str] = None
    language_tag: Optional[str] = None

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
    marketplaceId: str
    status: str
    itemName: str
    createdDate: datetime
    lastUpdatedDate: datetime
    productType: Optional[str] = None

class ListingsItem(BaseModel):
    sku: str
    summaries: List[ListingsSummaries]
    attributes: Optional[Dict[str, List[AttributeValue]]] = None
    issues: Optional[List[Issue]] = None
    offers: Optional[List[ListingsOfferType]] = None
    fulfillmentAvailability: Optional[List[FulfillmentAvailability]] = None
    procurement: Optional[Procurement] = None

class ErrorList(BaseModel):
    errors: List[Issue]

# Request and Response models for each operation
class GetListingsItemRequest(BaseModel):
    marketplaceIds: List[str]
    issueLocale: Optional[str] = None
    includedData: Optional[List[str]] = None

class GetListingsItemResponse(BaseModel):
    sku: str
    summaries: List[ListingsSummaries]
    attributes: Optional[Dict[str, List[AttributeValue]]] = None
    issues: Optional[List[Issue]] = None
    offers: Optional[List[ListingsOfferType]] = None
    fulfillmentAvailability: Optional[List[FulfillmentAvailability]] = None
    procurement: Optional[Procurement] = None

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