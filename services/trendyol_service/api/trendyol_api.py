""" The lines `import json`, `import re`, `import time`, `import os`, and `import requests` are
 importing necessary modules in Python for working with JSON data, regular expressions, time-related
 functions, operating system functionalities, and making HTTP requests, respectively."""

import asyncio
import json
import re
import time
import os
import logging
from typing import Dict, List, Optional
import requests
import aiohttp
from aiohttp import ClientSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrendyolAPI:

    def __init__(self):
        self.auth_hash = os.environ.get("TRENDYOLAUTHHASH")
        self.store_id = os.environ.get("TRENDYOLSTOREID")
        self.base_url = f"https://api.trendyol.com/sapigw/suppliers/{self.store_id}/products"
        self.headers = {
            "User-Agent": f"{self.store_id} - SelfIntegration",
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_hash}",
        }

    async def request_data(self, session: ClientSession, url: str, method: str, payload: Optional[Dict] = None) -> Optional[Dict]:
        """
        Send a request to the specified URL with the given method and payload.
        """
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                async with session.request(method, url, headers=self.headers, json=payload, timeout=300) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 400:
                        logger.warning(f"Bad request for URL: {url}")
                        return None
                    else:
                        logger.warning(f"Request failed with status {response.status} for URL: {url}")
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {str(e)}")

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        logger.error(f"Max retries reached for URL: {url}")
        return None

    async def get_products(self, every_product: bool = False, filters: str = "") -> List[Dict]:
        """
        Retrieve products data from multiple pages.
        """
        all_products = []
        page = 0
        async with aiohttp.ClientSession() as session:
            while True:
                url = f"{self.base_url}?page={page}&size=100{filters}"
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

    def process_product(self, data: Dict, every_product: bool) -> Optional[Dict]:
        """
        Process a single product data.
        """
        item = data.get("stockCode") or data.get("productMainId")
        if not item:
            return None

        if every_product:
            return data
        else:
            item_id = data.get("barcode")
            if not item_id:
                return None
            return {
                "id": str(item_id),
                "sku": str(item),
                "qty": data.get("quantity"),
                "price": data.get("salePrice"),
            }

    async def update_product(self, product: dict):
        """
        The function `post_data` sends a POST request to a specified URL with a payload containing a list of
        products.
        """
        uri_addon = "/price-and-inventory"

        post_payload = json.dumps(
            {"items": [{"barcode": product["barcode"],
                        "quantity": int(product["quantity"])}]}
        )
        post_response = self.request_data(uri_addon, "POST", post_payload)

        if post_response.status_code == 200:

            if re.search("failure", post_response.text):

                logger.error(
                    f"Request failure for product {
                        product['sku']} | Response: {post_response.text}"
                )

            else:

                batch_requestid = json.loads(post_response.text)[
                    "batchRequestId"]

                while True:

                    batchid_request_raw = self.request_data(
                        f"/batch-requests/{batch_requestid}", "GET", []
                    )

                    batchid_request = json.loads(batchid_request_raw.text)

                    if batchid_request["items"]:

                        request_status = batchid_request["items"][0]["status"]

                        if request_status == "SUCCESS":

                            logger.info(
                                f'Product with code: {
                                    product["stock_code"]}, New value: {product["quantity"]}'
                            )

                            return {"status": "Success", "barcode": product["barcode"]}

                        logger.error(
                            f"""Product with code: {
                                product["sku"]} failed to update || Reason: {
                                batchid_request["items"][0]["failureReasons"]}"""
                        )

                        return {"status": "Failed", "barcode": product["barcode"]}

                    else:

                        pass

        elif post_response.status_code == 429:

            time.sleep(15)

        else:

            post_response.raise_for_status()

            logger.error(
                f"""Request for product {
                    product['sku']} is unsuccessful | Response: {
                    post_response.text}"""
            )

    def delete_product(self, ids, include_keyword, exclude_keyword=""):

        url = "https://api.trendyol.com/sapigw/suppliers/120101/v2/products"
        batch_url = (
            "https://api.trendyol.com/sapigw/suppliers/120101/products/batch-requests/"
        )
        items = []

        for item in ids:

            if re.search(include_keyword, item["data"]["title"]):

                if exclude_keyword:

                    if not re.search(exclude_keyword, item["data"]["title"]):

                        items.append({"barcode": item["data"]["barcode"]})

                items.append({"barcode": item["data"]["barcode"]})

        payload = json.dumps({"items": items})

        response = requests.request(
            "DELETE", url, headers=self.headers, data=payload, timeout=3000)

        if response.status_code == 200:

            response_json = json.loads(response.text)

            while True:

                request_response = requests.request(
                    "GET",
                    batch_url + response_json["batchRequestId"],
                    headers=self.headers,
                    data=payload,
                    timeout=3000,
                )

                if request_response.status_code == 200:

                    batch_feedback = json.loads(request_response.text)
                    failed = []

                    if batch_feedback["status"] == "IN_PROGRESS":

                        time.sleep(5)

                    if batch_feedback["status"] == "COMPLETED":

                        for item_report in batch_feedback["items"]:

                            if item_report["status"] == "FAILED":

                                failed.append(
                                    {
                                        "barcode": item_report["requestItem"][
                                            "barcode"
                                        ],
                                        "reason": item_report["failureReasons"][0],
                                    }
                                )

                        if failed:

                            logger.info(f"Successfully deleted products: {
                                        batch_feedback['itemCount']-len(failed)}\t\t\tFailed to delete: {len(failed)}")
                            logger.error("Failed items:\n")
                            for i, item in enumerate(failed):

                                logger.error(f"{i+1}. {item['barcode']}: {item['reason']}")

                            break

                        else:

                            logger.info(f"Successfully deleted products: {batch_feedback['itemCount']}")

                            break
