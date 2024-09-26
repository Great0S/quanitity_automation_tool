""" The lines `import json`, `import re`, `import time`, `import os`, and `import requests` are
 importing necessary modules in Python for working with JSON data, regular expressions, time-related
 functions, operating system functionalities, and making HTTP requests, respectively."""

import asyncio
import json
import re
import time
import os
import logging
from typing import Any, Callable, Dict, List, Optional
import requests
import aiohttp
from aiohttp import ClientSession

from services.trendyol_service.schemas import ProductSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrendyolAPI:

    def __init__(self):
        self.auth_hash = os.environ.get("TRENDYOLAUTHHASH")
        self.store_id = os.environ.get("TRENDYOLSTOREID")
        self.base_url = f"https://api.trendyol.com/sapigw/suppliers/{self.store_id}/"
        self.headers = {
            "User-Agent": f"{self.store_id} - SelfIntegration",
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_hash}",
        }


    def process_product(self, data: Dict, every_product: bool = False) -> Optional[Dict]:
        """
        Process a single product data.

        Args:
            data (Dict): The product data to process.
            every_product (bool, optional): If True, return all data. Defaults to False.

        Returns:
            Optional[Dict]: Processed product data or None if invalid.
        """
        item = data.get("stockCode") or data.get("productMainId")
        if not item:
            return None

        if every_product:
            return data

        item_id = data.get("barcode")
        if not item_id:
            return None

        return {
            "id": str(item_id),
            "sku": str(item),
            "qty": data.get("quantity"),
            "price": data.get("salePrice"),
        }


    async def request_data(self, session: ClientSession, url: str, method: str, payload: Optional[Dict] = None) -> Optional[Dict]:
        """
        Send a request to the specified URL with the given method and payload.
        """
        max_retries = 3
        retry_delay = 1
        timeout = aiohttp.ClientTimeout(total=300)

        async def _make_request():
            try:
                async with session.request(method, url, headers=self.headers, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 400:
                        logger.warning(f"Bad request for URL: {url}")
                    else:
                        logger.warning(f"Request failed with status {response.status} for URL: {url}")
                    return None
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {str(e)}")
                return None

        for attempt in range(max_retries):
            result = await _make_request()
            if result is not None:
                return result

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff

        logger.error(f"Max retries reached for URL: {url}")
        return None


    async def check_batch_request(self, batch_request_id: str) -> Optional[Dict]:
        """
        Check the status of a batch request.

        :param batch_request_id: The ID of the batch request to check
        :return: Dictionary containing the batch request status or None if the request failed
        """
        url = f"{self.base_url}suppliers/{self.store_id}/products/batch-requests/{batch_request_id}"
        
        async with aiohttp.ClientSession() as session:
            response = await self.request_data(session, url, "GET")
            
            if response is None:
                logger.error(f"Failed to check batch request status for ID: {batch_request_id}")
                return None
            
            if "status" in response:
                logger.info(f"Batch request status for ID {batch_request_id}: {response['status']}")
                return response
            else:
                logger.error(f"Unexpected response from Trendyol API: {response}")
                return None


    async def create_product(self, product: ProductSchema) -> Optional[Dict]:
        """
        Create a new product on Trendyol.
        
        :param product: ProductSchema object containing the product details
        :return: Dictionary containing the API response or None if the request failed
        """
        url = f"{self.base_url}suppliers/{self.store_id}/v2/products"
        
        payload = {
            "items": [{
                "barcode": product.barcode,
                "title": product.title,
                "productMainId": product.product_main_id,
                "brandId": product.brand_id,
                "categoryId": product.category_id,
                "quantity": product.quantity,
                "stockCode": product.stock_code,
                "dimensionalWeight": product.dimensional_weight,
                "description": product.description,
                "currencyType": product.currency_type,
                "listPrice": product.list_price,
                "salePrice": product.sale_price,
                "cargoCompanyId": product.cargo_company_id,
                "images": [{"url": img_url} for img_url in product.images],
                "vatRate": product.vat_rate,
                "shipmentAddressId": product.shipment_address_id,
                "attributes": product.attributes,
                "variantAttributes": product.variant_attributes
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            response = await self.request_data(session, url, "POST", payload)
            
            if response is None:
                logger.error("Failed to create product on Trendyol")
                return None
            
            if "batchRequestId" in response:
                logger.info(f"Product creation request submitted. Batch Request ID: {response['batchRequestId']}")
                batch_status = await self.check_batch_request(response["batchRequestId"])
                if batch_status:
                    response["batchStatus"] = batch_status
                return response
            else:
                logger.error(f"Unexpected response from Trendyol API: {response}")
                return None

    
    async def get_products(self, every_product: bool = False, filters: str = "") -> List[Dict]:
        """
        Retrieve products data from multiple pages.
        """
        all_products = []
        page = 0
        async with aiohttp.ClientSession() as session:
            while True:
                url = f"{self.base_url}products?page={page}&size=100{filters}"
                decoded_data = await self.request_data(session, url, "GET")

                if not decoded_data:
                    break

                for data in decoded_data["content"]:
                    product = self.process_product(data, every_product)
                    if product:
                        all_products.append(product)

                page += 1
                if page >= int(decoded_data["totalPages"]):
                    break

        logger.info(f"Trendyol fetched {len(all_products)} products")
        return all_products


    async def update_product(self, product: Dict[str, Any]) -> Dict[str, str]:
        """
        Update a product's price and inventory on Trendyol.
        """
        uri_addon = "/price-and-inventory"
        post_payload = json.dumps({
            "items": [{
                "barcode": product["barcode"],
                "quantity": int(product["quantity"])
            }]
        })

        async with aiohttp.ClientSession() as session:
            while True:
                async with session.post(f"{self.base_url}{uri_addon}", headers=self.headers, data=post_payload) as post_response:
                    if post_response.status == 200:
                        response_text = await post_response.text()
                        if "failure" in response_text.lower():
                            logger.error(f"Request failure for product {product['sku']} | Response: {response_text}")
                            return {"status": "Failed", "barcode": product["barcode"]}

                        batch_request_id = json.loads(response_text)["batchRequestId"]
                        return await self._process_batch_request(
                            batch_request_id,
                            lambda item: {"status": "Success", "barcode": product["barcode"]} if item["status"] == "SUCCESS" else {"status": "Failed", "barcode": product["barcode"]},
                            lambda item: f"Product with code: {product['stock_code']}, New value: {product['quantity']}",
                            lambda item: f"Product with code: {product['sku']} failed to update || Reason: {item['failureReasons']}"
                        )
                    elif post_response.status == 429:
                        await asyncio.sleep(15)
                    else:
                        post_response.raise_for_status()
                        logger.error(f"Request for product {product['sku']} is unsuccessful | Response: {await post_response.text()}")
                        return {"status": "Failed", "barcode": product["barcode"]}


    async def delete_products(self, ids: List[Dict[str, Any]], include_keyword: str, exclude_keyword: str = "") -> None:
        """
        Delete multiple products from Trendyol.
        """
        url = f"{self.base_url}/suppliers/120101/v2/products"
        
        items = [
            {"barcode": item["data"]["barcode"]}
            for item in ids
            if re.search(include_keyword, item["data"]["title"])
            and (not exclude_keyword or not re.search(exclude_keyword, item["data"]["title"]))
        ]

        payload = json.dumps({"items": items})

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self.headers, data=payload) as response:
                if response.status == 200:
                    response_json = await response.json()
                    await self._process_batch_request(
                        response_json["batchRequestId"],
                        lambda item: {"barcode": item["requestItem"]["barcode"], "status": item["status"]},
                        lambda item: f"Successfully deleted products: {item['itemCount'] - len([i for i in item['items'] if i['status'] == 'FAILED'])}",
                        lambda item: f"Failed to delete: {item['barcode']}: {item['failureReasons'][0]}"
                    )
                else:
                    logger.error(f"Failed to initiate delete request. Status: {response.status}")


    async def _process_batch_request(
        self,
        batch_request_id: str,
        process_item: Callable[[Dict[str, Any]], Any],
        success_log: Callable[[Dict[str, Any]], str],
        failure_log: Callable[[Dict[str, Any]], str]
    ) -> List[Any]:
        """
        Process a batch request and handle the results.
        """
        batch_url = f"{self.base_url}batch-requests/{batch_request_id}"
        
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(batch_url, headers=self.headers) as response:
                    if response.status == 200:
                        batch_feedback = await response.json()
                        if batch_feedback["status"] == "IN_PROGRESS":
                            await asyncio.sleep(5)
                            continue

                        if batch_feedback["status"] == "COMPLETED":
                            results = []
                            for item in batch_feedback["items"]:
                                result = process_item(item)
                                if item["status"] == "SUCCESS":
                                    logger.info(success_log(item))
                                else:
                                    logger.error(failure_log(item))
                                results.append(result)
                            return results
                    else:
                        logger.error(f"Failed to get batch status. Status: {response.status}")
                        return []
