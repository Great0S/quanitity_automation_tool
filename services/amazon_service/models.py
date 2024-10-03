from sqlalchemy import Column, Float, Integer, String, Enum, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum
from datetime import datetime, UTC

Base = declarative_base()

class ProductType(PyEnum):
    HOME_BED_AND_BATH = "HOME_BED_AND_BATH"
    RUG = "RUG"
    CARPET = "CARPET"
    AREA_RUGS = "AREA_RUGS"
    BATHTUB_SHOWER_MAT = "BATHTUB_SHOWER_MAT"
    DOOR_MATS = "DOOR_MATS"
    BATH_RUGS = "BATH_RUGS"
    OUTDOOR_RUGS = "OUTDOOR_RUGS"
    CARPET_TILES = "CARPET_TILES"
    STAIR_TREADS = "STAIR_TREADS"
    DOLL_CLOTHING = "DOLL_CLOTHING"
    ANTI_FATIGUE_FLOOR_MAT = "ANTI_FATIGUE_FLOOR_MAT"
    LADDER = "LADDER"
    CARPETING = "CARPETING"
    UTILITY_KNIFE = "UTILITY_KNIFE"
    TOY_FIGURE = "TOY_FIGURE"
    SHOE_TREE = "SHOE_TREE"
    VEHICLE_MAT = "VEHICLE_MAT"
    CABINET = "CABINET"
    DEHUMIDIFIER = "DEHUMIDIFIER"
    DRAFT_STOPPER = "DRAFT_STOPPER"
    GAME_DICE = "GAME_DICE"
    MINIATURE_TOY_FURNISHING = "MINIATURE_TOY_FURNISHING"
    RUG_PAD = "RUG_PAD"
    SHOES = "SHOES"
    SLIPPER = "SLIPPER"
    SWEATSHIRT = "SWEATSHIRT"
    WALL_ART = "WALL_ART"
    OTHER = "OTHER"

class PatchOperationType(PyEnum):
    ADD = "add"
    REPLACE = "replace"
    DELETE = "delete"

class IssueType(PyEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"

class Status(PyEnum):
    ACCEPTED = "ACCEPTED"
    INVALID = "INVALID"

class AmazonProduct(Base):
    __tablename__ = "amazon_products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    listing_id = Column(String, default="N/A")
    quantity = Column(Integer, default=0)
    asin = Column(String, default="N/A")
    productTypes = Column('product_type', Enum(ProductType), default=ProductType.OTHER)
    browseClassification = Column(JSON, default={})
    color = Column(String, default="N/A")
    size = Column(String, default="N/A")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    attributes = relationship("AmazonProductAttribute", back_populates="product", cascade="all, delete-orphan")
    identifiers = relationship("AmazonProductIdentifier", back_populates="product", cascade="all, delete-orphan")
    images = relationship("AmazonProductImage", back_populates="product", cascade="all, delete-orphan")
    summaries = relationship("AmazonProductSummary", back_populates="product", cascade="all, delete-orphan")
    offers = relationship("AmazonOffer", back_populates="product", cascade="all, delete-orphan")
    fulfillment_availability = relationship("AmazonFulfillmentAvailability", back_populates="product", cascade="all, delete-orphan")
    procurement = relationship("AmazonProcurement", back_populates="product", uselist=False, cascade="all, delete-orphan")
    patch_requests = relationship("AmazonPatchRequest", back_populates="product", cascade="all, delete-orphan")
    put_requests = relationship("AmazonPutRequest", back_populates="product", cascade="all, delete-orphan")
    delete_requests = relationship("AmazonDeleteRequest", back_populates="product", cascade="all, delete-orphan")
    issues = relationship("AmazonProductIssue", back_populates="product", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.attributes is None:
            self.attributes = []
        if self.identifiers is None:
            self.identifiers = []
        if self.images is None:
            self.images = []
        if self.summaries is None:
            self.summaries = []
        if self.offers is None:
            self.offers = []
        if self.fulfillment_availability is None:
            self.fulfillment_availability = []
        if self.patch_requests is None:
            self.patch_requests = []
        if self.put_requests is None:
            self.put_requests = []
        if self.delete_requests is None:
            self.delete_requests = []
        if self.issues is None:
            self.issues = []
        # Note: procurement is a single object relationship, so we don't initialize it with a list

class AmazonProductAttribute(Base):
    __tablename__ = "amazon_product_attributes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))   
    name = Column(String)
    value = Column(JSON)

    product = relationship("AmazonProduct", back_populates="attributes")

class AmazonPatchRequest(Base):
    __tablename__ = "amazon_patch_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    product = relationship("AmazonProduct", back_populates="patch_requests")
    operations = relationship("AmazonPatchOperation", back_populates="patch_request", cascade="all, delete-orphan")
    issues = relationship("AmazonRequestIssue", back_populates="patch_request", cascade="all, delete-orphan")

class AmazonPatchOperation(Base):
    __tablename__ = "amazon_patch_operations"

    id = Column(Integer, primary_key=True, index=True)
    patch_request_id = Column(Integer, ForeignKey("amazon_patch_requests.id"))
    op = Column(Enum(PatchOperationType))
    path = Column(String)
    value = Column(JSON)

    patch_request = relationship("AmazonPatchRequest", back_populates="operations")

class AmazonPutRequest(Base):
    __tablename__ = "amazon_put_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    product = relationship("AmazonProduct", back_populates="put_requests")
    issues = relationship("AmazonRequestIssue", back_populates="put_request", cascade="all, delete-orphan")

class AmazonDeleteRequest(Base):
    __tablename__ = "amazon_delete_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    product = relationship("AmazonProduct", back_populates="delete_requests")
    issues = relationship("AmazonRequestIssue", back_populates="delete_request", cascade="all, delete-orphan")

class AmazonRequestIssue(Base):
    __tablename__ = "amazon_request_issues"

    id = Column(Integer, primary_key=True, index=True)
    patch_request_id = Column(Integer, ForeignKey("amazon_patch_requests.id"), nullable=True)
    put_request_id = Column(Integer, ForeignKey("amazon_put_requests.id"), nullable=True)
    delete_request_id = Column(Integer, ForeignKey("amazon_delete_requests.id"), nullable=True)
    code = Column(String)
    message = Column(String)
    severity = Column(Enum(IssueType))
    attribute_name = Column(String, nullable=True)

    patch_request = relationship("AmazonPatchRequest", back_populates="issues")
    put_request = relationship("AmazonPutRequest", back_populates="issues")
    delete_request = relationship("AmazonDeleteRequest", back_populates="issues")

class AmazonOffer(Base):
    __tablename__ = "amazon_offers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    
    price = Column(JSON)
    points = Column(JSON, nullable=True)

    product = relationship("AmazonProduct", back_populates="offers")

class AmazonFulfillmentAvailability(Base):
    __tablename__ = "amazon_fulfillment_availability"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    fulfillment_channel_code = Column(String)
    quantity = Column(Integer)

    product = relationship("AmazonProduct", back_populates="fulfillment_availability")

class AmazonProcurement(Base):
    __tablename__ = "amazon_procurement"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    cost_price = Column(JSON)
    minimum_order_quantity = Column(Integer, nullable=True)

    product = relationship("AmazonProduct", back_populates="procurement")

class AmazonProductSummary(Base):
    __tablename__ = "amazon_product_summaries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    
    brand = Column(String)
    browse_classification = Column(JSON)
    color = Column(String)
    item_classification = Column(String)
    item_name = Column(String)
    size = Column(String)
    website_display_group = Column(String)
    website_display_group_name = Column(String)

    product = relationship("AmazonProduct", back_populates="summaries")

class AmazonProductIssue(Base):
    __tablename__ = "amazon_product_issues"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    code = Column(String)
    message = Column(String)
    severity = Column(Enum(IssueType))
    attribute_name = Column(String, nullable=True)

    product = relationship("AmazonProduct", back_populates="issues")

class AmazonProductIdentifier(Base):
    __tablename__ = "amazon_product_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    
    identifier_type = Column(String)
    identifier = Column(String)

    product = relationship("AmazonProduct", back_populates="identifiers")

class AmazonProductImage(Base):
    __tablename__ = "amazon_product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"))
    
    variant = Column(String)
    link = Column(String)
    height = Column(Integer)
    width = Column(Integer)

    product = relationship("AmazonProduct", back_populates="images")
