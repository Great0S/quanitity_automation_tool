import os
from datetime import datetime
from contextlib import asynccontextmanager
import traceback
from typing import List, Optional, Type, TypeVar, Union
from pydantic import BaseModel

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from box import Box

from services.pttavm_service.models import Base, PTTAVMProduct
from services.pttavm_service.schemas import PTTAVMProductSchema, PTTAVMProductUpdateSchema


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

    async def create_product(self, product_data: PTTAVMProductSchema) -> PTTAVMProduct:
        async with self.get_db() as session:
            new_product = PTTAVMProduct(**product_data.model_dump())
            session.add(new_product)
            try:
                await session.commit()
                return new_product
            except SQLAlchemyError as e:
                await session.rollback()
                raise Exception(f"Error creating product: {str(e)}")

    async def update_product(self, barkod: str, product_data: PTTAVMProductUpdateSchema) -> PTTAVMProduct:
        async with self.get_db() as session:
            stmt = (
                update(PTTAVMProduct)
                .where(PTTAVMProduct.barkod == barkod)
                .values(**product_data.model_dump(exclude_unset=True))
            )
            try:
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount == 0:
                    raise Exception("Product not found")
                return await self.get_product(barkod)
            except SQLAlchemyError as e:
                await session.rollback()
                raise Exception(f"Error updating product: {str(e)}")

    async def get_product(self, barkod: str) -> Optional[PTTAVMProduct]:
        async with self.get_db() as session:
            stmt = select(PTTAVMProduct).where(PTTAVMProduct.barkod == barkod)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_product(self, barkod: str) -> bool:
        async with self.get_db() as session:
            stmt = delete(PTTAVMProduct).where(PTTAVMProduct.barkod == barkod)
            try:
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except SQLAlchemyError as e:
                await session.rollback()
                raise Exception(f"Error deleting product: {str(e)}")

