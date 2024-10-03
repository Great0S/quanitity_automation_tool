""" importing necessary modules and libraries for performing various
 tasks related to handling data, making HTTP requests, and working with concurrency """

import textwrap
import json
import os
import re
import time
import requests
import asyncio
from typing import List, Dict, Any
from sp_api.api import DataKiosk
from sp_api.base import ReportType, SellingApiException
from sp_api.api import (
    ListingsItems,
    ProductTypeDefinitions,
    Catalog,
    ReportsV2,
    CatalogItems
)

from app.config import logger


# DATA KIOSK API
client = DataKiosk()


client_id = os.environ.get("LWA_APP_ID")
client_secret = os.environ.get("LWA_CLIENT_SECRET")
refresh_token = os.environ.get("SP_API_REFRESH_TOKEN")
MarketPlaceID = os.environ.get("AMAZONTURKEYMARKETID")
AmazonSA_ID = os.environ.get("AMAZONSELLERACCOUNTID")
credentials = {
    "refresh_token": refresh_token,
    "lwa_app_id": client_id,
    "lwa_client_secret": client_secret,
}




class AmazonListingManager:

    def __init__(self):
        self.marketplace_id = os.environ.get("AMAZONTURKEYMARKETID")
        self.seller_id = os.environ.get("AMAZONSELLERACCOUNTID")
        self.listings_api = ListingsItems()
        self.product_type_api = ProductTypeDefinitions()
        self.catalog_api = Catalog()
        self.reports_api = ReportsV2()
        self.catalog_items_api = CatalogItems(version="2022-04-01")
        self.locale = 'tr_TR' 
        
    def retry_with_backoff(self, func, *args, retries=5, **kwargs):
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
                attempt += 1
        raise Exception(f"All {retries} retries failed for function {func.__name__}")

    def fetch_category_attributes(self, category_name):
        product_definitions = self.retry_with_backoff(
            self.product_type_api.search_definitions_product_types,
            keywords=category_name,
            marketplaceIds=[self.marketplace_id],
            locale="tr_TR"
        )
        
        if not product_definitions.payload['productTypes']:
            raise ValueError(f"No product type found for category: {category_name}")

        product_type = product_definitions.payload["productTypes"][0]["name"]

        # Use the new get_categories method to fetch category information
        category_response = self.retry_with_backoff(
            self.catalog_api.get_categories,
            marketplaceId=self.marketplace_id,
            ASIN=product_type  # Assuming product_type can be used as an ASIN
        )

        if not category_response.payload or 'categories' not in category_response.payload:
            raise ValueError(f"No category information found for product type: {product_type}")

        # Use the first category in the response
        category = category_response.payload['categories'][0]

        # Fetch attributes for the category
        attributes_response = self.retry_with_backoff(
            self.catalog_api.get_item_attributes,
            asin=category['asin'],
            marketplaceId=self.marketplace_id,
            includedData=['attributes', 'dimensions', 'identifiers', 'relationships']
        )

        return self.download_attribute_schema(attributes_response.payload)

    def download_attribute_schema(self, raw_category_attrs):
        file_path = f'amazon_{raw_category_attrs["productType"]}_attrs.json'
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                return raw_category_attrs, json.load(file)
        else:
            product_scheme = requests.get(raw_category_attrs["schema"]["link"]["resource"])
            scheme_json = product_scheme.json()
            category_attrs = self.extract_category_item_attrs(scheme_json, raw_category_attrs["productType"])
            with open(file_path, 'w') as file:
                json.dump(category_attrs, file)
            return raw_category_attrs, category_attrs

    def extract_category_item_attrs(self, file_data, file_name=""):
        processed_attrs = {}
        properties = file_data.get("properties", {})

        def process_property_details(property_details):
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

        for attribute_name, attribute_details in properties.items():
            attribute_type = attribute_details.get("type")
            processed_attr = process_property_details(attribute_details)

            if attribute_type == "array":
                processed_attrs[attribute_name] = [processed_attr]
            else:
                processed_attrs[attribute_name] = processed_attr

        with open(f"amazon_{file_name}_attrs.json", "w", encoding="utf-8") as attrFile:
            json.dump(processed_attrs, attrFile, indent=4)

        return processed_attrs
    
    def extract_attributes(self, attributes):
        extracted = {
            "size": "1",
            "size_match": ["1", "1"],
            "color": None,
            "feature": None,
            "style": None,
            "material": None,
            "thickness": "1",
            "shape": "Dikdörtgen"
        }

        for attr in attributes:
            attr_name = attr["attributeName"].lower()
            attr_value = attr["attributeValue"]
            
            if "boyut" in attr_name or "ebat" in attr_name or "beden" in attr_name:
                extracted["size"] = str(attr_value)
                extracted["size_match"] = str(attr_value).split("x")
            elif "renk" in attr_name or "color" in attr_name:
                extracted["color"] = attr_value
            elif "özellik" in attr_name:
                extracted["feature"] = attr_value
            elif "materyal" in attr_name:
                extracted["material"] = attr_value
            elif "tema" in attr_name:
                extracted["style"] = attr_value
            elif "hav yüksekliği" in attr_name:
                match = re.search(r"\d+", attr_value)
                if match:
                    extracted["thickness"] = match.group()
            elif "şekil" in attr_name:
                extracted["shape"] = attr_value

        return extracted

    def build_image_payload(self, images):
        product_images = {}
        for i, image in enumerate(images):
            if i == 0:
                product_images["main_image_url"] = image["url"]
            else:
                product_images[f"other_image_url{i+1}"] = image["url"]
        return product_images
   
    def build_payload(self, product_data):
        bullet_points = textwrap.wrap(product_data["description"], width=500)[:5]
        product_images = self.build_image_payload(product_data["images"])
        attributes = self.extract_attributes(product_data["attributes"])
        
        raw_category_attrs, category_attrs = self.fetch_category_attributes(product_data["categoryName"])

        payload = {
            "productType": raw_category_attrs["productType"],
            "requirements": "LISTING",
            "attributes": {
                "item_name": [{"value": product_data["title"]}],
                "brand": [{"value": product_data["brand"]}],
                "supplier_declared_has_product_identifier_exemption": [{"value": True}],
                "recommended_browse_nodes": [{"value": "13028044031"}],
                "bullet_point": bullet_points,  
                "condition_type": [{"value": "new_new"}],  
                "fulfillment_availability": [{"fulfillment_channel_code": "DEFAULT","quantity": product_data["quantity"],"lead_time_to_ship_max_days": "5"}],
                "gift_options": [{"can_be_messaged": "false", "can_be_wrapped": "false"}], 
                "generic_keyword": [{"value": product_data["title"].split(" ")[0]}],
                "list_price": [{"currency": "TRY","value_with_tax": product_data["listPrice"],}],
                "manufacturer": [{"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti."}],
                "material": [{"value": self.attributes["material"]}],
                "model_number": [{"value": product_data["productMainId"]}],
                "number_of_items": [{"value": 1}], 
                "color": [{"value": self.attributes["color"]}],
                "size": [{"value": self.attributes["size"]}],
                "style": [{"value": self.attributes["style"]}],
                "part_number": [{"value": product_data["productMainId"]}],
                "pattern": [{"value": "Düz"}],
                "product_description": [{"value": product_data["description"]}],
                "purchasable_offer": [{"currency": "TRY","our_price": [{"schedule": [{"value_with_tax": product_data["salePrice"]}]}],}],
                "country_of_origin": [{"value": "TR"}],
                "package_level": [{"value": "unit"}],
                "customer_package_type": [{"value": "Standart Paketleme"}],
                **product_images,
            },
            "offers": [
                {
                    "offerType": "B2C",
                    "price": {"currency": "TRY", "currencyCode": "TRY", "amount": product_data["salePrice"]},
                }
            ],
        }

        # Add category-specific attributes
        payload["attributes"].update(category_attrs)

        return payload

    def submit_listing(self, product_sku, payload):
        try:
            response = self.retry_with_backoff(
                self.listings_api.put_listings_item,
                sellerId=self.seller_id,
                sku=product_sku,
                marketplaceIds=[self.marketplace_id],
                body=payload
            )
            if response.payload["status"] == "ACCEPTED":
                logger.info(f"New product added with SKU: {product_sku}")
            else:
                logger.error(f"Failed to add product with SKU: {product_sku}. Response: {response}")
        except Exception as e:
            logger.error(f"Error submitting listing for SKU {product_sku}: {str(e)}")

    def add_listings(self, product_data):
        for _, data_items in product_data.items():
            for product in data_items:
                product_data = product["data"]
                product_sku = product_data['stockCode']
                try:
                    payload = self.build_payload(product_data)
                    self.submit_listing(product_sku, payload)
                except Exception as e:
                    logger.error(f"Failed to process product {product_sku}: {e}", exc_info=True)

    def update_listing(self, product_data: dict):
        sku = product_data["sku"]    
        qty = product_data["qty"]
        
        patch = {
            "productType": "HOME_BED_AND_BATH",
            "patches": [
                {
                    "op": "replace",
                    "path": "/attributes/fulfillment_availability",
                    "value": [
                        {
                            "fulfillment_channel_code": "DEFAULT",
                            "quantity": qty,
                        }
                    ],
                }
            ],
        }

        try:
            response = self.retry_with_backoff(
                self.listings_api.patch_listings_item,
                sellerId=self.seller_id,
                sku=sku,
                marketplaceIds=[self.marketplace_id],
                body=patch
            )
            if response.payload["status"] == "ACCEPTED":
                logger.info(f"Updated product with SKU: {sku}, New quantity: {qty}")
            else:
                logger.error(f"Failed to update product with SKU: {sku}. Response: {response}")
        except Exception as e:
            logger.error(f"Error updating listing for SKU {sku}: {str(e)}")

    async def get_listings(self, load_all: bool = False) -> List[Dict[str, Any]]:
        report_data = await self._fetch_report()

        products = self._process_report_data(report_data)

        if load_all:
            products = await self._enrich_product_data(products)

        return products
    
    async def _fetch_report(self) -> List[Dict[str, str]]:
        try:
            report_request = self.reports_api.create_report(
                reportType=ReportType.GET_MERCHANT_LISTINGS_ALL_DATA,
                marketplaceIds=[self.marketplace_id],
            )
            report_id = report_request.payload["reportId"]

            while True:
                report_status = self.reports_api.get_report(reportId=report_id)
                if report_status.payload["processingStatus"] == "DONE":
                    break
                await asyncio.sleep(5)

            report_document = self.reports_api.get_report_document(
                reportDocumentId=report_status.payload["reportDocumentId"],
                download=True,
                decrypt=True,
            )
            report_string = report_document.payload["document"]
            # Remove BOM if present
            report_string = report_string.lstrip('\ufeff')
            lines = report_string.splitlines()
            headers = lines[0].split('\t')
            return [dict(zip(headers, line.split('\t'))) for line in lines[1:]]
        except SellingApiException as e:
            logger.error(f"Error fetching report: {str(e)}")
            raise

    def _process_report_data(self, report_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        return [
            {
                "id": item["product-id"],
                "sku": item["seller-sku"],
                "listing-id": item["listing-id"],
                "quantity": item["quantity"],
            }
            for item in report_data
            if not re.search(r"\_fba", item["seller-sku"])]

    async def _enrich_product_data(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async def fetch_catalog_data(sku_chunk):
            try:
                sku_strings = ",".join(sku_chunk)
                response = self.retry_with_backoff(
                    self.catalog_items_api.search_catalog_items,
                    marketplaceIds=[self.marketplace_id],
                    includedData="attributes,identifiers,images,productTypes,summaries",
                    locale=self.locale,
                    sellerId=self.seller_id,
                    identifiersType="SKU",
                    identifiers=sku_strings,
                    pageSize=20
                )
                return response.payload.get("items", [])
            except Exception as e:
                logger.error(f"Error fetching catalog data for SKUs {sku_chunk}: {str(e)}")
                return []

        async def process_chunk(sku_chunk):
            catalog_items = await fetch_catalog_data(sku_chunk)
            for item in catalog_items:
                sku = next((i['identifier'] for i in item['identifiers'][0]['identifiers'] if i['identifierType'] == 'SKU'), "None")
                if sku in [product['sku'] for product in products]:
                    pass
                else:
                    print(f"SKU {sku} not found in products")
                if sku:
                    product = next((p for p in products if p['sku'] == sku), {"sku": sku})
                    if product:
                        # Filter out language-specific data and convert lists to dicts
                        filtered_item = self._filter_and_convert_item(item)
                        if not filtered_item:
                            pass
                        else:
                            product.update(filtered_item)
                    else:
                        logger.warning(f"Product with SKU {sku} not found in catalog data")
                else:
                    logger.warning(f"Product with SKU {sku} not found in report data")

        sku_chunks = [list(chunk) for chunk in self._chunks([product['sku'] for product in products], 20)]
        await asyncio.gather(*[process_chunk(chunk) for chunk in sku_chunks])
        return products

    @staticmethod
    def _chunks(iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    def _filter_and_convert_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        filtered_item = {}
        for key, value in item.items():
            if key == 'attributes':
                filtered_item[key] = self._process_attributes(value)
            elif key in ['images', 'productTypes','summaries']:
                filtered_item[key] = self._process_list_value(value)
                if key == 'images' and filtered_item[key] == []:
                    filtered_item[key] = [{"url": None}]
            elif key not in ['identifiers']:  # Exclude 'identifiers' as it's already processed
                filtered_item[key] = value
            
        return filtered_item

    def _process_attributes(self, attributes: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        return {
            attr_name: self._process_attribute_values(self._clean_attribute(attr_list))
            for attr_name, attr_list in attributes.items() if attr_list
        }

    def _clean_attribute(self, attr_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        cleaned_attr = {}
        for attr in attr_list:
            for k, v in attr.items():
                if k not in ['language_tag', 'marketplace_id', 'marketplaceId']:
                    cleaned_attr[k] = v if k not in cleaned_attr else (
                        [cleaned_attr[k], v] if not isinstance(cleaned_attr[k], list) 
                        else cleaned_attr[k] + [v]
                    )
        return cleaned_attr

    def _process_attribute_values(self, cleaned_attr: Dict[str, Any]) -> Any:
        return (cleaned_attr['value'] if len(cleaned_attr) == 1 and 'value' in cleaned_attr
                else self._process_nested_dict(cleaned_attr))

    def _process_nested_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: ([self._process_nested_dict(item) if isinstance(item, dict) else item for item in v]
                if isinstance(v, list) else
                self._process_nested_dict(v) if isinstance(v, dict) else v)
            for k, v in d.items()
        }

    def _process_list_value(self, value: List[Any]) -> Any:
        if not isinstance(value, list) or not value:
            return value

        filtered_value = [item for item in value if item]
        if not filtered_value:
            return value

        first_item = filtered_value[0]
        if isinstance(first_item, dict):
            cleaned_dict = {k: v for k, v in first_item.items() 
                            if k.lower() not in ['marketplaceid', 'marketplace_id', 'language_tag'] and v}
            if 'images' in cleaned_dict:
                return [img for img in cleaned_dict['images'] if img]
            
            processed_dict = self._process_nested_dict(cleaned_dict)
            return (next(iter(processed_dict.values())) 
                    if len(processed_dict) == 1 and not isinstance(next(iter(processed_dict.values())), (list, dict))
                    else processed_dict)
        elif isinstance(first_item, list):
            return [self._process_nested_dict(item) for item in first_item 
                    if isinstance(item, dict) and any(k.lower() not in ['marketplaceid', 'marketplace_id', 'language_tag'] for k in item.keys())]
        else:
            return first_item
