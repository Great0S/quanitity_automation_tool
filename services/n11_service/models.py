from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class N11Product(Base):
    __tablename__ = 'n11_products'

    id = Column(Integer, primary_key=True)
    n11ProductId = Column(Integer)
    sellerId = Column(Integer)
    sellerNickname = Column(String)
    stockCode = Column(String)
    title = Column(String)
    description = Column(String)
    categoryId = Column(Integer)
    productMainId = Column(String)
    status = Column(String)
    saleStatus = Column(String)
    preparingDay = Column(Integer)
    shipmentTemplate = Column(String)
    maxPurchaseQuantity = Column(Integer)
    catalogId = Column(Integer)
    barcode = Column(String)
    groupId = Column(Integer)
    currencyType = Column(String)
    salePrice = Column(Float)
    listPrice = Column(Float)
    quantity = Column(Integer)

    attributes = relationship("N11ProductAttribute", back_populates="product")

class N11ProductAttribute(Base):
    __tablename__ = 'n11_product_attributes'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('n11_products.id'))
    attributeId = Column(Integer)
    attributeName = Column(String)
    attributeValue = Column(String)

    product = relationship("N11Product", back_populates="attributes")
