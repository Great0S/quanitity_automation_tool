from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    Boolean,
    DECIMAL,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True)
    title = Column(String)
    product_main_id = Column(String)
    brand_id = Column(Integer)
    category_id = Column(Integer)
    category_name = Column(String)
    quantity = Column(Integer)
    stock_code = Column(String)
    dimensional_weight = Column(Float)
    description = Column(String)
    brand = Column(String)
    list_price = Column(Float)
    sale_price = Column(Float)
    vat_rate = Column(Integer)
    has_active_campaign = Column(Boolean, default=False)
    has_html_content = Column(Boolean, default=False)
    created_date = Column(DateTime)
    last_update_date = Column(DateTime)
    blacklisted = Column(Boolean, default=False)

    # Relationships
    images = relationship("Image", back_populates="product")
    attributes = relationship("Attribute", back_populates="product")

    def __str__(self):
        return (
            f"Product: {self.title}\n"
            f"Barcode: {self.barcode}\n"
            f"Main ID: {self.product_main_id}\n"
            f"Price: {self.sale_price}\n"
            f"Quantity: {self.quantity}\n"
            f"Stock Code: {self.stock_code}\n"
            f"Images: {len(self.images)}\n"
            f"Attributes: {len(self.attributes)}"
        )


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    url = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="images")


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer)
    attribute_value = Column(String)
    attribute_name = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="attributes")
