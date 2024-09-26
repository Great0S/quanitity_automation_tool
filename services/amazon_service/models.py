from sqlalchemy import Column, Integer, String, Enum, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum
from datetime import datetime

Base = declarative_base()

class ProductType(PyEnum):
    HOME_BED_AND_BATH = "HOME_BED_AND_BATH"
    RUGS = "RUGS"
    CARPET = "CARPET"
    AREA_RUGS = "AREA_RUGS"
    RUNNERS = "RUNNERS"
    DOOR_MATS = "DOOR_MATS"
    BATH_RUGS = "BATH_RUGS"
    OUTDOOR_RUGS = "OUTDOOR_RUGS"
    CARPET_TILES = "CARPET_TILES"
    STAIR_TREADS = "STAIR_TREADS"

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

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    product_type = Column(Enum(ProductType))
    attributes = relationship("ProductAttribute", back_populates="product", cascade="all, delete-orphan")
    patch_requests = relationship("PatchRequest", back_populates="product", cascade="all, delete-orphan")
    put_requests = relationship("PutRequest", back_populates="product", cascade="all, delete-orphan")
    delete_requests = relationship("DeleteRequest", back_populates="product", cascade="all, delete-orphan")

class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    value = Column(JSON)

    product = relationship("Product", back_populates="attributes")

class PatchRequest(Base):
    __tablename__ = "patch_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="patch_requests")
    operations = relationship("PatchOperation", back_populates="patch_request", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="patch_request", cascade="all, delete-orphan")

class PatchOperation(Base):
    __tablename__ = "patch_operations"

    id = Column(Integer, primary_key=True, index=True)
    patch_request_id = Column(Integer, ForeignKey("patch_requests.id"))
    op = Column(Enum(PatchOperationType))
    path = Column(String)
    value = Column(JSON)

    patch_request = relationship("PatchRequest", back_populates="operations")

class PutRequest(Base):
    __tablename__ = "put_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="put_requests")
    issues = relationship("Issue", back_populates="put_request", cascade="all, delete-orphan")

class DeleteRequest(Base):
    __tablename__ = "delete_requests"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    issue_locale = Column(String)
    submission_id = Column(String)
    status = Column(Enum(Status))
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="delete_requests")
    issues = relationship("Issue", back_populates="delete_request", cascade="all, delete-orphan")

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    patch_request_id = Column(Integer, ForeignKey("patch_requests.id"), nullable=True)
    put_request_id = Column(Integer, ForeignKey("put_requests.id"), nullable=True)
    delete_request_id = Column(Integer, ForeignKey("delete_requests.id"), nullable=True)
    code = Column(String)
    message = Column(String)
    severity = Column(Enum(IssueType))
    attribute_name = Column(String, nullable=True)

    patch_request = relationship("PatchRequest", back_populates="issues")
    put_request = relationship("PutRequest", back_populates="issues")
    delete_request = relationship("DeleteRequest", back_populates="issues")

class ListingsItem(Base):
    __tablename__ = "listings_items"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    summaries = relationship("ListingsSummary", back_populates="item", cascade="all, delete-orphan")
    attributes = relationship("ListingsAttribute", back_populates="item", cascade="all, delete-orphan")
    issues = relationship("ListingsIssue", back_populates="item", cascade="all, delete-orphan")
    offers = relationship("ListingsOffer", back_populates="item", cascade="all, delete-orphan")
    fulfillment_availability = relationship("FulfillmentAvailability", back_populates="item", cascade="all, delete-orphan")
    procurement = relationship("Procurement", back_populates="item", uselist=False, cascade="all, delete-orphan")

class ListingsSummary(Base):
    __tablename__ = "listings_summaries"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"))
    marketplace_id = Column(String)
    status = Column(String)
    item_name = Column(String)
    created_date = Column(DateTime)
    last_updated_date = Column(DateTime)
    product_type = Column(String)

    item = relationship("ListingsItem", back_populates="summaries")

class ListingsAttribute(Base):
    __tablename__ = "listings_attributes"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"))
    name = Column(String)
    value = Column(JSON)

    item = relationship("ListingsItem", back_populates="attributes")

class ListingsIssue(Base):
    __tablename__ = "listings_issues"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"))
    code = Column(String)
    message = Column(String)
    severity = Column(Enum(IssueType))
    attribute_name = Column(String, nullable=True)

    item = relationship("ListingsItem", back_populates="issues")

class ListingsOffer(Base):
    __tablename__ = "listings_offers"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"))
    marketplace_id = Column(String)
    price = Column(JSON)
    points = Column(JSON, nullable=True)

    item = relationship("ListingsItem", back_populates="offers")

class FulfillmentAvailability(Base):
    __tablename__ = "fulfillment_availability"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"))
    fulfillment_channel_code = Column(String)
    quantity = Column(Integer)
    marketplace_id = Column(String)

    item = relationship("ListingsItem", back_populates="fulfillment_availability")

class Procurement(Base):
    __tablename__ = "procurement"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("listings_items.id"), unique=True)
    cost_price = Column(JSON)

    item = relationship("ListingsItem", back_populates="procurement")

