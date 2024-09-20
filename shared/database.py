import os
from datetime import datetime
from contextlib import contextmanager
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from services.trendyol_service.models import Attribute, Base, Image, Product
from services.trendyol_service.schemas import ProductSchema, ProductUpdateSchema
from .logging import logger


class DatabaseManager:

    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME")

        self.database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_engine(self.database_url,
                                    pool_size=20,
                                    max_overflow=40,
                                    pool_timeout=60)
        self.session_local = sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=self.engine)

        # Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_db(self):
        """Provide a transactional scope around a series of operations."""
        db = self.session_local()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_db_product(self, product: ProductSchema) -> Product:
        """Function to create a new product in the database."""
        with self.get_db() as db:
            try:
                # Check if the product already exists
                existing_product = db.query(Product).filter(
                    Product.barcode == product["barcode"]).first()

                if existing_product:
                    logger.info(
                        "Product with barcode %s already exists. Skipping.",
                        product['barcode'])
                    return existing_product

                # Convert timestamp to datetime
                created_date = datetime.fromtimestamp(
                    product["createDateTime"] / 1000)
                last_update_date = datetime.fromtimestamp(
                    product["lastUpdateDate"] / 1000)

                # Create the product first
                db_product = Product(
                    barcode=product["barcode"],
                    title=product["title"],
                    product_main_id=product["productMainId"],
                    brand_id=product["brandId"],
                    category_id=product["pimCategoryId"],
                    category_name=product["categoryName"],
                    quantity=product["quantity"],
                    stock_code=product["stockCode"],
                    dimensional_weight=product["dimensionalWeight"],
                    description=product.get("description"),
                    brand=product["brand"],
                    list_price=product["listPrice"],
                    sale_price=product["salePrice"],
                    vat_rate=product["vatRate"],
                    has_active_campaign=product.get("hasActiveCampaign",
                                                    False),
                    has_html_content=product.get("hasHtmlContent", False),
                    created_date=created_date,
                    last_update_date=last_update_date,
                    blacklisted=product.get("blacklisted", False),
                )
                db.add(db_product)
                db.flush()  # This will assign an ID to db_product

                if "images" in product:
                    for img in product["images"]:
                        db.add(
                            Image(url=img.get("url"),
                                  product_id=db_product.id))

                # Create and add attributes
                if "attributes" in product:
                    for attr in product["attributes"]:
                        db.add(
                            Attribute(
                                attribute_id=attr.get("attributeId"),
                                attribute_name=attr.get("attributeName"),
                                attribute_value=attr.get("attributeValue"),
                                product_id=db_product.id,
                            ))

                db.refresh(db_product)
                return db_product

            except SQLAlchemyError as e:
                db.rollback()
                logger.error("Error creating product: %s", str(e))
                raise

    def get_item(self, model, identifier):
        """Helper function to get an item from the database by code or barcode and return as JSON."""
        with self.get_db() as db:
            try:
                item = db.query(model).filter(
                    model.stock_code == identifier).first()

                if item:
                    item_dict = {
                        column.name: getattr(item, column.name)
                        for column in item.__table__.columns
                    }
                    return item_dict
                else:
                    return JSONResponse(content={"message": "Item not found"},
                                        status_code=404)

            except SQLAlchemyError as e:
                db.rollback()
                logger.error("Error querying product: %s", str(e))
                return JSONResponse(
                    content={"error": "Database error occurred"},
                    status_code=500)

    def update_item(self, product_id, product_update: ProductUpdateSchema):
        """Update a product in the database based on ProductUpdate object."""
        with self.get_db() as db:
            try:
                db_product = db.query(Product).filter(
                    Product.barcode == product_id).first()

                if db_product:
                    # Update required fields
                    db_product.quantity = product_update['quantity']
                    db_product.sale_price = product_update['sale_price']
                    db_product.list_price = product_update['list_price']

                    # Update optional fields if they are provided
                    optional_fields = [
                        "title",
                        "product_main_id",
                        "brand_id",
                        "category_id",
                        "stock_code",
                        "dimensional_weight",
                        "description",
                        "currency_type",
                        "vat_rate",
                        "cargo_company_id",
                        "shipment_address_id",
                        "returning_address_id",
                    ]

                    for field in optional_fields:
                        value = getattr(product_update, field, None)
                        if value is not None:
                            setattr(db_product, field, value)

                    # Handle nested objects
                    if "images" in product_update and product_update['images']:
                        for img in product_update["images"]:
                            db.add(
                                Image(url=img.get("url"),
                                      product_id=db_product.id))

                    # Create and add attributes
                    if "attributes" in product_update and product_update[
                            "attributes"]:
                        for attr in product_update["attributes"]:
                            db.add(
                                Attribute(
                                    attribute_id=attr.get("attributeId"),
                                    attribute_name=attr.get("attributeName"),
                                    attribute_value=attr.get("attributeValue"),
                                    product_id=db_product.id,
                                ))

                    db.commit()
                    db.refresh(db_product)
                    return db_product

                return None

            except SQLAlchemyError as e:
                db.rollback()
                logger.error("Error updating product: %s", str(e))
                raise

    def delete_products(self, model, barcode):
        """Function to delete multiple products from the database."""
        with self.get_db() as db:
            deleted_items = []
            db_item = db.query(model).filter(model.barcode == barcode).first()
            if db_item:
                db.delete(db_item)
                deleted_items.append(db_item)
            return deleted_items

    def get_all_products(self):
        """Function to retrieve all products from the database."""
        with self.get_db() as db:
            try:
                products = db.query(Product).all()
                return products
            except SQLAlchemyError as e:
                db.rollback()
                logger.error("Error querying products: %s", str(e))
                return []

    def get_product_by_barcode(self, barcode):
        """Function to retrieve a product by barcode from the database."""
        with self.get_db() as db:
            try:
                product = db.query(Product).filter(
                    Product.barcode == barcode).first()
                return product
            except SQLAlchemyError as e:
                db.rollback()
                logger.error("Error querying product: %s", str(e))
