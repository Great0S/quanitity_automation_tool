import base64
import os
import re
import requests
import json
import time
# from app.config import logger
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PazaramaAPI:
    """
    A client for interacting with the Pazarama API.

    This class handles obtaining and refreshing an access token, and
    provides methods to send authenticated requests to the API.

    Attributes:
        access_token (str): The current access token for API authentication.
        token_expiry (float): The Unix timestamp when the current token expires.
    """

    def __init__(self):
        """
        Initializes the PazaramaAPIClient instance.

        This constructor does not immediately fetch an access token. The token
        is retrieved when the first API request is made or when the token is expired.
        """
        self.access_token = None
        self.token_expiry = None

        # Access environment variables securely
        pazaram_key = os.getenv('PAZARAMAKEY')
        pazaram_secret = os.getenv('PAZARAMASECRET')

        user_pass = f"{pazaram_key}:{pazaram_secret}"
        user_pass_bytes = user_pass.encode('utf-8')
        base64_bytes = base64.b64encode(user_pass_bytes)
        self.base64_hash = base64_bytes.decode('utf-8')

    def get_access_token(self):
        """
        Retrieves a new access token from the Pazarama API.

        This method sends a POST request to the Pazarama token endpoint
        and stores the access token and its expiration time.

        If the token request fails, an error is logged.

        Returns:
            None
        """
        url = "https://isortagimgiris.pazarama.com/connect/token"
        payload = "grant_type=client_credentials&scope=merchantgatewayapi.fullaccess"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {str(self.base64_hash)}",
        }

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if "accessToken" in response_data["data"]:
                self.access_token = response_data["data"]["accessToken"]
                expires_in = response_data["data"].get(
                    "expiresIn", 3600
                )  # Default to 1 hour if not provided
                self.token_expiry = (
                    time.time() + expires_in - 60
                )  # Refresh slightly before expiry
            else:
                logger.error(f"Access token request failed || Reason: {response_data}")
                self.access_token = None
                self.token_expiry = None

        except requests.exceptions.RequestException as e:
            logger.error(f"Access token request encountered an error: {str(e)}")
            self.access_token = None
            self.token_expiry = None

    def ensure_token_validity(self):
        """
        Ensures that the current access token is valid.

        If the token is missing or has expired, a new token is requested.

        Returns:
            None
        """
        if not self.access_token or time.time() >= self.token_expiry:
            self.get_access_token()

    def process_target_attributes(self, data):
        """
        Extracts 'id', 'name', and 'values' from a list of attributes.

        :param data: List of dictionaries containing attribute details
        :return: List of dictionaries containing 'id', 'name', and 'values'
        """
        extracted_data = []

        for attribute in data["attributes"]:
            # Extracting 'id', 'name', and 'values'
            attr_id = attribute.get("id")
            attr_name = attribute.get("name")
            attr_values = [
                {"id": value.get("id"), "value": value.get("value")}
                for value in attribute.get("attributeValues", [])
            ]

            # Append the extracted data to the result list
            extracted_data.append(
                {"id": attr_id, "name": attr_name, "values": attr_values}
            )

        return extracted_data

    def process_source_attributes(self, attributes):
        """
        Extracts relevant attributes from the product's attributes.

        Args:
            attributes (list): List of product attributes.

        Returns:
            dict: Extracted attributes.
        """
        size_match = [1, 1]
        size, color, feature, materyal, style, tip, thickness, shape = (
            1,
            None,
            None,
            None,
            None,
            None,
            1,
            "Dikdörtgen",
        )

        for attr in attributes:

            attr_id = attr["attributeId"]
            attr_name = attr["attributeName"]
            attr_values = attr["attributeValue"]

            if re.search(r"Boyut/Ebat|Beden", attr_name):
                if isinstance(attr_name, (int, float)):
                    size = attr_values
                    size_match = str(attr_values).split("x")
            elif re.search(r"Renk|Color", attr_name):
                color = attr_values
            elif re.search(r"Özellik", attr_name):
                feature = attr_values
            elif re.search(r"Materyal", attr_name):
                materyal = attr_values
            elif re.search(r"Tema", attr_name):
                style = attr_values
            elif re.search(r"Tip", attr_name):
                tip = attr_values
            elif re.search(r"Hav Yüksekliği", attr_name):
                match = re.search(r"\d+", attr_values)
                if match:
                    thickness = match.group()
            elif re.search(r"Şekil", attr_name):
                shape = attr_values

        return {
            "size": size,
            "size_match": size_match,
            "color": color,
            "feature": feature,
            "style": style,
            "material": materyal,
            "thickness": thickness,
            "shape": shape,
            "tip": tip,
        }

    def request_data(self, method="GET", uri="", params=None, payload=None):
        """
        Sends a request to the Pazarama API with the specified method, URI, parameters, and payload.

        This method handles authentication by ensuring that a valid access token
        is included in the request headers. If the token has expired or is not available,
        it is automatically refreshed.

        Args:
            method (str): The HTTP method for the request (e.g., 'GET', 'POST').
            uri (str): The URI path for the API endpoint.
            params (dict, optional): Query parameters to include in the request.
            payload (dict, optional): The JSON payload to include in the request.

        Returns:
            dict: The JSON response from the API if the request is successful.
            None: If the request fails, returns None.
        """
        self.ensure_token_validity()

        url = f"https://isortagimapi.pazarama.com/{uri}?"
        payload_dump = json.dumps(payload, ensure_ascii=False)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        while True:
            try:
                response = requests.request(
                    method, url, headers=headers, params=params, data=payload_dump
                )
                response_data = response.json()
                response.raise_for_status()

                if response.status_code == 200:
                    return response_data

            except requests.exceptions.RequestException as e:
                if response.status_code == 429:  # Too many requests
                    logger.warning("Rate limit exceeded. Retrying after a delay...")
                    time.sleep(3)
                else:
                    logger.error(
                        f"Request failed with status {response.status_code} || Reason: {e}"
                    )
                    return None

    def request_processing(
        self, uri: str, payload: dict = None, params: dict = None, method: str = "GET"
    ):
        """
        Processes a request to the Pazarama API, measuring the duration of the request.

        This function sends a request using the `request_data` function, logs the time taken,
        and returns the API response along with the elapsed time.

        Args:
            uri (str): The URI path for the API endpoint.
            payload (dict, optional): The JSON payload to include in the request. Defaults to None.
            params (dict, optional): Query parameters to include in the request. Defaults to None.
            method (str): The HTTP method for the request (e.g., 'GET', 'POST'). Defaults to 'GET'.

        Returns:
            tuple: A tuple containing:
                - The JSON response from the API if the request is successful, or None if it fails.
                - The time taken to complete the request in seconds.
        """
        # Use empty dictionaries if None is provided
        payload = payload or {}
        params = params or {}

        start_time = time.time()

        try:
            # Call request_data to perform the actual API request
            response = self.request_data(
                method=method, uri=uri, params=params, payload=payload
            )
        except Exception as e:
            # Log the exception with details
            logger.error(f"Error during API request: {str(e)}")
            response = None

        end_time = time.time()
        elapsed_time = end_time - start_time

        return response, elapsed_time

    def create_products(self, product_data):
        """
        The function `pazarama_updateRequest` updates the stock count of a product on Pazarama platform
        based on the provided product information.

        :param product: The `pazarama_updateRequest` function takes a `product` parameter, which is expected
        to be a dictionary containing the following keys:
        """

        categories = {
            "Kapı Önü Paspası": {
                "id": "cfb8e050-84d7-4bfd-b8de-6591443481a6",
                "target_name": "Dış Mekan Paspası",
            },
            "Halı": {
                "id": "50af37b5-4de3-4f86-bc8e-065f78d9fdb8",
                "target_name": "Halı",
            },
            "Pilates Minder ve Mat": {
                "id": "026d861d-174b-423d-b0fc-ea8399519e22",
                "target_name": "Pilates, Yoga Matı, Minderi",
            },
            "Kedi Tuvaleti": {
                "id": "bebee8ab-639a-465a-b4f8-2d5105918fa2",
                "target_name": "Kedi Tuvaleti, Aksesuarları",
            },
            "Merdiven Aparatları": {
                "id": "b3d1b879-1b82-4a6a-a254-cfb910e0f70c",
                "target_name": "Merdivenler",
            },
            "Yapıştırıcı&Bantlar": {
                "id": "06f358f2-6e2a-4c90-a042-23a18d9be7c5",
                "target_name": "Yapıştırıcı Bantlar",
            },
            "Maket Bıçağı": {
                "id": "c45b36f1-119b-424b-be4d-8c75a87fa733",
                "target_name": "Makas, Maket Bıçağı",
            },
            "Oto Paspasları": {
                "id": "df40da26-ff65-4861-9c59-65757fda6b85",
                "target_name": "Oto Paspası",
            },
            "Kırlent ve Kırlent Kılıfı": {
                "id": "81a97ee5-3950-45d9-b37e-b51e1a74aa39",
                "target_name": "Dekoratif Yastık, Kırlent, Kılıf",
            },
            "Bahçe Yer Döşemeleri": {
                "id": "f5dc89bb-88e4-4bd3-8bef-943bd47def7b",
                "target_name": "Bahçe Yer Döşemesi",
            },
            "Çocuk Halısı": {
                "id": "50af37b5-4de3-4f86-bc8e-065f78d9fdb8",
                "target_name": "Halı",
            },
            "Dikiş Makinesi Aksesuarları": {
                "id": "e63975fc-a24a-4b7d-b5a2-c3281e05b774",
                "target_name": "Dikiş Makinesi Aksesuarları",
            },
        }

        for _, data_items in product_data.items():
            for product in data_items:
                product_data = product["data"]
                product_sku = product_data["stockCode"]
                product_category = product_data["categoryName"]
                category_id = categories[product_category]["id"]
                brands = {
                    "Stepmat": "20fd0ae7-cf18-4bba-90f6-61ea5856045d",
                    "Myfloor": "825300a0-71a1-4e56-bab9-08dacc7459ff",
                }
                images = [{"imageurl": image["url"]}for image in product_data["images"]]

                request_payload = {
                    "products": [
                        {
                            "name": product_data["title"],
                            "displayName": product_data["title"],
                            "description": product_data["description"],
                            "brandId": brands[product_data["brand"]],
                            "desi": 1,
                            "code": product_data["barcode"],
                            "groupCode": product_data["productMainId"],
                            "stockCode": product_data["stockCode"],
                            "stockCount": product_data["quantity"],
                            "listPrice": product_data["listPrice"],
                            "salePrice": product_data["salePrice"],
                            "productSaleLimitQuantity": 1000,
                            "currencyType": "TRY",
                            "vatRate": 10,
                            "images": images,
                            "categoryId": category_id,
                            "attributes": [],
                            "deliveries": [ { "deliveryId": "", "cityList": [] } ],
                        }
                    ]
                }

                update_request, elapsed_time = self.request_processing(
                    uri="product/create", payload=request_payload, method="POST"
                )

                if update_request:

                    if update_request["success"] == True:

                        logger.info(
                            f"""Product with code: {product["sku"]}, New value: {product["qty"]}, Elapsed time: {elapsed_time:.2f} seconds."""
                        )

                    else:

                        logger.error(
                            f'Product with code: {product_sku} failed to update || Reason: {update_request["data"][0]["error"]} || Elapsed time: {elapsed_time:.2f} seconds.'
                        )

    def get_products(self, everyProduct: bool = False, local: bool = False):
        """
        Retrieves a list of products from the Pazarama API and returns a subset of product data
        based on the specified condition.

        Args:
            everyProduct (bool): If True, returns detailed product data. If False, returns a simplified subset.
            local (bool): A placeholder argument for future use or additional functionality. Currently not used.

        Returns:
            list: A list of dictionaries containing product information. The structure of each dictionary
                  depends on the value of `everyProduct`.
        """
        products_items = []

        params = {"Approved": "true", "Size": 250}

        try:
            products_list, elapsed_time = self.request_processing(
                uri="product/products", params=params
            )
            if not products_list or "data" not in products_list:
                logger.error("Failed to retrieve product data or data is missing.")
                return products_items

            products = products_list["data"]

            if products:
                for product in products:
                    if not everyProduct:
                        products_items.append(
                            {
                                "id": product.get("code"),
                                "sku": product.get("stockCode"),
                                "qty": product.get("stockCount"),
                                "price": product.get("salePrice"),
                            }
                        )
                    else:
                        products_items.append(product)

            logger.info(
                f"Pazarama fetched {len(products_items)} products in {elapsed_time:.2f} seconds."
            )

        except Exception as e:
            logger.error(f"Error retrieving products: {str(e)}")

        return products_items

    def update_product(self, product_data: dict):
        """
        The function `pazarama_updateRequest` updates the stock count of a product on Pazarama platform
        based on the provided product information.

        :param product: The `pazarama_updateRequest` function takes a `product` parameter, which is expected
        to be a dictionary containing the following keys:
        """

        product_code = product_data["code"]
        qty = product_data["stockCount"]

        update_payload = {"items": [{"code": product_code, "stockCount": int(qty)}]}

        update_request, elapsed_time = self.request_processing(
            uri="product/updateStock-v2", payload=update_payload, method="POST"
        )

        if update_request:

            if update_request["success"] == True:

                logger.info(
                    f"""Product with code: {product_code}, New value: {qty}, Elapsed time: {elapsed_time:.2f} seconds."""
                )

                return True

            else:

                logger.error(
                    f'Product with code: {product_code} failed to update || Reason: {update_request["data"][0]["error"]} || Elapsed time: {elapsed_time:.2f} seconds.'
                )

                return False
    