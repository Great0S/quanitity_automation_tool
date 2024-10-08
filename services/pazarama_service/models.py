from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class PazaramaProduct(Base):
    __tablename__ = 'pazarama_products'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    displayName = Column(String(255))
    description = Column(String)
    brandName = Column(String(100))
    code = Column(String(100), unique=True, index=True)
    groupCode = Column(String(100))
    stockCount = Column(Integer)
    stockCode = Column(String(100))
    priorityRank = Column(Integer)
    listPrice = Column(Float)
    salePrice = Column(Float)
    vatRate = Column(Integer)
    categoryName = Column(String(100))
    categoryId = Column(String(100))
    state = Column(Integer)
    status = Column(String(50))
    waitingApproveExp = Column(String)

    attributes = relationship("PazaramaProductAttribute", back_populates="product", cascade="all, delete-orphan")
    images = relationship("PazaramaProductImage", back_populates="product", cascade="all, delete-orphan")
    delivery_types = relationship("PazaramaDeliveryType", back_populates="product", cascade="all, delete-orphan")


class PazaramaProductAttribute(Base):
    __tablename__ = 'pazarama_product_attributes'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('pazarama_products.id'))
    name = Column(String(100))
    value = Column(String)

    product = relationship("PazaramaProduct", back_populates="attributes")


class PazaramaProductImage(Base):
    __tablename__ = 'pazarama_product_images'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('pazarama_products.id'))
    url = Column(String(255))

    product = relationship("PazaramaProduct", back_populates="images")


class PazaramaDeliveryType(Base):
    __tablename__ = 'pazarama_delivery_types'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('pazarama_products.id'))
    type = Column(String(100))

    product = relationship("PazaramaProduct", back_populates="delivery_types")

