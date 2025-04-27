"""
Amazon Client for better workflow management and error handling
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, TypedDict, Union, Tuple
from datetime import datetime, timezone
from sp_api.base import Marketplaces, ReportType
from sp_api.api import (
    ProductTypeDefinitions,
    ListingsItems,
    ReportsV2,
    CatalogItems,
    DataKiosk
)
from sp_api.api.catalog_items.catalog_items import CatalogItemsVersion
from core.exceptions import APIError
from core.logger import logger
from .base_client import BaseAPIClient

class ProductFeatures(TypedDict):
    """Type definition for product features"""
    thickness: Union[int, str]
    size_match: List[Union[int, float]]
    feature: Optional[str]
    shape: str

class ProductAttribute(TypedDict):
    """Type definition for product attributes"""
    attributeName: str
    attributeValue: Any

class AmazonConfig:
    """Configuration class for Amazon client"""
    def __init__(self):
        self.marketplace_id = os.getenv("AMAZONTURKEYMARKETID")
        self.seller_id = os.getenv("AMAZONSELLERACCOUNTID")
        self.client_id = os.getenv("LWA_APP_ID")
        self.client_secret = os.getenv("LWA_CLIENT_SECRET")
        self.refresh_token = os.getenv("SP_API_REFRESH_TOKEN")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY")
        self.aws_secret_key = os.getenv("AWS_SECRET_KEY")
        self.region = os.getenv("AWS_REGION", "eu-west-1")

class AmazonClient(BaseAPIClient):
    """Enhanced Amazon Selling Partner API client"""
    
    def __init__(self):
        super().__init__()
        self.config = AmazonConfig()
        self.marketplace = Marketplaces.TR
        self.setup_credentials()
        self.setup_api_clients()
        
    def setup_credentials(self) -> None:
        """Setup API credentials"""
        self.credentials = {
            "refresh_token": self.config.refresh_token,
            "lwa_app_id": self.config.client_id,
            "lwa_client_secret": self.config.client_secret,
            "aws_access_key": self.config.aws_access_key,
            "aws_secret_key": self.config.aws_secret_key,
            "region": self.config.region
        }

    def setup_api_clients(self) -> None:
        """Initialize API clients"""
        self.catalog_api = CatalogItems(credentials=self.credentials)
        self.listings_api = ListingsItems(credentials=self.credentials)
        self.reports_api = ReportsV2(credentials=self.credentials)
        self.product_types_api = ProductTypeDefinitions(credentials=self.credentials)

    async def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from Amazon
        
        Args:
            **kwargs: Additional parameters for filtering
            
        Returns:
            List[Dict[str, Any]]: List of products
        """
        try:
            # Get inventory report
            report = await self.get_inventory_report()
            
            # Process report data
            products = await self.process_report_data(report)
            
            # Enrich with catalog data
            if kwargs.get('include_catalog_data', True):
                products = await self.enrich_with_catalog_data(products)
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to fetch products: {str(e)}")
            raise APIError(f"Failed to fetch products: {str(e)}")

    async def get_inventory_report(self) -> Dict[str, Any]:
        """Get inventory report from Amazon"""
        try:
            # Create report request
            report_response = self.reports_api.create_report(
                reportType=ReportType.GET_MERCHANT_LISTINGS_ALL_DATA,
                marketplaceIds=[self.config.marketplace_id]
            )
            
            report_id = report_response.payload['reportId']
            
            # Wait for report completion
            while True:
                status = self.reports_api.get_report(reportId=report_id)
                if status.payload['processingStatus'] == 'DONE':
                    break
                elif status.payload['processingStatus'] == 'CANCELLED':
                    raise APIError("Report generation was cancelled")
                await asyncio.sleep(5)
            
            # Get report document
            document = self.reports_api.get_report_document(
                reportDocumentId=status.payload['reportDocumentId'],
                decrypt=True
            )
            
            return document.payload
            
        except Exception as e:
            logger.error(f"Failed to get inventory report: {str(e)}")
            raise APIError(f"Failed to get inventory report: {str(e)}")

    async def process_report_data(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process inventory report data"""
        try:
            products = []
            for item in report.get('data', []):
                product = {
                    'sku': item.get('seller-sku'),
                    'data': {
                        'title': item.get('item-name'),
                        'price': float(item.get('price', 0)),
                        'quantity': int(item.get('quantity', 0)),
                        'asin': item.get('asin'),
                        'status': item.get('status'),
                        'fulfillment': item.get('fulfillment-channel')
                    }
                }
                products.append(product)
            return products
            
        except Exception as e:
            logger.error(f"Failed to process report data: {str(e)}")
            raise APIError(f"Failed to process report data: {str(e)}")

    async def enrich_with_catalog_data(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich products with catalog data"""
        try:
            for product in products:
                if asin := product['data'].get('asin'):
                    catalog_data = self.catalog_api.get_catalog_item(
                        asin=asin,
                        marketplaceIds=[self.config.marketplace_id],
                        includedData=['attributes', 'images', 'productTypes']
                    )
                    
                    if catalog_data.payload:
                        product['data'].update({
                            'brand': catalog_data.payload.get('brand'),
                            'category': catalog_data.payload.get('productType'),
                            'images': catalog_data.payload.get('images', []),
                            'attributes': catalog_data.payload.get('attributes', {})
                        })
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to enrich with catalog data: {str(e)}")
            raise APIError(f"Failed to enrich with catalog data: {str(e)}")

    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product on Amazon
        
        Args:
            product_data: Product data to update
            
        Returns:
            Dict[str, Any]: Updated product data
        """
        try:
            sku = product_data['sku']
            
            # Prepare update payload
            payload = self.prepare_update_payload(product_data)
            
            # Submit update
            response = self.listings_api.put_listings_item(
                sellerId=self.config.seller_id,
                sku=sku,
                marketplaceIds=[self.config.marketplace_id],
                body=payload
            )
            
            if response.payload['status'] == 'ACCEPTED':
                logger.info(f"Successfully updated product {sku}")
                return product_data
            else:
                raise APIError(f"Failed to update product {sku}: {response.payload}")
                
        except Exception as e:
            logger.error(f"Failed to update product: {str(e)}")
            raise APIError(f"Failed to update product: {str(e)}")

    def prepare_update_payload(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for product update"""
        try:
            data = product_data['data']
            
            payload = {
                "productType": data.get('category', 'HOME'),
                "patches": [
                    {
                        "op": "replace",
                        "path": "/attributes/fulfillment_availability",
                        "value": [{
                            "fulfillment_channel_code": "DEFAULT",
                            "quantity": data['quantity']
                        }]
                    },
                    {
                        "op": "replace",
                        "path": "/attributes/purchasable_offer",
                        "value": [{
                            "our_price": [{
                                "schedule": [{
                                    "value_with_tax": data['price']
                                }]
                            }]
                        }]
                    }
                ]
            }
            
            # Add optional updates if provided
            if 'title' in data:
                payload['patches'].append({
                    "op": "replace",
                    "path": "/attributes/title",
                    "value": [{"value": data['title']}]
                })
                
            if 'brand' in data:
                payload['patches'].append({
                    "op": "replace",
                    "path": "/attributes/brand",
                    "value": [{"value": data['brand']}]
                })
                
            return payload
            
        except Exception as e:
            logger.error(f"Failed to prepare update payload: {str(e)}")
            raise APIError(f"Failed to prepare update payload: {str(e)}")

    async def bulk_update_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update multiple products
        
        Args:
            products: List of products to update
            
        Returns:
            Dict[str, Any]: Update results
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        for product in products:
            try:
                await self.update_product(product)
                results['successful'].append(product['sku'])
            except Exception as e:
                logger.error(f"Failed to update product {product['sku']}: {str(e)}")
                results['failed'].append({
                    'sku': product['sku'],
                    'error': str(e)
                })
        
        return results

    async def get_product_types(self, category_name: str) -> List[Dict[str, Any]]:
        """Get available product types for category"""
        try:
            response = self.product_types_api.search_definitions_product_types(
                keywords=category_name,
                marketplaceIds=[self.config.marketplace_id]
            )
            return response.payload['productTypes']
            
        except Exception as e:
            logger.error(f"Failed to get product types: {str(e)}")
            raise APIError(f"Failed to get product types: {str(e)}")

    async def get_product_attributes(self, product_type: str) -> Dict[str, Any]:
        """Get required attributes for product type"""
        try:
            response = self.product_types_api.get_definitions_product_type(
                productType=product_type,
                marketplaceIds=[self.config.marketplace_id],
                sellerId=self.config.seller_id
            )
            return response.payload['schema']
            
        except Exception as e:
            logger.error(f"Failed to get product attributes: {str(e)}")
            raise APIError(f"Failed to get product attributes: {str(e)}")

    def validate_product_data(self, product_data: Dict[str, Any], 
                            product_type: str) -> List[str]:
        """Validate product data against required attributes"""
        errors = []
        
        try:
            # Get required attributes
            attributes = self.get_product_attributes(product_type)
            required = attributes.get('required', [])
            
            # Check required fields
            for field in required:
                if field not in product_data['data']:
                    errors.append(f"Missing required field: {field}")
            
            return errors
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            raise APIError(f"Validation failed: {str(e)}")
