""" importing necessary modules and libraries for performing various
 tasks related to handling data, making HTTP requests, and working with concurrency """

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from glob import glob
import textwrap
from urllib import parse
import json
import os
import re
import csv
import io
import time
import requests
from sp_api.api import DataKiosk
from sp_api.api import (
    ListingsItems,
    ProductTypeDefinitions,
    CatalogItems,
    CatalogItemsVersion,
    ReportsV2,
)
from sp_api.base.reportTypes import ReportType
from datetime import datetime
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

    def retry_with_backoff(self, func, *args, retries=5, **kwargs):
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
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

        product_attrs = self.retry_with_backoff(
            self.product_type_api.get_definitions_product_type,
            productType=product_type,
            marketplaceIds=[self.marketplace_id],
            requirements="LISTING",
            locale="tr_TR"
        )

        return self.download_attribute_schema(product_attrs.payload)

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

    def get_listings_items(self):
        try:
            response = self.retry_with_backoff(
                self.listings_api.get_listings_items,
                sellerId=self.seller_id,
                marketplaceIds=[self.marketplace_id],
                includedData=['attributes', 'issues', 'offers', 'summaries', 'fulfillmentAvailability', 'procurement'],
                pageSize=100  # Maximum allowed page size
            )
            
            items = []
            while True:
                if response.payload:
                    items.extend(response.payload)
                    logger.info(f"Retrieved {len(response.payload)} listings")
                
                if response.next_token:
                    response = self.retry_with_backoff(
                        self.listings_api.get_listings_items,
                        sellerId=self.seller_id,
                        marketplaceIds=[self.marketplace_id],
                        includedData=['attributes', 'issues', 'offers', 'summaries', 'fulfillmentAvailability', 'procurement'],
                        pageSize=100,
                        nextToken=response.next_token
                    )
                else:
                    break
            
            if items:
                logger.info(f"Successfully retrieved all {len(items)} listings")
                return items
            else:
                logger.warning("No listings found")
                return None
        except Exception as e:
            logger.error(f"Error retrieving listings: {str(e)}")
            return None

