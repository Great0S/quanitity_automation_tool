import os
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update, delete
from datetime import datetime
from typing import List, Optional, Dict, Any, TypeVar
from contextlib import asynccontextmanager

from services.amazon_service.models import (
    Base, PatchOperationType, Product, ProductAttribute, PatchRequest, PutRequest, DeleteRequest,
    PatchOperation, Issue, ListingsItem, ListingsSummary, ListingsAttribute,
    ListingsIssue, ListingsOffer, FulfillmentAvailability, Procurement
)
from services.amazon_service.schemas import (
    ListingsPatchRequest, ListingsItemPutRequest, GetListingsItemRequest
)
from services.amazon_service.models import Status
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

    async def create_product(self, product_data: ListingsItemPutRequest) -> Product:
        async with self.get_db() as session:
            new_product = Product(
                sku=product_data.sku,
                product_type=product_data.productType
            )
            session.add(new_product)
            await session.flush()

            for name, values in product_data.attributes.items():
                for value in values:
                    attr = ProductAttribute(
                        product_id=new_product.id,
                        name=name,
                        value=value
                    )
                    session.add(attr)

            await session.commit()
            return new_product

    async def get_product(self, sku: str, request: GetListingsItemRequest) -> Optional[ListingsItem]:
        async with self.get_db() as session:
            query = select(Product).options(
                selectinload(Product.attributes),
                selectinload(Product.offers),
                selectinload(Product.fulfillment_availability),
                selectinload(Product.procurement)
            ).filter(Product.sku == sku)

            result = await session.execute(query)
            product = result.scalar_one_or_none()

            if not product:
                return None

            return ListingsItem(
                sku=product.sku,
                summaries=[ListingsSummary(
                    marketplace_id=marketplace_id,
                    status="BUYABLE",  # This should be determined based on your business logic
                    item_name=next((attr.value for attr in product.attributes if attr.name == "item_name"), None),
                    created_date=product.created_at,
                    last_updated_date=product.updated_at,
                    product_type=product.product_type
                ) for marketplace_id in request.marketplaceIds],
                attributes={attr.name: [attr.value] for attr in product.attributes},
                offers=[ListingsOffer.from_orm(offer) for offer in product.offers] if 'offers' in request.includedData else None,
                fulfillment_availability=[FulfillmentAvailability.from_orm(fa) for fa in product.fulfillment_availability] if 'fulfillmentAvailability' in request.includedData else None,
                procurement=Procurement.from_orm(product.procurement) if product.procurement and 'procurement' in request.includedData else None
            )

    async def update_product(self, sku: str, patch_request: ListingsPatchRequest) -> PatchRequest:
        async with self.get_db() as session:
            product = await session.execute(select(Product).filter(Product.sku == sku))
            product = product.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product with SKU {sku} not found")

            patch_req = PatchRequest(
                product_id=product.id,
                issue_locale=patch_request.issueLocale,
                status=Status.ACCEPTED,
                submission_id=f"submission_{datetime.utcnow().timestamp()}",
                created_at=datetime.utcnow()
            )
            session.add(patch_req)

            for patch in patch_request.patches:
                operation = PatchOperation(
                    patch_request_id=patch_req.id,
                    op=patch.op,
                    path=patch.path,
                    value=patch.value
                )
                session.add(operation)

                # Apply the patch operation to the product
                await self._apply_patch(session, product, patch)

            await session.commit()
            return patch_req

    async def _apply_patch(self, session: AsyncSession, product: Product, patch: PatchOperation):
        path_parts = patch.path.split('/')
        if path_parts[1] == 'attributes':
            attr_name = path_parts[2]
            if patch.op == PatchOperationType.REPLACE:
                stmt = select(ProductAttribute).filter(
                    ProductAttribute.product_id == product.id,
                    ProductAttribute.name == attr_name
                )
                result = await session.execute(stmt)
                attr = result.scalar_one_or_none()
                if attr:
                    attr.value = patch.value
                else:
                    new_attr = ProductAttribute(product_id=product.id, name=attr_name, value=patch.value)
                    session.add(new_attr)
            elif patch.op == PatchOperationType.DELETE:
                stmt = delete(ProductAttribute).filter(
                    ProductAttribute.product_id == product.id,
                    ProductAttribute.name == attr_name
                )
                await session.execute(stmt)
        # Add more conditions for other patch operations as needed

    async def delete_product(self, sku: str) -> DeleteRequest:
        async with self.get_db() as session:
            stmt = select(Product).filter(Product.sku == sku)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product with SKU {sku} not found")

            delete_req = DeleteRequest(
                product_id=product.id,
                status=Status.ACCEPTED,
                submission_id=f"deletion_{datetime.utcnow().timestamp()}",
                created_at=datetime.utcnow()
            )
            session.add(delete_req)

            await session.delete(product)
            await session.commit()

            return delete_req

    # Add more methods as needed for other operations