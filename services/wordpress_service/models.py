# models/product.py
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    permalink = Column(String, nullable=False)
    date_created = Column(String)  # Consider using DateTime for actual date objects
    date_modified = Column(String)
    type = Column(String)
    status = Column(String)
    featured = Column(Boolean)
    catalog_visibility = Column(String)
    description = Column(Text)
    short_description = Column(Text)
    sku = Column(String, unique=True, nullable=False)
    price = Column(Float)
    regular_price = Column(Float)
    sale_price = Column(Float)
    on_sale = Column(Boolean)
    purchasable = Column(Boolean)
    stock_quantity = Column(Integer)
    manage_stock = Column(Boolean)
    stock_status = Column(String)
    categories = Column(JSON)  # Store categories as JSON
    images = Column(JSON)  # Store images as JSON
    attributes = Column(JSON)  # Store attributes as JSON

    def __repr__(self):
        return f"<Product(name={self.name}, sku={self.sku}, price={self.price})>"