from sqlalchemy import Column, Float, Integer, String, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class HepsiburadaProduct(Base):
    __tablename__ = 'hepsiburada_products'

    id = Column(Integer, primary_key=True)
    merchantSku = Column(String(100), unique=True, index=True)
    barcode = Column(String(100))
    hbSku = Column(String(100))
    variantGroupId = Column(String(100))
    productName = Column(String(255))
    brand = Column(String(100))
    categoryId = Column(Integer)
    categoryName = Column(String(100))
    tax = Column(Float(10, 2), default=0)
    price = Column(Float(10, 2), default=0)
    description = Column(Text)
    status = Column(String(50))
    stock = Column(Integer, default=0)

    images = relationship("HepsiburadaProductImage", back_populates="product", cascade="all, delete-orphan")
    baseAttributes = relationship("HepsiburadaProductAttribute", back_populates="product", cascade="all, delete-orphan")
    

class HepsiburadaProductImage(Base):
    __tablename__ = 'hepsiburada_product_images'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('hepsiburada_products.id'))
    url = Column(String(255))

    product = relationship("HepsiburadaProduct", back_populates="images")


class HepsiburadaProductAttribute(Base):
    __tablename__ = 'hepsiburada_product_attributes'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('hepsiburada_products.id'))
    name = Column(String(100))
    value = Column(Text)
    mandatory = Column(Boolean, default=False)

    product = relationship("HepsiburadaProduct", back_populates="baseAttributes")

    