from datetime import datetime
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
import os

from services.trendyol_service.models import Attribute, Base, Image, Product
from services.trendyol_service.scheme import ProductScheme, ProductUpdate
from .logging import logger


# Database connection settings
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Create the SQLAlchemy engine
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40, pool_timeout=60)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


# Common database operations
def create_db_product(product: ProductScheme) -> Product:
    """Function to create a new product in the database."""
    with get_db() as db:
        try:
            # Check if the product already exists
            existing_product = (
                db.query(Product).filter(Product.barcode == product["barcode"]).first()
            )

            if existing_product:
                logger.info(
                    f"Product with barcode {product['barcode']} already exists. Skipping."
                )
                return existing_product

            # Convert timestamp to datetime
            created_date = datetime.fromtimestamp(product["createDateTime"] / 1000)
            last_update_date = datetime.fromtimestamp(product["lastUpdateDate"] / 1000)

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
                has_active_campaign=product.get("hasActiveCampaign", False),
                has_html_content=product.get("hasHtmlContent", False),
                created_date=created_date,
                last_update_date=last_update_date,
                blacklisted=product.get("blacklisted", False),
            )
            db.add(db_product)
            db.flush()  # This will assign an ID to db_product

            if "images" in product:
                for img in product["images"]:
                    db.add(Image(url=img.get("url"), product_id=db_product.id))

            # Create and add attributes
            if "attributes" in product:
                for attr in product["attributes"]:
                    db.add(
                        Attribute(
                            attribute_id=attr.get("attributeId"),
                            attribute_name=attr.get("attributeName"),
                            attribute_value=attr.get("attributeValue"),
                            product_id=db_product.id,
                        )
                    )

            db.refresh(db_product)
            return db_product

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating product: {str(e)}")
            raise


def get_item(db, model, identifier):
    """
    Helper function to get an item from the database by code or barcode and return as JSON.

    :param db: Database session
    :param model: The model class to query
    :param identifier: The code or barcode to search for
    :return: JSONResponse with the found item or an error message
    """
    with get_db() as db:
        try:
            item = db.query(model).filter(model.stock_code == identifier).first()

            if item:
                # Convert the item to a dictionary
                item_dict = {
                    column.name: getattr(item, column.name)
                    for column in item.__table__.columns
                }
                # return JSONResponse(content=item_dict, status_code=200)
                return item_dict
            else:
                return JSONResponse(
                    content={"message": "Item not found"}, status_code=404
                )

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error querying product: {str(e)}")
            return JSONResponse(
                content={"error": "Database error occurred"}, status_code=500
            )


def update_item(product_update: ProductUpdate):
    """Update a product in the database based on ProductUpdate object."""
    # Query the database for the product with the matching barcode
    with get_db() as db:
        try:
            db_product = (
                db.query(Product)
                .filter(Product.barcode == product_update.barcode)
                .first()
            )

            if db_product:
                # Update required fields
                db_product.quantity = product_update.quantity
                db_product.sale_price = product_update.sale_price
                db_product.list_price = product_update.list_price

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
                    value = getattr(product_update, field)
                    if value is not None:
                        setattr(db_product, field, value)

                # Handle nested objects
                if product_update.delivery_option:
                    db_product.delivery_duration = (
                        product_update.delivery_option.delivery_duration
                    )
                    db_product.fast_delivery_type = (
                        product_update.delivery_option.fast_delivery_type
                    )

                if product_update.images:
                    # Assuming you have a separate table for images
                    db_product.images = [
                        Image(url=img.url) for img in product_update.images
                    ]

                if product_update.attributes:
                    # Assuming you have a separate table for attributes
                    db_product.attributes = [
                        Attribute(
                            attribute_id=attr.attribute_id,
                            attribute_value_id=attr.attribute_value_id,
                            custom_attribute_value=attr.custom_attribute_value,
                        )
                        for attr in product_update.attributes
                    ]

                db.commit()
                db.refresh(db_product)
                return db_product
            else:
                return None
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating product: {str(e)}")
            raise


def delete_products(model, barcode):
    """Function to delete multiple products from the database."""
    with get_db() as db:

        deleted_items = []
        db_item = db.query(model).filter(model.barcode == barcode).first()
        if db_item:
            db.delete(db_item)
            deleted_items.append(db_item)

        return deleted_items


# You can add more common database operations here
