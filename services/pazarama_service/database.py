import os
from datetime import datetime
from contextlib import asynccontextmanager
import traceback
from typing import List, Optional, Type, TypeVar, Union
from pydantic import BaseModel

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from box import Box

from services.pazarama_service.models import Base, PazaramaProduct, PazaramaProductAttribute, PazaramaProductImage, PazaramaDeliveryType
from services.pazarama_service.schemas import PazaramaProductCreateSchema, PazaramaProductSchema, PazaramaProductUpdateSchema, ProductAttributeSchema, ProductImageSchema, DeliveryTypeSchema
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

    async def create_product(self, product: PazaramaProductCreateSchema) -> Optional[PazaramaProduct]:
        async with self.get_db() as db:
            try:
                db_product = PazaramaProduct(
                    name=product.name,
                    displayName=product.displayName,
                    description=product.description,
                    brandName=product.brandName,
                    code=product.code,
                    groupCode=product.groupCode,
                    stockCount=product.stockCount,
                    stockCode=product.stockCode,
                    priorityRank=product.priorityRank,
                    listPrice=product.listPrice,
                    salePrice=product.salePrice,
                    vatRate=product.vatRate,
                    categoryName=product.categoryName,
                    categoryId=product.categoryId,
                    state=product.state,
                    status=product.status,
                    waitingApproveExp=product.waitingApproveExp
                )
                db.add(db_product)
                await db.flush()

                if product.attributes:  
                    await self._add_attributes(db, db_product, product.attributes)
                if product.images:
                    await self._add_images(db, db_product, product.images)
                if product.deliveryTypes:
                    await self._add_delivery_types(db, db_product, product.deliveryTypes)

                await db.commit()
                await db.refresh(db_product)
                return db_product
            except SQLAlchemyError as e:
                logger.error(f"Error creating product: {str(e)}")
                raise

    async def _add_attributes(self, db: AsyncSession, product: PazaramaProduct, attributes: List[ProductAttributeSchema]):
        for attr in attributes:
            db_attribute = PazaramaProductAttribute(
                name=attr.name,
                value=attr.value,
                product_id=product.id
            )
            db.add(db_attribute)

    async def _add_images(self, db: AsyncSession, product: PazaramaProduct, images: List[ProductImageSchema]):
        for img in images:
            db_image = PazaramaProductImage(
                url=img.url,
                product_id=product.id
            )
            db.add(db_image)

    async def _add_delivery_types(self, db: AsyncSession, product: PazaramaProduct, delivery_types: List[DeliveryTypeSchema]):
        for dt in delivery_types:
            db_delivery_type = PazaramaDeliveryType(
                type=dt.type,
                product_id=product.id
            )
            db.add(db_delivery_type)

    async def get_product(self, code: str) -> Optional[PazaramaProduct]:
        async with self.get_db() as db:
            try:
                if code:
                    result = await db.execute(
                        select(PazaramaProduct)
                        .options(selectinload(PazaramaProduct.attributes))
                        .options(selectinload(PazaramaProduct.images))
                        .options(selectinload(PazaramaProduct.delivery_types))
                        .filter(PazaramaProduct.code == code)
                    )
                    return result.scalar_one_or_none()
                else:
                    result = await db.execute(
                        select(PazaramaProduct)
                        .options(selectinload(PazaramaProduct.attributes))
                        .options(selectinload(PazaramaProduct.images))
                        .options(selectinload(PazaramaProduct.delivery_types))
                    )
                    return result.scalars().all()
            except SQLAlchemyError as e:
                logger.error(f"Error querying product: {str(e)}")
                raise

    async def update_product(self, code: str, product_update: List[PazaramaProductUpdateSchema]) -> Optional[PazaramaProduct]:
        async with self.get_db() as db:
            try:
                if code:
                    result = await db.execute(
                        select(PazaramaProduct)
                        .options(selectinload(PazaramaProduct.attributes))
                        .options(selectinload(PazaramaProduct.images))
                        .options(selectinload(PazaramaProduct.delivery_types))
                        .filter(PazaramaProduct.code == code)
                    )
                    db_product = result.scalar_one_or_none()

                    if db_product:
                        update_data = product_update.model_dump(exclude_unset=True, exclude_none=True)
                        for key, value in update_data.items():
                            if key == 'attributes':
                                await self._update_attributes(db, db_product, value)
                            elif key == 'images':
                                await self._update_images(db, db_product, value)
                            elif key == 'deliveryTypes':
                                await self._update_delivery_types(db, db_product, value)
                            else:   
                                setattr(db_product, key, value)

                    await db.commit()
                    await db.refresh(db_product)
                    return db_product
                else:
                    updated_products = []
                    for update in product_update:
                        result = await db.execute(
                            select(PazaramaProduct)
                            .options(selectinload(PazaramaProduct.attributes))
                            .options(selectinload(PazaramaProduct.images))
                            .options(selectinload(PazaramaProduct.delivery_types))
                        )
                        db_product = result.scalars().all()
                        
                        if db_product:
                            for key, value in update.model_dump(exclude_unset=True, exclude_none=True).items():
                                setattr(db_product, key, value)

                            if update.attributes:
                                await self._update_attributes(db, db_product, update.attributes)
                            if update.images:
                                await self._update_images(db, db_product, update.images)
                            if update.deliveryTypes:
                                await self._update_delivery_types(db, db_product, update.deliveryTypes)

                            updated_products.append(db_product)

                    await db.commit()
                    for product in updated_products:
                        await db.refresh(product)
                    return updated_products
            except SQLAlchemyError as e:
                logger.error(f"Error updating product: {str(e)}")
                raise

    async def _update_attributes(self, db: AsyncSession, product: PazaramaProduct, attributes: List[ProductAttributeSchema]):
        await db.execute(delete(PazaramaProductAttribute).where(PazaramaProductAttribute.product_id == product.id))
        await self._add_attributes(db, product, attributes)

    async def _update_images(self, db: AsyncSession, product: PazaramaProduct, images: List[ProductImageSchema]):
        await db.execute(delete(PazaramaProductImage).where(PazaramaProductImage.product_id == product.id))
        await self._add_images(db, product, images)

    async def _update_delivery_types(self, db: AsyncSession, product: PazaramaProduct, delivery_types: List[DeliveryTypeSchema]):
        await db.execute(delete(PazaramaDeliveryType).where(PazaramaDeliveryType.product_id == product.id))
        await self._add_delivery_types(db, product, delivery_types)

    async def delete_product(self, code: str) -> bool:
        async with self.get_db() as db:
            try:
                result = await db.execute(delete(PazaramaProduct).where(PazaramaProduct.code == code))
                deleted_count = result.rowcount
                await db.commit()
                return deleted_count > 0
            except SQLAlchemyError as e:
                logger.error(f"Error deleting product: {str(e)}")
                raise