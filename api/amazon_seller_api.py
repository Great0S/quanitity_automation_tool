""" importing necessary modules and libraries for performing various
 tasks related to handling data, making HTTP requests, and working with concurrency """

import asyncio
import os
import json
from pathlib import Path
import time
import logging
import re
import textwrap
from dotenv import load_dotenv
import requests
import io
import csv
from glob import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Dict, List, Any, Optional, TypedDict, Union, Tuple
from datetime import datetime, timezone
from sp_api.base import Marketplaces, ReportType
from sp_api.api import ProductTypeDefinitions, ListingsItems, ReportsV2, CatalogItems, ProductTypeDefinitions, ListingsItems, DataKiosk
from sp_api.api.catalog_items.catalog_items import CatalogItemsVersion
from urllib3 import Retry
from app.config.logging_init import logger

# Type definitions
class ProductFeatures(TypedDict):
    thickness: Union[int, str]
    size_match: List[Union[int, float]]
    feature: Optional[str]
    shape: str

class ProductAttribute(TypedDict):
    attributeName: str
    attributeValue: Any

@dataclass
class ListingReport:
    """Data class for storing listing report information."""
    report_id: str
    document_id: str
    status: str
    data: Optional[List[Dict[str, Any]]] = None

@dataclass
class ProductData(TypedDict):
    title: str
    brand: str
    description: str
    images: List[Dict[str, str]]
    attributes: List[ProductAttribute]
    quantity: int
    listPrice: float
    salePrice: float
    productMainId: str
    stockCode: str
    categoryName: str
    catalog_data: Optional[Dict[str, Any]] = None
    inventory_data: Optional[Dict[str, Any]] = None
    pricing_data: Optional[Dict[str, Any]] = None

@dataclass
class AmazonConfig:
    marketplace_id: str
    seller_id: str

class ListingFetchError(Exception):
    """Custom exception for listing fetch errors."""
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"Error fetching listings: {message}")

class RetryHandler:
    """Handles retry logic with exponential backoff."""
    
    @staticmethod
    def retry_with_backoff(func: callable, *args, retries: int = 5, **kwargs) -> Any:
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
                attempt += 1
        raise Exception(f"All {retries} retries failed for function {func.__name__}")

class AttributeManager:
    """Handles attribute-related operations for Amazon listings."""
    
    @staticmethod
    def extract_attributes(attributes: List[ProductAttribute]) -> Dict[str, Any]:
        """Extracts and processes product attributes."""
        default_attrs = {
            "size_match": [1, 1],
            "size": 1,
            "color": None,
            "feature": None,
            "material": "N/A",
            "style": None,
            "thickness": 1,
            "shape": "Dikdörtgen"
        }
        
        attr_patterns = {
            r"Boyut/Ebat|Beden": lambda v: ("size", "size_match", v),
            r"Renk|Color": lambda v: ("color", v),
            r"Özellik": lambda v: ("feature", v),
            r"Materyal": lambda v: ("material", v),
            r"Tema": lambda v: ("style", v),
            r"Hav Yüksekliği": lambda v: ("thickness", re.search(r"\d+", v).group() if re.search(r"\d+", v) else 1),
            r"Şekil": lambda v: ("shape", v)
        }
        
        for attr in attributes:
            attr_name = attr["attributeName"]
            attr_value = attr["attributeValue"]
            
            for pattern, processor in attr_patterns.items():
                if re.search(pattern, attr_name):
                    result = processor(attr_value)
                    if len(result) == 3:  # Special case for size
                        if isinstance(attr_value, (int, float)):
                            default_attrs[result[0]] = attr_value
                            default_attrs[result[1]] = str(attr_value).split("x")
                    else:
                        default_attrs[result[0]] = result[1]
                    break
                    
        return default_attrs

class CategoryManager:
    """Manages category-related operations for Amazon listings."""
    
    def __init__(self, config: AmazonConfig):
        self.config = config
        self.retry = RetryHandler.retry_with_backoff
        
    def fetch_category_attributes(self, category_name: str) -> tuple:
        """Fetches category-specific attributes."""
        product_definitions = self._get_product_definitions(category_name)
        product_type = product_definitions.payload["productTypes"][0]["name"]
        
        product_attrs = self.retry(
            ProductTypeDefinitions().get_definitions_product_type,
            productType=product_type,
            marketplaceIds=self.config.marketplace_id,
            requirements="LISTING",
            locale="tr_TR",
        )
        
        return self._download_attribute_schema(product_attrs.payload)
    
    def _get_product_definitions(self, category_name: str):
        """Gets product definitions, falling back to default if necessary."""
        while True:
            definitions = self.retry(
                ProductTypeDefinitions().search_definitions_product_types,
                itemName=category_name,
                marketplaceIds=self.config.marketplace_id,
                searchLocale="tr_TR",
                locale="tr_TR",
            )
            
            if len(definitions.payload['productTypes']) > 0:
                return definitions
                
            logging.warning(f"Product type {category_name} not found, using default type.")
            return self.retry(
                ProductTypeDefinitions().search_definitions_product_types,
                itemName='Halı',
                marketplaceIds=self.config.marketplace_id,
                searchLocale="tr_TR",
                locale="tr_TR",
            )
    
    def _download_attribute_schema(self, raw_category_attrs: Dict) -> tuple:
        """Downloads and caches the attribute schema."""
        file_path = f'amazon_{raw_category_attrs["productType"]}_attrs.json'
        
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                return raw_category_attrs, json.load(file)
        
        product_scheme = requests.get(raw_category_attrs["schema"]["link"]["resource"])
        scheme_json = product_scheme.json()
        category_attrs = self._extract_category_item_attrs(scheme_json, raw_category_attrs["productType"])
        
        with open(file_path, 'w') as file:
            json.dump(category_attrs, file)
            
        return raw_category_attrs, category_attrs
    
    def _extract_category_item_attrs(self, file_data: Dict, file_name: str = "") -> Dict:
        """Extracts category item attributes from schema."""
        def process_property_details(property_details: Dict) -> Any:
            if "examples" in property_details:
                return property_details.get("examples", [None])[0]
            if "items" in property_details:
                nested_items = property_details["items"]
                nested_properties = nested_items.get("properties", {})
                return {
                    required: nested_properties.get(required, {}).get("examples", [None])[0]
                    for required in nested_items.get("required", [])
                }
            if "properties" in property_details:
                return {
                    inner_property: process_property_details(inner_details)
                    for inner_property, inner_details in property_details["properties"].items()
                }
            return {}

        processed_attrs = {}
        properties = file_data.get("properties", {})

        for attribute_name, attribute_details in properties.items():
            attribute_type = attribute_details.get("type")
            processed_attr = process_property_details(attribute_details)
            processed_attrs[attribute_name] = [processed_attr] if attribute_type == "array" else processed_attr

        with open(f"amazon_{file_name}_attrs.json", "w", encoding="utf-8") as attrFile:
            json.dump(processed_attrs, attrFile, indent=4)

        return processed_attrs
        
class PayloadBuilder:
    """Builds payloads for Amazon listing operations."""
    
    @staticmethod
    def build_image_payload(images: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Builds the image payload structure."""
        product_images = {}
        for i, image in enumerate(images):
            key = "main_product_image_locator" if i == 0 else f"other_product_image_locator_{i}"
            product_images[key] = [{"media_location": image["url"]}]
        return product_images
    
    @staticmethod
    def build_bullet_points(description: str) -> List[Dict[str, str]]:
        """Builds bullet points from product description."""
        if not description:
            return [{'value': ''}]
        bullet_points_list = textwrap.wrap(description, width=len(description) // 5)
        return [{"value": bullet_point} for bullet_point in bullet_points_list]

class AmazonListingManager:
    """Main class for managing Amazon listings."""
   
    def __init__(self):
        self.config = AmazonConfig(
            marketplace_id=os.environ.get("AMAZONTURKEYMARKETID"),
            seller_id=os.environ.get("AMAZONSELLERACCOUNTID")
        )
        self.category_manager = CategoryManager(self.config)
        self.retry = RetryHandler.retry_with_backoff
        self.attribute_manager = AttributeManager()
        self.payload_builder = PayloadBuilder()

        # Load environment variables from .env file
        env_path = Path('.') / '.env'
        load_dotenv(dotenv_path=env_path)

        # DATA KIOSK API
        self.client = DataKiosk()
        self.client_id = os.environ.get("LWA_APP_ID")
        self.client_secret = os.environ.get("LWA_CLIENT_SECRET")
        self.refresh_token = os.environ.get("SP_API_REFRESH_TOKEN")
        self.marketplace_id = os.environ.get("AMAZONTURKEYMARKETID")
        self.amazon_sa_id = os.environ.get("AMAZONSELLERACCOUNTID")
        self.credentials = {
            "refresh_token": self.refresh_token,
            "lwa_app_id": self.client_id,
            "lwa_client_secret": self.client_secret,
        }
        self.session = requests.session()
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 300  # 5 minutes timeout for report generation
        self.chunk_size = 20
        self.max_workers = 5

    def get_access_token(self):
        """
        The function `get_access_token` retrieves an access token by sending a POST request to a specified
        URL with necessary parameters.
        :return: The function `get_access_token` is returning the access token obtained from the API
        response after making a POST request to the token URL with the provided payload containing the
        client ID, client secret, and refresh token.
        """
        token_url = "https://api.amazon.com/auth/o2/token"
        payload = f"grant_type=refresh_token&client_id={self.client_id}&client_secret={self.client_secret}&refresh_token={self.refresh_token}"
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}
        token_response = requests.request(
            "POST", token_url, headers=headers, data=payload, timeout=300
        )
        response_content = json.loads(token_response.text)
        access_token_data = response_content["access_token"]
        return access_token_data

    def request_data(
        self,
        session_data=None,
        operation_uri="",
        params: dict = None,
        payload=None,
        method="GET",
        url=None,
    ):
        """
        The function `request_data` sends a request to a specified API endpoint with optional parameters and
        handles various response scenarios.
        """
        endpoint_url = f"https://sellingpartnerapi-eu.amazon.com{operation_uri}?"
        request_url = ""
        if params:
            uri = "&".join([f"{k}={params[k]}" for k, v in params.items()])
        else:
            uri = ""
        if url:
            request_url = url
        else:
            request_url = endpoint_url + uri
        # Get the current time
        current_time = datetime.now(timezone.utc)
        # Format the time in the desired format
        formatted_time = current_time.strftime("%Y%m%dT%H%M%SZ")
        access_token = self.get_access_token()
        headers = {
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "x-amz-access-token": f"{access_token}",
            "x-amz-date": formatted_time,
        }
        while True:
            if session_data:
                session_data.headers = headers
                try:
                    init_request = session_data.get(f"{request_url}", data=payload)
                except ConnectionError:
                    logger.error(
                        "Amazon request had a ConnectionError, sleeping for 5 seconds!"
                    )
                    time.sleep(5)
            else:
                init_request = requests.request(
                    method, f"{request_url}", headers=headers, data=payload, timeout=30
                )
            if init_request.status_code in (200, 400):
                if init_request.text:
                    jsonify = json.loads(init_request.text)
                else:
                    logger.error("SP-API Has encountred an error. Try again later!")
                    jsonify = None
                return jsonify
            if init_request.status_code == 403:
                session_data.headers["x-amz-access-token"] = access_token
            elif init_request.status_code == 429:
                time.sleep(65)
            else:
                error_message = json.loads(init_request.text)["errors"][0]["message"]
                if re.search("not found", error_message):
                    return None
                else:
                    logger.error(f"An error has occured || {error_message}")
                    return None
        
    def build_payload(self, product_data: ProductData) -> Dict:
        """Builds the complete payload for Amazon listing."""
        bullet_points = self.payload_builder.build_bullet_points(product_data["description"])
        product_images = self.payload_builder.build_image_payload(product_data["images"])
        attributes = self.attribute_manager.extract_attributes(product_data["attributes"])
        
        product_type = self._determine_product_type(product_data['categoryName'])
        raw_category_attrs, category_attrs = self.category_manager.fetch_category_attributes(product_type)
        
        base_payload = self._build_base_payload(product_data, bullet_points, product_images, attributes)
        specific_attrs = self._get_category_specific_attrs(raw_category_attrs["productType"], product_data, attributes)
        
        base_payload["attributes"].update(specific_attrs)
        self._apply_special_rules(base_payload, raw_category_attrs["productType"])
        
        return base_payload
    
    def process_product_images(self, images: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Process and format product images for Amazon listing."""
        product_images = {}
        
        for idx, image in enumerate(images):
            if idx == 0:
                product_images["main_product_image_locator"] = [
                    {"media_location": image["url"]}
                ]
            else:
                product_images[f"other_product_image_locator_{idx}"] = [
                    {"media_location": image["url"]}
                ]
        
        return product_images

    def extract_product_attributes(self, source_attrs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and process product attributes from source data."""
        attrs = {
            'size': 1,
            'size_match': [1, 1],
            'color': None,
            'feature': None,
            'material': None,
            'style': None,
            'thickness': 1,
            'shape': 'Dikdörtgen'
        }

        for attr in source_attrs:
            attr_name = attr["attributeName"]
            attr_value = attr["attributeValue"]

            if re.search("Boyut/Ebat|Beden", attr_name):
                if isinstance(attr_value, (int, float)):
                    attrs['size'] = attr_value
                    attrs['size_match'] = str(attr_value).split('x')

            elif re.search(r"Renk|Color", attr_name):
                attrs['color'] = attr_value

            elif re.search("Özellik", attr_name):
                attrs['feature'] = attr_value

            elif re.search("Materyal", attr_name):
                attrs['material'] = attr_value

            elif re.search("Tema", attr_name):
                attrs['style'] = attr_value

            elif re.search("Hav Yüksekliği", attr_name):
                thickness = attr_value
                match = re.search(r"\d+", thickness)
                attrs['thickness'] = match.group() if match else 1

            elif re.search("Şekil", attr_name):
                attrs['shape'] = attr_value

        return attrs

    @Retry
    def get_product_definitions(self, category_name: str) -> Dict[str, Any]:
        """Get product type definitions from Amazon."""
        product_definitions = ProductTypeDefinitions().search_definitions_product_types(
            itemName=category_name,
            marketplaceIds=[self.marketplace_id],
            searchLocale="tr_TR",
            locale="tr_TR",
        )
        
        if not product_definitions.payload['productTypes']:
            raise ValueError(f"No product types found for category: {category_name}")
            
        return product_definitions.payload["productTypes"][0]

    def build_base_payload(self, product_data: Dict[str, Any], product_type: str, 
                          attrs: Dict[str, Any], images: Dict[str, List[Dict[str, str]]]) -> Dict[str, Any]:
        """Build the base payload for product listing."""
        bullet_points = [
            {"value": point} for point in textwrap.wrap(
                product_data["description"], 
                width=len(product_data["description"]) // 5
            )
        ]

        payload = {
            "productType": product_type,
            "requirements": "LISTING",
            "attributes": {
                "item_name": [{"value": product_data["title"]}],
                "brand": [{"value": product_data["brand"]}],
                "bullet_point": bullet_points,
                "condition_type": [{"value": "new_new"}],
                "fulfillment_availability": [{
                    "fulfillment_channel_code": "DEFAULT",
                    "quantity": product_data["quantity"],
                    "lead_time_to_ship_max_days": "5"
                }],
                "color": [{"value": attrs['color']}],
                "size": [{"value": attrs['size']}],
                "style": [{"value": attrs['style']}],
                # ... other base attributes ...
            }
        }
        
        # Add images to payload
        payload["attributes"].update(images)
        
        return payload

    def add_category_specific_attributes(self, payload: Dict[str, Any], 
                                       product_type: str, attrs: Dict[str, Any], 
                                       product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add category-specific attributes to the payload."""
        category_attrs = {
            "RUG": {
                "product_site_launch_date": [
                    {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
                ],
                "item_dimensions": [{
                    "length": {"value": attrs['thickness'], "unit": "millimeters"},
                    "width": {"value": attrs['size_match'][1], "unit": "centimeters"},
                    "height": {"value": attrs['size_match'][0], "unit": "centimeters"}
                }],
                # ... other RUG specific attributes ...
            },
            "LITTER_BOX": {
                # ... LITTER_BOX specific attributes ...
            },
            # ... other categories ...
        }

        if product_type in category_attrs:
            payload["attributes"].update(category_attrs[product_type])

        return payload

    def _handle_api_error(self, operation: str, error: Exception) -> None:
        """Handle API errors with proper logging and potential recovery actions."""
        error_msg = f"Error during {operation}: {str(error)}"
        logger.error(error_msg)
        
        if "Rate exceeded" in str(error):
            logger.info("Rate limit exceeded, implementing exponential backoff")
            time.sleep(self.retry_delay)
            self.retry_delay *= 2
        elif "Token expired" in str(error):
            logger.info("Token expired, refreshing credentials")
            self._refresh_credentials()
        
        raise ListingFetchError(error_msg)

    async def _refresh_credentials(self) -> None:
        """Refresh API credentials."""
        try:
            # Implement credential refresh logic here
            pass
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {str(e)}")
            raise

    @staticmethod
    def validate_report_data(report_data: List[Dict[str, Any]]) -> bool:
        """Validate report data structure and content."""
        required_fields = {"product-id", "seller-sku", "listing-id", "quantity", "price"}
        
        if not report_data:
            return False
            
        return all(
            all(field in item for field in required_fields)
            for item in report_data
        )

    async def get_report_async(self, report_type: str) -> ListingReport:
        """Asynchronously create and retrieve a report."""
        try:
            # Create report request
            report_request = self.retry(
                lambda: ReportsV2().create_report(
                    reportType=report_type,
                    marketplaceIds=[self.marketplace_id],
                )
            )
            
            report_id = report_request.payload["reportId"]
            start_time = time.time()
            
            # Wait for report completion
            while time.time() - start_time < self.timeout:
                report_status = self.retry(
                    lambda: ReportsV2().get_report(reportId=report_id)
                )
                
                if report_status.payload["processingStatus"] == "DONE":
                    return ListingReport(
                        report_id=report_id,
                        document_id=report_status.payload["reportDocumentId"],
                        status="DONE"
                    )
                    
                elif report_status.payload["processingStatus"] == "CANCELLED":
                    raise ListingFetchError("Report generation was cancelled")
                
                await asyncio.sleep(30)
            
            raise ListingFetchError("Report generation timed out")
            
        except Exception as e:
            self._handle_api_error("report generation", e)

    def process_report_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process the report document and extract relevant data."""
        try:
            report_string = document.payload["document"]
            if report_string.startswith("\ufeff"):
                report_string = report_string[1:]

            report_file = io.StringIO(report_string)
            report_data = list(csv.DictReader(report_file, delimiter="\t"))
            
            if not self.validate_report_data(report_data):
                raise ListingFetchError("Invalid report data structure")
                
            return report_data
            
        except Exception as e:
            self._handle_api_error("report processing", e)

    def process_product_data(self, raw_data: Dict[str, Any]) -> ProductData:
        """Process raw product data into structured format."""
        try:
            basic_info = {
                "id": raw_data["product-id"],
                "sku": raw_data["seller-sku"],
                "listing_id": raw_data["listing-id"],
                "quantity": int(raw_data["quantity"]),
                "price": float(raw_data['price']) if raw_data['price'] else 0,
                "status": raw_data.get("status", "ACTIVE"),
                "condition": raw_data.get("item-condition", "NEW"),
                "last_updated": datetime.now().isoformat()
            }
            
            # return ProductData(basic_info=basic_info)
            return basic_info
            
        except Exception as e:
            logger.error(f"Error processing product data: {str(e)}")
            return None

    async def fetch_catalog_data_batch(self, skus: List[str]) -> List[Dict[str, Any]]:
        """Fetch catalog data for a batch of SKUs."""
        try:
            catalog_item = CatalogItems()
            catalog_item.version = CatalogItemsVersion.V_2022_04_01
            
            sku_string = ",".join(skus)
            response = await self.retry(
                lambda: catalog_item.search_catalog_items(
                    marketplaceIds=[self.marketplace_id],
                    includedData="attributes,identifiers,images,productTypes,summaries,relationships,dimensions,salesRanks",
                    locale="tr_TR",
                    sellerId=self.amazon_sa_id,
                    identifiersType="SKU",
                    identifiers=sku_string,
                    pageSize=len(skus),
                )
            )
            
            return response.payload.get("items", [])
            
        except Exception as e:
            self._handle_api_error(f"catalog data fetch for SKUs {sku_string}", e)
            return []

    def get_listings(self, 
                          every_product: bool = False,
                          include_inventory: bool = False,
                          include_pricing: bool = False,
                          status_filter: Optional[List[str]] = None) -> List[ProductData]:
        """
        Enhanced method to retrieve Amazon listings with various options and filters.
        
        Args:
            every_product (bool): Fetch detailed catalog data for each product
            include_inventory (bool): Include current inventory levels
            include_pricing (bool): Include current pricing information
            status_filter (List[str]): Filter products by status (e.g., ['ACTIVE', 'INACTIVE'])
            
        Returns:
            List[ProductData]: List of processed product data
        """
        try:
            # Get basic report
            report = asyncio.run(self.get_report_async(ReportType.GET_MERCHANT_LISTINGS_ALL_DATA))
            report_document = self.retry(
                lambda: ReportsV2().get_report_document(
                    reportDocumentId=report.document_id,
                    download=True,
                    decrypt=True,
                )
            )
            
            # Process report data
            raw_data = self.process_report_document(report_document)
            
            # Filter by status if needed
            if status_filter:
                raw_data = [
                    item for item in raw_data 
                    if item.get("status", "ACTIVE") in status_filter
                ]
            
            # Process basic product data
            products = [
                self.process_product_data(item) 
                for item in raw_data 
                if not re.search(r"\_fba", item["seller-sku"])
            ]
            
            if not every_product:
                return products
            
            # Get SKUs for detailed data
            skus = [p["sku"] for p in products if p]
            
            # Fetch detailed data in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Split SKUs into chunks
                sku_chunks = list(self.chunk_list(skus, self.chunk_size))
                
                # Create tasks for parallel execution
                tasks = []
                
                # Catalog data tasks
                if every_product:
                    tasks.extend([
                        executor.submit(self.fetch_catalog_data_batch, chunk)
                        for chunk in sku_chunks
                    ])
                
                # Inventory data tasks
                if include_inventory:
                    tasks.extend([
                        executor.submit(self.fetch_inventory_data_batch, chunk)
                        for chunk in sku_chunks
                    ])
                
                # Pricing data tasks
                if include_pricing:
                    tasks.extend([
                        executor.submit(self.fetch_pricing_data_batch, chunk)
                        for chunk in sku_chunks
                    ])
                
                # Wait for all tasks to complete
                results = {}
                for future in as_completed(tasks):
                    try:
                        data = future.result()
                        results.update(data)
                    except Exception as e:
                        logger.error(f"Error in parallel execution: {str(e)}")
            
            # Merge all data
            self.merge_product_data(products, results)
            
            logger.info(f"Successfully fetched {len(products)} products with detailed data")
            return products
            
        except Exception as e:
            self._handle_api_error("listing retrieval", e)
            return []

    def merge_product_data(self, products: List[ProductData], 
                          additional_data: Dict[str, Any]) -> None:
        """Merge additional data into product objects."""
        for product in products:
            if not product:
                continue
                
            sku = product.basic_info["sku"]
            
            # Merge catalog data
            if "catalog" in additional_data and sku in additional_data["catalog"]:
                product.catalog_data = additional_data["catalog"][sku]
            
            # Merge inventory data
            if "inventory" in additional_data and sku in additional_data["inventory"]:
                product.inventory_data = additional_data["inventory"][sku]
            
            # Merge pricing data
            if "pricing" in additional_data and sku in additional_data["pricing"]:
                product.pricing_data = additional_data["pricing"][sku]

    def export_listings(self, products: List[ProductData], 
                       format: str = "json",
                       file_path: Optional[str] = None) -> Optional[str]:
        """
        Export listings data to various formats.
        
        Args:
            products: List of product data to export
            format: Export format ('json', 'csv', or 'excel')
            file_path: Optional path to save the file
            
        Returns:
            str: Path to the exported file if file_path is provided
        """
        try:
            if format == "json":
                data = [asdict(p) for p in products if p]
                if file_path:
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                return data
            
            elif format == "csv":
                # Implement CSV export
                pass
            
            elif format == "excel":
                # Implement Excel export
                pass
                
        except Exception as e:
            logger.error(f"Error exporting listings: {str(e)}")
            return None

    @Retry
    def add_listing(self, data: Dict[str, Any]) -> None:
        """Create a new product listing on Amazon."""
        for _, data_items in data.items():
            for product in data_items:
                try:
                    product_data = product["data"]
                    product_sku = product_data['stockCode']
                    
                    # Process images and attributes
                    images = self.process_product_images(product_data["images"])
                    attrs = self.extract_product_attributes(product_data["attributes"])
                    
                    # Get product definitions
                    product_def = self.get_product_definitions(product_data["categoryName"])
                    product_type = product_def["name"]
                    
                    # Build payload
                    payload = self.build_base_payload(product_data, product_type, attrs, images)
                    payload = self.add_category_specific_attributes(payload, product_type, attrs, product_data)
                    
                    # Create listing
                    response = ListingsItems().put_listings_item(
                        sellerId=self.amazon_sa_id,
                        sku=product_sku,
                        marketplaceIds=[self.marketplace_id],
                        body=payload
                    )
                    
                    if response and response.payload["status"] == "ACCEPTED":
                        logger.info(f"New product added with code: {product_sku}, qty: {product_data['quantity']}")
                    else:
                        logger.error(f"New product with code: {product_sku} creation has failed || Reason: {response}")
                        
                except Exception as e:
                    logger.error(f"Error creating listing for SKU {product_sku}: {str(e)}")
                    continue
    
    def update_listing(self, product_data: Dict[str, Any]) -> None:
        """Updates an existing Amazon listing."""
        try:
            payload = self._build_update_payload(product_data)
            response = self._submit_update(sku=product_data["sku"], payload=payload)
            
            if response and response.payload["status"] == "ACCEPTED":
                logger.info(f"Product with code: {response.payload['sku']}, new qty: {product_data['quantity']}")
            else:
                logger.error(f"Product with code: {response.payload['sku']} update has failed || Reason: {response.payload}")
        except Exception as e:
            logging.error(f"Failed to update product {product_data['sku']}: {e}", exc_info=True)
    
    def _determine_product_type(self, category_name: str) -> str:
        """Determines the product type based on category name."""
        if re.search(r"yapıştırıcısı", category_name, re.IGNORECASE):
            return 'Zemin Kaplamaları Yapıştırıcısı'
        elif category_name == 'Dikiş Makinesi Aksesuarı':
            return 'Dikiş İğnesi'
        return category_name
    
    def _submit_listing(self, product_sku: str, payload: Dict) -> None:
        """Submits a listing to Amazon."""
        listing_add_request = self.retry(
            func=ListingsItems().put_listings_item,
            sellerId=self.config.seller_id,
            sku=product_sku,
            marketplaceIds=self.config.marketplace_id,
            body=payload
        )
        
        if listing_add_request and listing_add_request.payload["status"] == "ACCEPTED":
            logging.info(f"New product added with code: {product_sku}, qty: {payload['attributes']['fulfillment_availability'][0]['quantity']}")
        else:
            logging.error(f"New product with code: {product_sku} creation has failed || Reason: {listing_add_request.payload['issues']}")
    
    def _submit_update(self, payload: Dict[str, Any], sku: str) -> None:
        """
        Submits an update to Amazon for a specific SKU.
        
        Args:
            payload (Dict[str, Any]): The update payload to submit
            sku (str): The SKU of the product to update
        
        Raises:
            Exception: If the update submission fails
        """
        try:
            response = ListingsItems().patch_listings_item(
                marketplaceIds=[self.config.marketplace_id],
                sellerId=self.config.seller_id,
                body=payload,
                sku=sku
            )
            
            if not response.payload['status'] == "ACCEPTED":
                raise Exception(f"Failed to update listing for SKU {sku}: {response.errors}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error updating listing for SKU {sku}: {str(e)}")
            raise

    def _build_update_payload(self, product_data: Dict[str, Any]) -> Dict:
        """Builds payload for updating an existing listing."""
        return {
            "productType": "HOME_BED_AND_BATH",
            "patches": [
                {
                    "op": "replace",
                    "path": "/attributes/fulfillment_availability",
                    "value": [{
                        "fulfillment_channel_code": "DEFAULT",
                        "quantity": product_data["quantity"],
                        "marketplace_id": "A33AVAJ2PDY3EV",
                    }]
                },
                {
                    "op": 'replace',
                    "path": '/attributes/purchasable_offer',
                    "value": [{
                        "purchasable_offer": [{
                            "currency": "TRY",
                            "our_price": [{
                                "schedule": [{
                                    "value_with_tax": product_data["price"]
                                }]
                            }],
                            "marketplace_id": 'A33AVAJ2PDY3EV'
                        }],
                    }]
                }
            ]
        }

# Example usage:
# if __name__ == "__main__":
#     # Initialize the manager
#     manager = AmazonListingManager()
    
#     # Example product data
#     product_data = {
#         "data": {
#             "title": "Example Product",
#             "brand": "Example Brand",
#             "description": "Product description",
#             "images": [{"url": "http://example.com/image.jpg"}],
#             "attributes": [],
#             "quantity": 10,
#             "listPrice": 99.99,
#             "salePrice": 89.99,
#             "productMainId": "123",
#             "stockCode": "ABC123",
#             "categoryName": "RUG"
#         }
#     }
    
#     # Add new listing
#     manager.add_listings([product_data])
    
#     # Update existing listing
#     update_data = {
#         "sku": "ABC123",
#         "quantity": 15,
#         "price": 94.99
#     }
#     manager.update_listing(update_data)
