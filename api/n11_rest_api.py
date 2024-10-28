import base64
import json
import os
import re
import requests
from app.config import logger
import time
import time
import time


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
            'Pilates Minder & Mat': 1003252,
            'Maket Bıçak': 1001621,
            "Merdiven Aparatı": 1120112,
            'Kapı Önü Paspası': 1000722
        }

        if category_name:

            return categories.get(category_name)  # Return category ID if found

        logger.warning(f"Category '{category_name}' not found.")

        return 'null'  # Return 'null' if no match is found

    def _create_basic_auth(self, username, password):
        """Create basic authentication header."""

        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode("ascii")
        return f"Basic {base64_string}"

    def get_attrs(self, attrs_data, category_id='null'):
        # Initialize dictionaries
        attrs = {}
        n11_attrs = {}

        # Mapping of original attribute names to n11 attribute names
        n11_attrs_names = {
            "Renk": "Renk",
            "Şekil": "Şekil",
            "Boyut/Ebat": "Ölçüler",
            "Taban": "Taban Özelliği",
            "Hav Yüksekliği": "Hav Yüksekliği",
            "Marka": "Marka",
            "Materyal": "Materyal",
            "Basamak Sayısı": "Basamak Sayısı"
        }

        # First pass: collect all attributes from attrs_data
        for attr in attrs_data['data']["attributes"]:
            attr_name = attr["attributeName"]
            # Check if the attribute name matches any key in n11_attrs_names
            for original_name, n11_name in n11_attrs_names.items():
                if re.search(attr_name, original_name):
                    attrs[n11_name] = attr["attributeValue"].replace(
                        " Taban", "")
                    break

        # Special handling for Hav Yüksekliği - extract only digits
        if 'Hav Yüksekliği' in attrs:
            attrs['Hav Yüksekliği'] = re.sub(
                r'\D', '', attrs['Hav Yüksekliği'])

        # Get category attributes from n11 API
        n11_category_attrs_response = requests.get(
            self.base_url + f"cdn/category/{category_id}/attribute",
            headers=self.headers
        )
        n11_category_attrs = n11_category_attrs_response.json()

        # Process each category attribute
        for n11_attr in n11_category_attrs['categoryAttributes']:

            current_attr_name = n11_attr['attributeName']

            if current_attr_name == 'Marka':
                for mk in n11_attr['attributeValues']:
                    if mk['value'] == attrs_data['data']['brand']:
                        value_id = mk['id']
                        custom_value = 'null'
                        break
                    else:
                        value_id = 'null'
                        custom_value = attrs_data['data']['brand']

                n11_attrs[current_attr_name] = {
                    "id": n11_attr['attributeId'],
                    "valueId": value_id,
                    "customValue": custom_value
                }
                continue

            # Skip if attribute is not in our mapping
            if current_attr_name not in n11_attrs_names.values():
                continue

            # Find the corresponding attribute value
            value_id = 'null'
            custom_value = 'null'

            # Get the original attribute name
            attr_value = attrs.get(current_attr_name)

            if attr_value:
                # Try to find matching value ID
                for attr_val in n11_attr['attributeValues']:
                    if attr_val['value'] == attr_value:
                        value_id = attr_val['id']
                        break

                # If no matching ID found, use as custom value
                if value_id == 'null':
                    custom_value = attr_value

            # Store the processed attribute
            n11_attrs[current_attr_name] = {
                "id": n11_attr['attributeId'],
                "valueId": value_id,
                "customValue": custom_value
            }

        if attrs_data['data']['categoryName'] == 'Kedi Tuvaleti Paspası':

            n11_attrs['Materyal'] = {
                "id": 223,
                "valueId": 11034090
            }

        if attrs_data['data']['categoryName'] == 'Merdiven Aparatı':
            n11_attrs['Basamak Sayısı'] = {
                "id": 1392,
                "valueId": 9005305,
                "customValue": 'null'
            }
            n11_attrs['Malzeme'] = {
                "id": 1505,
                "valueId": 10936474,
                "customValue": 'null'
            }

        return n11_attrs

    def create_product(self, product_data):
        """Create products using the N11 API."""
        payload = {"payload": {"integrator": "QAT 1.0", "skus": []}}

        # Prepare the SKU data from the provided product data
        for product in product_data:
            category_id = self.find_category_id(
                product["data"]["categoryName"])
            if not category_id or product["data"]["quantity"] == 0:
                continue
            attrs = self.get_attrs(product, category_id)
            images = product["data"].get("images", [])
            image_list = []

            for index, img in enumerate(images, start=1):
                image_list.append({"url": img["url"], "order": index})

            # Create a dictionary representing the SKU data
            sku_data = {
                "title": product["data"]["title"],
                "description": product["data"]["description"],
                "categoryId": category_id,
                "currencyType": "TL",
                "productMainId": product["data"].get("productMainId", 'null'),
                "preparingDay": 3,
                "shipmentTemplate": "Kargo",
                "maxPurchaseQuantity": 100,
                "stockCode": product["data"]["stockCode"],
                "catalogId": 'null',
                "barcode": product["data"].get("barcode", 'null'),
                "quantity": product["data"]["quantity"],
                "images": image_list,
                "attributes": [
                    {
                        "id": value["id"],
                        "valueId": value.get("valueId", 'null'),
                        "customValue": value.get("customValue", 'null'),
                    }
                    for attr, value in attrs.items()
                ],
                "salePrice": product["data"]["salePrice"],
                "listPrice": product["data"]["listPrice"],
            }
            # print(sku_data)
            payload["payload"]["skus"].append(sku_data)

        # Send POST request to create products
        try:
            response = requests.post(
                self.base_url + "ms/product/tasks/product-create",
                headers={
                    "Authorization": self.auth,
                    "Content-Type": "application/json",
                    "appkey": self.api_key,
                    "appsecret": self.api_secret,
                },
                data=json.dumps(payload),
            )

            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200:
                while True:
                    # Fetch task details
                    task_detail = requests.post(
                        self.base_url + "ms/product/task-details/page-query",
                        headers=self.headers,
                        data=json.dumps({"taskId": response_data["id"], "pageable": {
                            "page": 0,
                                                                        "size": 1000
                        }}),)
                    task_response = task_detail.json()
                    if task_response['status'] in ['PROCESSED', 'REJECT']:
                        break

                    time.sleep(5)

                for item in task_response['skus']['content']:
                    if item['status'] == 'SUCCESS':
                        logger.info(
                            f"{item['itemCode']} is successfully created")
                    else:
                        logger.error(f"Not created || Reason: {item['reasons']}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return 'null'

    def get_products(self, stock_code='null', page=1, page_size=50, raw_data=False):
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
                return 'null'

        logger.info(f"N11 fetched {len(products)} products")

        if not raw_data:
            # Return filtered data: stock code, quantity, and sale price
            return [
                {
                    "id": product.get("n11ProductId"),
                    "sku": product.get("stockCode"),
                    "quantity": product.get("quantity"),
                    "price": product.get("salePrice"),
                }
                for product in products
            ]
        else:
            # Return full product data
            products = [{'sku': item['stockCode'], 'data': item}
                        for item in products]
            return products

    def update_product(self, product: dict):

        uri_addon = "ms/product/tasks/price-stock-update"

        post_payload = {
            "payload": {
                "integrator": "QAT 1.0",
                "skus": [
                    {"stockCode": product["sku"], "listPrice": int(product['price']) * 2, "salePrice": int(
                        product['price']), "quantity": int(product["quantity"]), "currencyType": "TL"}
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

                        logger.info(f"""Product with code: {
                            product["sku"]}, New value: {product["quantity"]}, New price: {product["price"]} updated successfully""")

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
