import base64
import json
import os
import re
import requests
from app.config import logger


class N11RestAPI:
    def __init__(self):
        """Initialize with the base URL of the N11 product API."""
        self.base_url = "https://api.n11.com/"

        # Auth
        self.api_key = os.getenv("N11_KEY")
        self.api_secret = os.getenv("N11_SECRET")
        self.auth = self._create_basic_auth(self.api_key, self.api_secret)
        self.headers = {
            "appkey": self.api_key,
            "appsecret": self.api_secret,
            "Content-Type": "application/json",
        }

    def find_category_id(self, category_name):
        """Find category ID by matching category name."""

        categories = {
            "Kedi Tuvaleti": 1000831,
            "Halı": 1000722,
            "Pilates Minderi": 1003252,
            "Maket Bıçağı": 1001621,
        }

        if category_name:

            return categories.get(category_name, None)  # Return category ID if found

        logger.warning(f"Category '{category_name}' not found.")

        return None  # Return None if no match is found

    def _create_basic_auth(self, username, password):
        """Create basic authentication header."""

        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode("ascii")
        return f"Basic {base64_string}"

    def get_attrs(self, attrs_data):

        attrs = {}

        for attr in attrs_data["attributes"]:
            attr_name = ["Renk", "Şekil", "Boyut/Ebat", "Taban", "Hav Yüksekliği"]

            for item in attr_name:

                if re.search(attr["attributeName"], item):
                    attrs[attr["attributeName"]] = attr["attributeValue"].replace(
                        " Taban", ""
                    )

        return attrs

    def create_product(self, product_data):
        """Create products using the N11 API."""
        payload = {"integrator": "QAT 1.0", "skus": []}

        # Prepare the SKU data from the provided product data
        for product in product_data:
            category_id = self.find_category_id(product["data"]["categoryName"])
            attrs = self.get_attrs(product_data)
            sku_data = {
                "title": product["data"]["title"],
                "description": product["data"]["description"],
                "categoryId": category_id,
                "currencyType": 1,
                "productMainId": product["data"].get("productMainId", None),
                "preparingDay": 3,
                "shipmentTemplate": "Kargo",
                "maxPurchaseQuantity": 100,
                "stockCode": product["data"]["stockCode"],
                "catalogId": None,
                "barcode": product["data"].get("barcode", None),
                "quantity": product["data"]["quantity"],
                "images": [
                    {"url": img["url"], "order": index}
                    for index, img in product["data"].get("images", [])
                ],
                "attributes": [
                    {
                        "id": attr["id"],
                        "valueId": attr.get("valueId", None),
                        "customValue": attr.get("customValue", None),
                    }
                    for attr in product["data"].get("attributes", [])
                ],
                "salePrice": product["data"]["salePrice"],
                "listPrice": product["data"]["listPrice"],
            }
            payload["skus"].append(sku_data)

        # Send POST request to create products
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": self.auth,
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload),
            )

            response.raise_for_status()  # Raise an error for bad responses
            return response.json()  # Return the JSON response
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return None

    def get_products(self, stock_code=None, page=1, page_size=50, raw_data=False):
        """Retrieve products from the API with optional filters."""
        page = 1
        products = []
        headers = self.headers

        while True:
            params = {"page": page, "size": page_size}

            product_request_url = self.base_url + "ms/product-query"

            try:
                response = requests.get(
                    product_request_url, params=params, headers=headers
                )
                response.raise_for_status()  # Raise an error for bad responses
                data = response.json()
                products.extend(data.get("content", []))

                if data.get("totalPages", 0) == page:
                    break  # No more pages, exit the loop

                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred: {e}")
                return None

        logger.info(f"N11 fetched {len(products)} products")

        if not raw_data:
            # Return filtered data: stock code, quantity, and sale price
            return [
                {
                    "id": product.get("n11ProductId"),
                    "sku": product.get("stockCode"),
                    "qty": product.get("quantity"),
                    "price": product.get("salePrice"),
                }
                for product in products
            ]
        else:
            # Return full product data
            return products

    def update_product(self, product: dict):

        uri_addon = "ms/product/tasks/price-stock-update"

        post_payload = {
            "payload": {
                "integrator": "QAT 1.0",
                "skus": [
                    {"stockCode": product["sku"], "quantity": int(product["qty"])}
                ],
            }
        }

        post_response = requests.post(
            self.base_url + uri_addon, headers=self.headers, json=post_payload
        )

        if post_response.status_code == 200:

            task_payload = {
                "taskId": post_response.json()["id"],
                "pageable": {"page": 0, "size": 1000},
            }

            while True:
                task_response = requests.post(
                    self.base_url + "ms/product/task-details/page-query",
                    headers=self.headers,
                    json=task_payload,
                )

                if task_response.status_code == 200:
                    if task_response.json().get("status") == "PROCESSED":

                        task_response_json = task_response.json()

                        logger.info(
                            f"Request for product {product['sku']} is successful | Response: {task_response_json['skus']['content'][0]['status']} - {task_response_json['skus']['content'][0]['reasons']}"
                        )

                        return

                    continue

                else:
                    break

        else:

            post_response.raise_for_status()

            logger.error(
                f"""Request for product {
                   product['sku']} is unsuccessful | Response: {
                       post_response.text}"""
            )
