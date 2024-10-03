import random
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

class AttributeValue(BaseModel):
    value: Union[str, List[str], Dict[str, Any], int]

class BrowseClassificationSchema(BaseModel):
    classificationId: Optional[str] = '0404'
    displayName: Optional[str] = 'N/A'

class AmazonProductSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    sku: str
    listing_id: str
    quantity: int
    asin: str
    productTypes: Optional[ProductType] = ProductType.OTHER
    browseClassification: Optional[BrowseClassificationSchema] = BrowseClassificationSchema()
    color: Optional[str] = 'N/A'
    size: Optional[str] = 'N/A'
    created_at: Optional[datetime] = datetime.now()
    updated_at: Optional[datetime] = datetime.now()

class AmazonProductAttributeSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    
    name: str
    value: AttributeValue

class AmazonProductIdentifierSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    identifier_type: str
    identifier: str

class AmazonProductImageSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    variant: str
    link: str
    height: int
    width: int

class AmazonProductSummarySchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    
    brand: str = 'N/A'
    browse_classification: BrowseClassificationSchema
    color: str = 'N/A'
    item_classification: str = 'N/A'
    item_name: str = 'N/A'
    size: str = 'N/A'
    website_display_group: str = 'N/A'
    website_display_group_name: str = 'N/A'

class AmazonPatchRequestSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    patch_data: Dict[str, Any]
    status: Status
    submission_id: str
    created_at: Optional[datetime] = datetime.now()

class AmazonPutRequestSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    put_data: Dict[str, Any]
    status: Status
    submission_id: str
    created_at: Optional[datetime] = datetime.now()

class AmazonDeleteRequestSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    status: Status
    submission_id: str
    created_at: Optional[datetime] = datetime.now()

class AmazonProductIssueSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    code: str
    message: str
    severity: IssueType
    attribute_name: Optional[str] = 'N/A'

class AmazonOfferSchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    
    price: Dict[str, Any]
    points: Optional[Dict[str, Any]] = {'pointsNumber': 0}

class AmazonFulfillmentAvailabilitySchema(BaseModel):
    id: Optional[int] = random.randint(1, 1000000)
    product_id: int
    fulfillment_channel_code: str = 'N/A'
    quantity: int

class ErrorList(BaseModel):
    errors: List[Issue]

# Request and Response models for each operation
class GetListingsItemRequest(BaseModel):
    marketplaceIds: List[str]
    issueLocale: Optional[str] = 'en_US'
    includedData: Optional[List[str]] = ['summaries']

class GetListingsItemResponse(BaseModel):
    sku: str
    listing_id: str
    quantity: int
    asin: str
    attributes: Dict[str, Union[AttributeValue, List[AttributeValue]]]
    images: List[AmazonProductImageSchema]
    productTypes: Optional[ProductType] = ProductType.OTHER
    browseClassification: Optional[BrowseClassificationSchema] = BrowseClassificationSchema()
    size: str = 'N/A'

