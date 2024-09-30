import os
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update, delete
from datetime import datetime
from typing import List, Optional, Dict, Any, TypeVar, Union
from contextlib import asynccontextmanager
from sqlalchemy import inspect as sa_inspect

from services.amazon_service.models import (
    Base, PatchOperationType, AmazonProduct, AmazonProductAttribute, AmazonPatchRequest, AmazonPutRequest, AmazonDeleteRequest,
    AmazonPatchOperation, AmazonProductIssue, AmazonProductSummary, AmazonOffer,
    AmazonFulfillmentAvailability, AmazonProcurement, AmazonProductIdentifier, AmazonProductImage, ProductType
)
from services.amazon_service.schemas import (
    ListingsPatchRequest, ListingsItemPutRequest, GetListingsItemRequest, GetListingsItemResponse
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
        try:
            async with self.engine.begin() as conn:
                # Check if tables exist
                def get_table_names(connection):
                    inspector = sa_inspect(connection)
                    return inspector.get_table_names()

                existing_tables = await conn.run_sync(get_table_names)
                # await conn.run_sync(Base.metadata.drop_all)

                
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

    async def create_product(self, products_data: List[Dict]) -> List[AmazonProduct]:
        async with self.get_db() as session:
            new_products = []
            for product_data in products_data:
                new_product = AmazonProduct(
                    sku=product_data['sku'],
                    listing_id=product_data.get('listing-id'),
                    quantity=int(product_data.get('quantity', 0)),
                    asin=product_data.get('asin'),
                    product_type=ProductType(product_data.get('productType')) if product_data.get('productType') else None
                )
                session.add(new_product)
                await session.flush()

                # Add attributes
                for name, values in product_data.get('attributes', {}).items():
                    for value in values:
                        attr = AmazonProductAttribute(
                            product_id=new_product.id,
                            name=name,
                            value=value['value'],
                        )
                        session.add(attr)

                # Add identifiers
                for identifier_group in product_data.get('identifiers', []):
                    for identifier in identifier_group.get('identifiers', []):
                        ident = AmazonProductIdentifier(
                            product_id=new_product.id,
                            identifier_type=identifier.get('identifierType'),
                            identifier=identifier.get('identifier')
                        )
                        session.add(ident)

                # Add images
                for image_group in product_data.get('images', []):
                    for image in image_group.get('images', []):
                        img = AmazonProductImage(
                            product_id=new_product.id,
                            variant=image.get('variant'),
                            link=image.get('link'),
                            height=image.get('height'),
                            width=image.get('width')
                        )
                        session.add(img)

                # Add summaries
                for summary_data in product_data.get('summaries', []):
                    summary = AmazonProductSummary(
                        product_id=new_product.id,
                        adult_product=summary_data.get('adultProduct'),
                        autographed=summary_data.get('autographed'),
                        brand=summary_data.get('brand'),
                        browse_classification=summary_data.get('browseClassification'),
                        color=summary_data.get('color'),
                        item_classification=summary_data.get('itemClassification'),
                        item_name=summary_data.get('itemName'),
                        memorabilia=summary_data.get('memorabilia'),
                        size=summary_data.get('size'),
                        trade_in_eligible=summary_data.get('tradeInEligible'),
                        website_display_group=summary_data.get('websiteDisplayGroup'),
                        website_display_group_name=summary_data.get('websiteDisplayGroupName')
                    )
                    session.add(summary)

                new_products.append(new_product)

            await session.commit()
            return new_products

    async def get_products(self, sku: Optional[str] = None, request: GetListingsItemRequest = None) -> Union[List[GetListingsItemResponse], GetListingsItemResponse]:
        async with self.get_db() as session:
            query = select(AmazonProduct).options(
                selectinload(AmazonProduct.attributes),
                selectinload(AmazonProduct.identifiers),
                selectinload(AmazonProduct.images),
                selectinload(AmazonProduct.summaries),
                selectinload(AmazonProduct.offers),
                selectinload(AmazonProduct.fulfillment_availability),
                selectinload(AmazonProduct.procurement)
            )

            if sku:
                query = query.filter(AmazonProduct.sku == sku)

            result = await session.execute(query)
            products = result.scalars().all()

            if not products:
                return [] if not sku else None

            def create_response(product):
                item_response = GetListingsItemResponse(
                    sku=product.sku,
                    listing_id=product.listing_id,
                    quantity=product.quantity,
                    asin=product.asin,
                    attributes={attr.name: [{"value": attr.value, "marketplace_id": attr.marketplace_id, "language_tag": attr.language_tag}] for attr in product.attributes},
                    images=[{
                        "marketplaceId": image.marketplace_id,
                        "images": [{"variant": image.variant, "link": image.link, "height": image.height, "width": image.width}]
                    } for image in product.images],
                    productTypes= product.product_type,
                    browseClassification = product.summaries.browse_classification,
                    color = product.summaries.color,
                    size = product.summaries.size,
                )
                return item_response
            responses = [create_response(product) for product in products]
            return responses if not sku else responses[0] if responses else None

    async def update_product(self, sku: str, patch_request: ListingsPatchRequest) -> AmazonPatchRequest:
        async with self.get_db() as session:
            product = await session.execute(select(AmazonProduct).filter(AmazonProduct.sku == sku))
            product = product.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product with SKU {sku} not found")

            patch_req = AmazonPatchRequest(
                product_id=product.id,
                issue_locale=patch_request.issueLocale,
                status=Status.PENDING,
                submission_id=f"submission_{datetime.utcnow().timestamp()}",
                created_at=datetime.utcnow()
            )
            session.add(patch_req)

            try:
                for patch in patch_request.patches:
                    operation = AmazonPatchOperation(
                        patch_request_id=patch_req.id,
                        op=patch.op,
                        path=patch.path,
                        value=patch.value
                    )
                    session.add(operation)

                    # Apply the patch operation to the product
                    await self._apply_patch(session, product, patch)

                patch_req.status = Status.ACCEPTED
                await session.commit()
            except Exception as e:
                patch_req.status = Status.REJECTED
                await session.commit()
                logger.error(f"Error updating product {sku}: {str(e)}")
                raise

            return patch_req

    async def _apply_patch(self, session: AsyncSession, product: AmazonProduct, patch: AmazonPatchOperation):
        path_parts = patch.path.split('/')
        if path_parts[1] == 'attributes':
            await self._update_attribute(session, product, patch, path_parts[2])
        elif path_parts[1] == 'offers':
            await self._update_offer(session, product, patch)
        elif path_parts[1] == 'fulfillmentAvailability':
            await self._update_fulfillment_availability(session, product, patch)
        else:
            raise ValueError(f"Unsupported patch path: {patch.path}")

    async def _update_attribute(self, session: AsyncSession, product: AmazonProduct, patch: AmazonPatchOperation, attr_name: str):
        if patch.op == PatchOperationType.REPLACE:
            stmt = select(AmazonProductAttribute).filter(
                AmazonProductAttribute.product_id == product.id,
                AmazonProductAttribute.name == attr_name
            )
            result = await session.execute(stmt)
            attr = result.scalar_one_or_none()
            if attr:
                attr.value = patch.value
                # Update marketplace_id and language_tag if provided
                if isinstance(patch.value, dict):
                    attr.marketplace_id = patch.value.get('marketplace_id', attr.marketplace_id)
                    attr.language_tag = patch.value.get('language_tag', attr.language_tag)
            else:
                new_attr = AmazonProductAttribute(
                    product_id=product.id,
                    name=attr_name,
                    value=patch.value if not isinstance(patch.value, dict) else patch.value['value'],
                    marketplace_id=patch.value.get('marketplace_id') if isinstance(patch.value, dict) else None,
                    language_tag=patch.value.get('language_tag') if isinstance(patch.value, dict) else None
                )
                session.add(new_attr)
        elif patch.op == PatchOperationType.DELETE:
            stmt = delete(AmazonProductAttribute).filter(
                AmazonProductAttribute.product_id == product.id,
                AmazonProductAttribute.name == attr_name
            )
            await session.execute(stmt)
        else:
            raise ValueError(f"Unsupported operation for attributes: {patch.op}")

    async def _update_offer(self, session: AsyncSession, product: AmazonProduct, patch: AmazonPatchOperation):
        # Implement offer updates here
        pass

    async def _update_fulfillment_availability(self, session: AsyncSession, product: AmazonProduct, patch: AmazonPatchOperation):
        # Implement fulfillment availability updates here
        pass

    async def delete_product(self, sku: str) -> AmazonDeleteRequest:
        async with self.get_db() as session:
            stmt = select(AmazonProduct).filter(AmazonProduct.sku == sku)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product with SKU {sku} not found")

            delete_req = AmazonDeleteRequest(
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