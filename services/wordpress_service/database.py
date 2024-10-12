import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import TypeVar
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select

from services.wordpress_service.models import Base, Product
from services.wordpress_service.schemas import ProductCreate, UpdateStockSchema
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
            # await conn.run_sync(Base.metadata.drop_all)
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

    async def create_product(self, product_data: ProductCreate) -> Product:
        async with self.get_db() as session:
            new_product = Product(**product_data.model_dump())
            session.add(new_product)
            await session.commit()
            await session.refresh(new_product)  # Refresh to get the new ID
            logger.info(f"Created new product: {new_product}")
            return new_product

    async def get_product(self, product_id: int) -> Product:
        async with self.get_db() as session:
            try:
                result = await session.execute(select(Product).filter(Product.sku == product_id))
                product = result.scalar_one_or_none()  # Get the single product or raise an error
                logger.info(f"Retrieved product: {product}")
                return product
            except NoResultFound:
                logger.error(f"Product with ID {product_id} not found.")
                raise ValueError(f"Product with ID {product_id} not found.")


    async def update_product_stock(self, product_id: int, stock_data: UpdateStockSchema):
        async with self.get_db() as session:
            try:
                result = await session.execute(select(Product).where(Product.id == product_id))
                product = result.scalar_one()  # Get the single product or raise an error

                if stock_data.stock_quantity is not None:
                    product.stock_quantity = stock_data.stock_quantity
                if stock_data.stock_status is not None:
                    product.stock_status = stock_data.stock_status

                await session.commit()
                logger.info(f"Updated stock for product ID {product_id}: {stock_data}")
                return product
            except NoResultFound:
                logger.error(f"Product with ID {product_id} not found.")
                raise ValueError(f"Product with ID {product_id} not found.")

    async def delete_product(self, product_id: int) -> None:
        async with self.get_db() as session:
            try:
                result = await session.execute(select(Product).where(Product.id == product_id))
                product = result.scalar_one()  # Get the single product or raise an error
                await session.delete(product)
                await session.commit()
                logger.info(f"Deleted product ID {product_id}")
            except NoResultFound:
                logger.error(f"Product with ID {product_id} not found.")
                raise ValueError(f"Product with ID {product_id} not found.")