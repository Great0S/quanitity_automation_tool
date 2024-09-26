import os
from datetime import datetime
from contextlib import asynccontextmanager
import traceback
from typing import List, Optional, Type, TypeVar, Union
from pydantic import BaseModel

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from box import Box

from services.trendyol_service.models import Attribute, Base, Image, Product
from services.trendyol_service.schemas import AttributeSchema, ImageSchema, ProductPriceUpdate, ProductSchema, ProductStockUpdate, ProductBase
from shared.logging import logger

T = TypeVar('T', bound=BaseModel)

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME")

        self.database_url = f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_async_engine(
            self.database_url,
            pool_size=20,
            max_overflow=40,
            pool_timeout=60
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_db(self):
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_product(self, product: ProductSchema) -> Product:
        """Function to create a new product in the database."""
        async with self.get_db() as db:
            try:
                product = Box(product)
                # Check if the product already exists
                existing_product = await self._get_existing_product(db, product.stockCode)
                if existing_product:
                    # logger.info(f"Product with barcode {product.barcode} already exists. Skipping.")
                    return existing_product

                db_product = await self._create_new_product(db, product)
                await self._add_images(db, db_product, product.images)
                await self._add_attributes(db, db_product, product.attributes)

                await db.refresh(db_product)
                return db_product

            except SQLAlchemyError as e:
                logger.error(f"Error creating product: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating product: {str(e)}")
                logger.debug(traceback.format_exc())
                raise

    async def _get_existing_product(self, db: AsyncSession, identifier: str) -> Optional[Product]:
        result = await db.execute(select(Product).filter(Product.stockCode == identifier))
        return result.scalar_one_or_none()

    async def _create_new_product(self, db: AsyncSession, product: ProductSchema) -> Product:
        db_product = Product(
            barcode=product.barcode,
            title=product.title,
            productMainId=product.productMainId,
            brandId=product.brandId,
            pimCategoryId=product.pimCategoryId,
            categoryName=product.categoryName,
            quantity=product.quantity,
            stockCode=product.stockCode,
            dimensionalWeight=product.dimensionalWeight,
            description=product.description,
            brand=product.brand,
            listPrice=product.listPrice,
            salePrice=product.salePrice,
            vatRate=product.vatRate,
            hasActiveCampaign=product.hasActiveCampaign,
            hasHtmlContent=product.hasHtmlContent,
            createDateTime=datetime.now(),
            lastUpdateDate=datetime.now(),
            blacklisted=product.blacklisted,
        )
        db.add(db_product)
        await db.flush()
        return db_product

    async def _add_images(self, db: AsyncSession, product: Product, images: List[ImageSchema]):
        if not images:
            logger.warning(f"No images provided for product {product.stockCode}")
            return

        for img in images:
            try:
                if isinstance(img, ImageSchema):
                    db.add(Image(url=img.url, product_id=product.id))
                elif isinstance(img, dict) and 'url' in img:
                    db.add(Image(url=img['url'], product_id=product.id))
                elif isinstance(img, str):
                    db.add(Image(url=img, product_id=product.id))
                else:
                    logger.warning(f"Invalid image data for product {product.stockCode}: {img}")
            except Exception as e:
                logger.error(f"Error adding image for product {product.stockCode}: {str(e)}")
                logger.debug(traceback.format_exc())

    async def _add_attributes(self, db: AsyncSession, product: Product, attributes: List[AttributeSchema]):
        if not attributes:
            logger.warning(f"No attributes provided for product {product.stockCode}")
            return

        for attr in attributes:
            try:
                if isinstance(attr, AttributeSchema) or isinstance(attr, dict):
                    db.add(Attribute(
                        attributeId=attr.attributeId,
                        attributeName=attr.attributeName,
                        attributeValue=str(attr.attributeValue),  # Convert to string as per the model
                        product_id=product.id,
                    ))
                else:
                    logger.warning(f"Invalid attribute data for product {product.stockCode}: {attr}")
            except Exception as e:
                logger.error(f"Error adding attribute for product {product.stockCode}: {str(e)}")
                logger.debug(traceback.format_exc())
        
    async def get_item(self, model: Type[T], identifier: str) -> Optional[dict]:
        """Get an item from the database by code or barcode and return as a dictionary."""
        async with self.get_db() as db:
            try:
                result = await db.execute(select(model).filter(model.stockCode == identifier))
                item = result.scalar_one_or_none()

                if item:
                    return {column.name: getattr(item, column.name) for column in item.__table__.columns}
                else:
                    logger.info(f"Item with identifier {identifier} not found")
                    return None

            except SQLAlchemyError as e:
                logger.error(f"Error querying item: {str(e)}")
                raise

    async def update_item(self, stock_code: str, product_update: Union[ProductStockUpdate, ProductPriceUpdate, ProductBase]) -> Optional[Product]:
        """Update a product in the database based on ProductBase."""
        async with self.get_db() as db:
            try:
                result = await db.execute(select(Product).filter(Product.stockCode == stock_code))
                db_product = result.scalar_one_or_none()

                if db_product:
                    product_update = product_update.model_dump(exclude_none=True, exclude_unset=True)
                    for field, value in product_update.items():
                        if field == "images":
                            await self._update_images(db, db_product, value)
                        elif field == "attributes":
                            await self._update_attributes(db, db_product, value)
                        else:
                            setattr(db_product, field, value)

                    await db.commit()
                    await db.refresh(db_product)
                    return db_product

                logger.info(f"Product with stock code {stock_code} not found for update")
                return None

            except SQLAlchemyError as e:
                logger.error(f"Error updating product: {str(e)}")
                raise

    async def _update_images(self, db, product: Product, images: List[dict]):
        # Remove existing images
        await db.execute(delete(Image).where(Image.product_id == product.id))

        # Add new images
        for img in images:
            db.add(Image(url=img["url"], product_id=product.id))

    async def _update_attributes(self, db, product: Product, attributes: List[dict]):
        # Remove existing attributes
        await db.execute(delete(Attribute).where(Attribute.product_id == product.id))

        # Add new attributes
        for attr in attributes:
            db.add(Attribute(
                attributeId=attr["attributeId"],
                attributeName=attr["attributeName"],
                attributeValue=attr["attributeValue"],
                product_id=product.id,
            ))

    async def delete_product(self, model: Type[T], identifier: str) -> Optional[T]:
        """Delete a product from the database."""
        async with self.get_db() as db:
            try:
                result = await db.execute(select(model).filter(model.stockCode == identifier))
                db_item = result.scalar_one_or_none()

                if db_item:
                    await db.delete(db_item)
                    await db.commit()
                    return db_item

                    logger.info(f"Product with stock code {identifier} not found for deletion")
                return None

            except SQLAlchemyError as e:
                logger.error(f"Error deleting product: {str(e)}")
                raise

    async def get_all_products(self) -> List[Product]:
        """Retrieve all products from the database."""
        async with self.get_db() as db:
            try:
                result = await db.execute(select(Product))
                return result.scalars().all()
            except SQLAlchemyError as e:
                logger.error(f"Error querying products: {str(e)}")
                raise

    async def get_product_by_stock_code(self, identifier: str) -> Optional[Product]:
        """Retrieve a product by stock code from the database."""
        async with self.get_db() as db:
            try:
                result = await db.execute(select(Product).filter(Product.stockCode == identifier))
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"Error querying product: {str(e)}")
                raise