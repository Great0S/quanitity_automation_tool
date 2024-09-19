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

    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    product_main_id = Column(String, nullable=False)
    brand_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    category_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    stock_code = Column(String, nullable=False)
    dimensional_weight = Column(Float, nullable=False)
    description = Column(String)
    brand = Column(String, nullable=False)
    list_price = Column(DECIMAL(10, 2), nullable=False)
    sale_price = Column(DECIMAL(10, 2), nullable=False)
    vat_rate = Column(Integer, nullable=False)
    has_active_campaign = Column(Boolean, default=False)
    has_html_content = Column(Boolean, default=False)
    created_date = Column(DateTime, nullable=False)
    last_update_date = Column(DateTime, nullable=False)
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="images")


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True)
    attribute_id = Column(Integer, nullable=False)
    attribute_value = Column(String, nullable=True)
    attribute_name = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="attributes")
