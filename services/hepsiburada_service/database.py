import os
from contextlib import asynccontextmanager
from typing import Optional, TypeVar
from pydantic import BaseModel

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from services.hepsiburada_service.schemas import HepsiburadaProductSchema, ProductAttributeSchema, ProductImageSchema
from sqlalchemy.orm import sessionmaker, selectinload
from box import Box
from contextlib import asynccontextmanager
from sqlalchemy import inspect as sa_inspect

from shared.logging import logger
from services.hepsiburada_service.models import Base, HepsiburadaProduct, HepsiburadaProductAttribute, HepsiburadaProductImage

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
        try:
            async with self.engine.begin() as conn:
                # Check if tables exist
                def get_table_names(connection):
                    inspector = sa_inspect(connection)
                    return inspector.get_table_names()

                existing_tables = await conn.run_sync(get_table_names)
                await conn.run_sync(Base.metadata.drop_all)

                
                if not existing_tables:
                    logger.info("No existing tables found. Creating tables...")
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("Tables created successfully.")
                else:
                    model_tables = set(Base.metadata.tables.keys())
                    existing_tables_set = set(existing_tables)
                    if model_tables.issubset(existing_tables_set):
                        pass
                    else:
                        missing_tables = model_tables - existing_tables_set
                        logger.info(f"Creating missing tables: {missing_tables}")
                        await conn.run_sync(Base.metadata.create_all)
                        logger.info("Tables created successfully.")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            logger.error(f"Database URL: {self.database_url}")
            logger.error("Please check if the database server is running and accessible.")
            logger.error("Ensure that the following environment variables are set correctly:")
            logger.error(f"DB_USER: {self.db_user}")
            logger.error(f"DB_HOST: {self.db_host}")
            logger.error(f"DB_PORT: {self.db_port}")
            logger.error(f"DB_NAME: {self.db_name}")
            raise

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

    async def create_product(self, product: HepsiburadaProductSchema) -> Optional[HepsiburadaProduct]:
        async with self.get_db() as db:
            try:
                db_product = HepsiburadaProduct(
                    merchantSku=product.merchantSku,
                barcode=product.barcode,
                hbSku=product.hbSku,
                variantGroupId=product.variantGroupId,
                productName=product.productName,
                brand=product.brand,
                categoryId=product.categoryId,
                categoryName=product.categoryName,
                tax=product.tax,
                price=product.price,
                description=product.description,
                status=product.status,
                stock=product.stock
            )
                db.add(db_product)
                await db.flush()

                for img in product.images:
                    db_image = HepsiburadaProductImage(url=img.imageUrl, order=img.order, product_id=db_product.id)
                    db.add(db_image)

                for attr in product.baseAttributes + product.variantTypeAttributes + product.productAttributes:
                    db_attribute = HepsiburadaProductAttribute(
                        name=attr.name,
                        value=attr.value,
                        mandatory=attr.mandatory,
                        product_id=db_product.id
                    )
                    db.add(db_attribute)

                await db.commit()
                await db.refresh(db_product)
                return db_product
            except SQLAlchemyError as e:
                logger.error(f"Error creating product: {str(e)}")
                await db.rollback()
                return None

    async def get_product(self, merchantSku: str) -> Optional[HepsiburadaProductSchema]:
        async with self.get_db() as db:
            try:
                query = select(HepsiburadaProduct).filter(HepsiburadaProduct.merchantSku == merchantSku)
                
                query = query.options(
                    selectinload(HepsiburadaProduct.images),
                    selectinload(HepsiburadaProduct.baseAttributes),
                )
                result = await db.execute(query)
                db_product = result.scalar_one_or_none()
                if db_product:
                    product = HepsiburadaProductSchema(
                        merchantSku=db_product.merchantSku,
                        barcode=db_product.barcode,
                        hbSku=db_product.hbSku,
                        variantGroupId=db_product.variantGroupId,
                        productName=db_product.productName,
                        brand=db_product.brand,
                        images=[ProductImageSchema(imageUrl=img.imageUrl, order=img.order) for img in db_product.images],
                        categoryId=db_product.categoryId,
                        categoryName=db_product.categoryName,
                        tax=db_product.tax,
                        price=db_product.price,
                        description=db_product.description,
                        status=db_product.status,
                        baseAttributes=[ProductAttributeSchema(name=attr.name, value=attr.value, mandatory=attr.mandatory) 
                                        for attr in db_product.baseAttributes],
                        stock=db_product.stock
                    )
                    return product
                return None
            except SQLAlchemyError as e:
                logger.error(f"Error getting product: {str(e)}")
                return None

    async def update_product(self, merchantSku: str, product_update: HepsiburadaProductSchema) -> Optional[HepsiburadaProduct]:
        async with self.get_db() as db:
            try:
                result = await db.execute(select(HepsiburadaProduct).filter(HepsiburadaProduct.merchantSku == merchantSku))
                db_product = result.scalar_one_or_none()
                if db_product:
                    for key, value in product_update.dict(exclude_unset=True).items():
                        if key not in ['images', 'baseAttributes', 'variantTypeAttributes', 'productAttributes']:
                            setattr(db_product, key, value)

                # Update images
                await db.execute(delete(HepsiburadaProductImage).where(HepsiburadaProductImage.product_id == db_product.id))
                for img in product_update.images:
                    db_image = HepsiburadaProductImage(url=img.imageUrl, order=img.order, product_id=db_product.id)
                    db.add(db_image)

                # Update attributes
                await db.execute(delete(HepsiburadaProductAttribute).where(HepsiburadaProductAttribute.product_id == db_product.id))
                for attr in product_update.baseAttributes + product_update.variantTypeAttributes + product_update.productAttributes:
                    db_attribute = HepsiburadaProductAttribute(
                        name=attr.name,
                        value=attr.value,
                        mandatory=attr.mandatory,
                        product_id=db_product.id
                    )
                    db.add(db_attribute)

                await db.commit()
                return db_product
            except SQLAlchemyError as e:
                logger.error(f"Error updating product: {str(e)}")
                await db.rollback()
                return None

    async def delete_product(self, merchantSku: str) -> bool:
        async with self.get_db() as db:
            try:
                result = await db.execute(select(HepsiburadaProduct).filter(HepsiburadaProduct.merchantSku == merchantSku))
                db_product = result.scalar_one_or_none()
                if db_product:
                    await db.delete(db_product)
                    await db.commit()
                    return True
                return False
            except SQLAlchemyError as e:
                logger.error(f"Error deleting product: {str(e)}")
                await db.rollback()
                return False