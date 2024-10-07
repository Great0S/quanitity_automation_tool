import os
from datetime import datetime
from contextlib import asynccontextmanager
import traceback
from typing import List, Optional, Type, TypeVar, Union
from pydantic import BaseModel

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from box import Box

from services.n11_service.schemas import N11ProductCreateSchema, N11ProductResponseSchema, N11ProductSchema, N11ProductUpdateSchema
from services.n11_service.models import Base, N11Product, N11ProductAttribute
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

    async def create_n11_product(self, product_json: N11ProductCreateSchema) -> N11Product:
        async with self.get_db() as session:
            try:
                product = Box(product_json)
                existing_product = await self._get_existing_product(session, product.stockCode)
                if existing_product:
                    await session.refresh(existing_product, ['attributes'])
                    return existing_product
                
                product_model = N11ProductCreateSchema(**product_json)
                db_product = await self._create_new_product(session, product_model)
                await self._add_attributes(session, db_product, product.attributes)

                await session.commit()
                
                # Reload the product with its attributes
                await session.refresh(db_product, ['attributes'])

                return db_product
            except SQLAlchemyError as e:
                logger.error(f"Error creating product: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating product: {str(e)}")
                logger.debug(traceback.format_exc())
                raise

    async def _get_existing_product(self, session: AsyncSession, stock_code: str) -> Optional[N11Product]:
        result = await session.execute(select(N11Product).filter(N11Product.stockCode == stock_code))
        return result.scalar_one_or_none()

    async def _create_new_product(self, session: AsyncSession, product: N11ProductCreateSchema) -> N11Product:
        db_product = N11Product(**product.model_dump(exclude={'attributes'}))
        session.add(db_product)
        await session.flush()
        return db_product

    async def _add_attributes(self, session: AsyncSession, product: N11Product, attributes: List[dict]):
        if not attributes:
            logger.warning(f"No attributes provided for product {product.stockCode}")
            return

        for attr in attributes:
            try:
                db_attribute = N11ProductAttribute(**attr, product_id=product.id)
                session.add(db_attribute)
            except Exception as e:
                logger.error(f"Error adding attribute for product {product.stockCode}: {str(e)}")
                logger.debug(traceback.format_exc())

    async def get_n11_product(self, stock_code: str) -> Optional[N11ProductSchema]:
        async with self.get_db() as session:
            try:
                result = await session.execute(
                    select(N11Product)
                    .options(selectinload(N11Product.attributes))
                    .filter(N11Product.stockCode == stock_code)
                )
                product = result.scalar_one_or_none()
                if product:
                    return N11ProductSchema.model_validate(product)
                return None
            except SQLAlchemyError as e:
                logger.error(f"Error querying product: {str(e)}")
                raise

    async def get_n11_products(self, limit: int = 100) -> List[N11ProductSchema]:
        async with self.get_db() as session:
            try:
                result = await session.execute(
                    select(N11Product)
                    .options(selectinload(N11Product.attributes))
                    .limit(limit)
                )
                products = result.scalars().all()
                
                # Convert to Pydantic models within the session context
                return [N11ProductSchema.model_validate(product) for product in products]
            except SQLAlchemyError as e:
                logger.error(f"Error querying products: {str(e)}")
                raise

    async def update_n11_product(self, stock_code: str, product_update: N11ProductUpdateSchema) -> Optional[N11ProductSchema]:
        async with self.get_db() as session:
            try:
                result = await session.execute(
                    select(N11Product)
                    .options(selectinload(N11Product.attributes))
                    .filter(N11Product.stockCode == stock_code)
                )
                db_product = result.scalar_one_or_none()

                if db_product:
                    update_data = product_update.model_dump(exclude_unset=True)
                    
                    for field, value in update_data.items():
                        if field == 'attributes':
                            await self._update_attributes(session, db_product, value)
                        else:
                            setattr(db_product, field, value)

                    await session.commit()
                    await session.refresh(db_product)
                    return N11ProductSchema.model_validate(db_product)

                logger.info(f"Product with stock code {stock_code} not found for update")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Error updating product: {str(e)}")
                raise

    async def _update_attributes(self, session: AsyncSession, product: N11Product, attributes: List[dict]):
        await session.execute(delete(N11ProductAttribute).where(N11ProductAttribute.product_id == product.id))
        for attr in attributes:
            db_attribute = N11ProductAttribute(**attr, product_id=product.id)
            session.add(db_attribute)

    async def delete_n11_product(self, stock_code: str) -> bool:
        async with self.get_db() as session:
            try:
                result = await session.execute(select(N11Product).filter(N11Product.stockCode == stock_code))
                db_product = result.scalar_one_or_none()

                if db_product:
                    await session.delete(db_product)
                    await session.commit()
                    return True

                logger.info(f"Product with stock code {stock_code} not found for deletion")
                return False
            except SQLAlchemyError as e:
                logger.error(f"Error deleting product: {str(e)}")
                raise