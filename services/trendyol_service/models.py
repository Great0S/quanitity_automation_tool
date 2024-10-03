from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = "trendyol_products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True)
    title = Column(String)
    productMainId = Column(String)
    brandId = Column(Integer)
    pimCategoryId = Column(Integer)
    categoryName = Column(String)
    quantity = Column(Integer)
    stockCode = Column(String)
    dimensionalWeight = Column(Float)
    description = Column(String)
    brand = Column(String)
    listPrice = Column(Float)
    salePrice = Column(Float)
    vatRate = Column(Integer)
    hasActiveCampaign = Column(Boolean, default=False)
    hasHtmlContent = Column(Boolean, default=False)
    createDateTime = Column(DateTime)
    lastUpdateDate = Column(DateTime)
    blacklisted = Column(Boolean, default=False)

    # Relationships
    images = relationship("Image", back_populates="product", cascade="all, delete-orphan")
    attributes = relationship("Attribute", back_populates="product", cascade="all, delete-orphan")


    def __str__(self):
        return (
            f"Product: {self.title}\n"
            f"Barcode: {self.barcode}\n"
            f"Main ID: {self.productMainId}\n"
            f"Price: {self.salePrice}\n"
            f"Quantity: {self.quantity}\n"
            f"Stock Code: {self.stockCode}\n"
            f"Images: {len(self.images)}\n"
            f"Attributes: {len(self.attributes)}"
        )


class Image(Base):
    __tablename__ = "trendyol_images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="images")


class Attribute(Base):
    __tablename__ = "trendyol_attributes"

    id = Column(Integer, primary_key=True, index=True)
    attributeId = Column(Integer)
    attributeValue = Column(String)
    attributeName = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="attributes")
