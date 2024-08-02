""" importing required libs for the script """

import logging
import os
import random
import re
import time
import json
import requests
from circuitbreaker import CircuitBreaker

products = []


class HpApi:

    def __init__(self):

        self.data = None
        self.size = ""
        self.color = ""
        self.shape = ""
        self.style = ""
        self.category_attrs = {}
        self.category_target = ""
        self.store_id = os.environ.get("HEPSIBURADAMERCHENETID")
        self.mpop_url = "https://mpop.hepsiburada.com/"
        self.listing_external_url = f"https://listing-external.hepsiburada.com/Listings/merchantid/{
            self.store_id}"
        self.auth_hash = os.environ.get("HEPSIBURADAAUTHHASH")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_hash}",
        }
        self.logger = logging.getLogger(__name__)

    def request_data(
        self,
        subdomain: str,
        url_addons: str,
        request_type: str,
        payload_content: str,
        base_delay: int = 3,
    ):
        """
        Sends a HTTP request to the specified Hepsiburada API endpoint.

        Handles retries with exponential backoff and circuit breaker for resilience.

        Args:
            subdomain (str): The Hepsiburada subdomain (e.g., 'listing-external').
            url_addons (str): The additional URL path for the API endpoint.
            request_type (str): The HTTP request method (e.g., 'GET', 'POST').
            payload_content (str): The request payload as a string.
            max_retries (int, optional): The maximum number of retry attempts. Defaults to 3.

        Returns:
            requests.Response: The response object from the successful request.

        Raises:
            Exception: If the maximum number of retries is exceeded or an unexpected error occurs.
        """

        payload = payload_content
        url = f"{subdomain}{url_addons}"
        circuit_breaker = CircuitBreaker(
            failure_threshold=5, 
            recovery_timeout=60)
        attempt = 0

        try:
            with circuit_breaker:

                api_request = requests.request(
                    request_type, 
                    url, 
                    headers=self.headers,
                    data=payload, 
                    timeout=3000
                )

                if api_request.status_code == 200:

                    return api_request

                if api_request.status_code == 400:

                    error_message = json.loads(api_request.text)
                    self.logger.error(
                        f"""API bad request || Payload: {payload} || Message: {error_message['title']}""")

                    return None

                if api_request.status_code in [500, 502, 503, 504]:

                    raise Exception("HepsiBurada Server has an error")

        except Exception as e:

            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            self.logger(f"""API request failure || Retrying in {delay} seconds""")
            time.sleep(delay)

    def prepare_product_data(self, items: dict, source: str = "", op: str = "") -> list:
        """
        Prepares product data for creating or fetching listings on HepsiBurada.

        Args:
            items (dict): A dictionary containing product data.
            op (str): Can be 'info' for updating or 'create' for creating listings.

        Returns:
            list: A list of dictionaries containing prepared product data.
        """

        def get_categories(self) -> dict:
            """
            Fetches category data from HepsiBurada API or a local cache file.

            Returns:
                dict: A dictionary containing category data.
            """

            def get_category_attrs(self, payload, category) -> tuple:
                """
                Retrieves additional category attributes (base, variant, etc.)

                Args:
                    payload (dict): Data to be sent with the request.
                    category (dict): Category information.
                    self (HpApi): Instance of the HpApi class.

                Returns:
                    tuple: A tuple containing base, regular, and variant attributes.
                """

                property_response = self.request_data(
                    subdomain=self.mpop_url,
                    url_addons=f"""product/api/categories/{
                        category['categoryId']}/attributes""",
                    request_type="GET",
                    payload_content=payload,
                )
                property_data = json.loads(property_response.text)["data"]

                if property_data:

                    base_attrs = property_data["baseAttributes"]
                    attrs = property_data["attributes"]
                    variant_attrs = property_data["variantAttributes"]

                    return base_attrs, attrs, variant_attrs

                else:

                    # Handle case where property data is empty
                    return [], [], []

            url = self.mpop_url + "product/api/categories/get-all-categories?size=10000"

            payload = {}
            categories = {}
            file_name = "hp_categories.json"

            if os.path.exists(file_name):

                with open(file_name, "r", encoding="utf-8") as json_file:

                    file_data = json.load(json_file)

                    for category in file_data:

                        if file_data[category]["baseAttributes"]:

                            categories[category] = file_data[category]

                            continue

                        baseAttrs, attrs, variyantAttrs = get_category_attrs(
                            payload=payload, category=file_data[category]
                        )
                        file_data[category]["baseAttributes"] = baseAttrs
                        file_data[category]["attributes"] = attrs
                        file_data[category]["variantAttributes"] = variyantAttrs

                        categories[category] = file_data[category]

                if len(categories) == len(file_data):

                    with open(file_name, "w", encoding="utf-8") as json_file:

                        json.dump(categories, json_file)

                return file_data

            return None

        ready_data = []

        categories = get_categories(self)
        sorted_items = sorted(items.items())

        for item_data_list in sorted_items:

            if len(item_data_list[1]) <= 1:

                continue

            else:

                if len(item_data_list[1]) > 2:

                    if item_data_list[1][0]["platform"] == source:

                        self.data = item_data_list[1][0]["data"]
                        del item_data_list[1][1]

                elif item_data_list[1][0]["platform"] == source:

                    self.data = item_data_list[1][0]["data"]

            if not self.data:

                continue

            images = self.data["images"]
            source_category = self.data["categoryName"]
            product = self.data["title"]

            for cat_data in categories:

                item_data = categories[cat_data]

                if re.search(cat_data, product):

                    self.category_target = item_data["categoryId"]
                    attrs = (
                        item_data["baseAttributes"]
                        + item_data["attributes"]
                        + item_data["variantAttributes"]
                    )
                    category_attrs_list = [{x["id"]: x["name"]} for x in attrs]
                    self.category_attrs = {
                        a: b for d in category_attrs_list for a, b in d.items()
                    }

                    break

                elif source_category == cat_data:

                    self.category_target = item_data["categoryId"]
                    attrs = (
                        item_data["baseAttributes"]
                        + item_data["attributes"]
                        + item_data["variantAttributes"]
                    )
                    category_attrs_list = [{x["id"]: x["name"]} for x in attrs]
                    self.category_attrs = {
                        a: b for d in category_attrs_list for a, b in d.items()
                    }

                    break

            for i in enumerate(images):

                self.category_attrs[f"Image{i[0]+1}"] = i[1]["url"]
                if i[0] == 5:

                    pass

            source_product_attrs = self.data["attributes"]

            for atrr in source_product_attrs:

                if re.search("Boyut/Ebat", atrr["attributeName"]):

                    self.size = atrr["attributeValue"]

                if re.search("Renk", atrr["attributeName"]):

                    self.color = atrr["attributeValue"]

                if re.search("Tema", atrr["attributeName"]):

                    self.style = atrr["attributeValue"]

                if re.search("Şekil", atrr["attributeName"]):

                    self.shape = atrr["attributeValue"]

                else:

                    self.shape = "Dikdörtgen"

            self.category_attrs["hbsku"] = item_data_list[1][1]["data"][
                "hepsiburadaSku"
            ]
            self.category_attrs["merchantSku"] = self.data.get(
                "stockCode", None)
            self.category_attrs["VaryantGroupID"] = self.data.get(
                "productMainId", None)
            self.category_attrs["Barcode"] = self.data.get("barcode", None)
            self.category_attrs["UrunAdi"] = self.data.get("title", None)
            self.category_attrs["UrunAciklamasi"] = self.data.get(
                "description", None)
            self.category_attrs["Marka"] = self.data.get("brand", "Myfloor")
            self.category_attrs["GarantiSuresi"] = 24
            self.category_attrs["kg"] = "1"
            self.category_attrs["tax_vat_rate"] = "8"
            self.category_attrs["price"] = self.data.get("salePrice", 0)
            self.category_attrs["stock"] = self.data.get("quantity", 0)
            self.category_attrs["Video1"] = ""

            if self.category_attrs["stock"] == 0:

                continue

            if re.search("dip çubuğu", self.data["title"]):

                self.category_attrs["renk_variant_property"] = self.color
                self.category_attrs["secenek_variant_property"] = ""

            elif re.search("Maket Bıçağ", self.data["title"]):

                self.category_attrs["adet_variant_property"] = 1
                self.category_attrs["ebatlar_variant_property"] = self.size

            elif re.search(
                r"Koko|Kauçuk|Nem Alıcı Paspas|Kapı önü Paspası|Halı|Tatami|Kıvırcık|Comfort|Hijyen|Halı Paspas|Halıfleks Paspas",
                self.data["title"],
            ):

                self.category_attrs["00004LW9"] = self.style  # Desen / Tema"
                self.category_attrs["00005JUG"] = "Var"  # Kaymaz Taban
                self.category_attrs["sekil"] = self.shape
                self.category_attrs["renk_variant_property"] = self.color
                self.category_attrs["00001CM1"] = self.size  # Ebatlar

            listing_details = {
                "categoryId": self.category_target,
                "merchant": self.store_id,
                "attributes": self.category_attrs,
            }

            ready_data.append(listing_details)
            self.category_attrs = {k: "" for k in self.category_attrs}

        return ready_data

    def create_listing(self, url, ready_data) -> None:
        """
        Sends a POST request to the HepsiBurada API to create a new listing.

        Args:
            url (str): The URL of the API endpoint.
            ready_data (list): A list of dictionaries containing product data.
        """

        if ready_data:

            with open("integrator.json", "w", encoding="utf-8") as json_file:
                json.dump(ready_data, json_file)

            files = {
                "file": (
                    "integrator.json",
                    open("integrator.json", "rb"),
                    "application/json",
                )
            }

            self.headers["Accept"] = "application/json"
            self.headers.pop("Content-Type")

            response = requests.post(url, files=files, headers=self.headers)

            self.logger.info(response.text)

    def update_listing(self, products, options=None, source="") -> None:
        """
        Updates stock information for a product on HepsiBurada.

        Args:
            product (dict): A dictionary containing product data.
            options (str, optional): Can be 'full' for a complete update or 'info' for a partial update, defaults to None.
        """

        update_request_raw = ''

        if options:

            if options != "full":

                update_data = self.prepare_product_data(
                    items=products, op=options, source=source
                )
                listing_details = {}
                listing_items = []
                for update_item in update_data:

                    listing_items.append({"hbSku": update_item['attributes'].get('hbsku', ''),
                                          "productName": update_item['attributes'].get('UrunAdi', ''),
                                          "productDescription": update_item['attributes'].get('UrunAciklamasi', ''),
                                          "image1": update_item['attributes']['Image1'],
                                          "image2": update_item['attributes']['Image2'],
                                          "image3": update_item['attributes']['Image3'],
                                          "image4": update_item['attributes']['Image4'],
                                          "image5": update_item['attributes']['Image5'],
                                          "video": update_item['attributes']['Video1'],
                                          "attributes": {
                        "renk_variant_property": update_item['attributes'].get('renk_variant_property', ''),
                        "numara_variant_property": update_item['attributes'].get('00001CM1', ''),
                        "00004LW9": update_item['attributes'].get('00004LW9'),
                        "00005JUG": update_item['attributes'].get('00005JUG'),
                        "sekil": update_item['attributes'].get('sekil'),
                        "00001CM1": update_item['attributes'].get('00001CM1'),
                        "malzeme": ""
                    }})

                listing_details["merchantId"] = self.store_id
                listing_details["items"] = listing_items

                with open("integrator-ticket-upload.json", "w", encoding="utf-8") as json_file:

                    json.dump(listing_details, json_file)

                    files = {
                        "file": (
                            "integrator-ticket-upload.json",
                            open("integrator-ticket-upload.json", "rb"),
                            "application/json",
                        )
                    }

                self.headers["Accept"] = "application/json;charset=UTF-8"
                self.headers.pop("Content-Type")
                update_request_raw = requests.post(
                    url=self.mpop_url + f"""ticket-api/api/integrator/import""",
                    files=files,
                    headers=self.headers
                )

                if update_request_raw:

                    update_state_response = json.loads(update_request_raw.text)

                    if update_state_response['success'] == True:

                        update_state_id = update_state_response["data"]["trackingId"]

                        while True:
                        
                            check_status_request = self.request_data(
                                subdomain=self.mpop_url,
                                url_addons=f"""/ticket-api/api/integrator/status/{update_state_id}""",
                                request_type="GET",
                                payload_content=[],
                            )
                            if check_status_request:
                            
                                check_status = json.loads(check_status_request.text)

                                if check_status['success'] == False:

                                    self.logger.error(f"""Update file uploaded successfuly but request success is {check_status['success']} | Reason: {check_status['message']}""")
                                    break
                    
                    else:

                        self.logger.error(f"""Update request success is {update_state_response['success']} | Reason: {update_state_response['message']}""")

        else:

            update_payload = json.dumps(
                [
                    {
                        "hepsiburadaSku": products["id"],
                        "merchantSku": products["sku"],
                        "availableStock": products["qty"],
                    }
                ]
            )
            update_request_raw = self.request_data(
                subdomain=self.listing_external_url,
                url_addons=f"""/stock-uploads""",
                request_type="POST",
                payload_content=update_payload,
            )
            if update_request_raw:

                update_state_id = json.loads(update_request_raw.text)["id"]

                while True:

                    check_status_request = self.request_data(
                        subdomain=self.listing_external_url,
                        url_addons=f"""/stock-uploads/id/{update_state_id}""",
                        request_type="GET",
                        payload_content=[],
                    )
                    if check_status_request:

                        check_status = json.loads(check_status_request.text)

                        if check_status["status"] == "Done" and not check_status["errors"]:

                            self.logger.info(
                                f"""Product with code: {products["sku"]}, New value: {products["qty"]}"""
                            )
                            break

                        if check_status["errors"]:

                            self.logger.error(
                                f"""Product with code: {products["sku"]} failed to update || Reason: {check_status["errors"]}"""
                            )
                            break

                    else:

                        continue

    def get_listings(self, everyproduct: bool = False) -> list:
        """
        Retrieves stock data for products from HepsiBurada.

        Args:
            everyproduct (bool, optional): If True, returns all product data. Defaults to False.

        Returns:
            list: A list of product data.
        """

        self.logger.info("Fetching product data from HepsiBurada")

        listings_list = []

        try:

            data_request_raw = self.request_data(
                subdomain=self.listing_external_url,
                url_addons=f"?limit=1000",
                request_type="GET",
                payload_content=[],
            )
            formatted_data = json.loads(data_request_raw.text)

            for data in formatted_data["listings"]:
                if not everyproduct:

                    listings_list.append(
                        {
                            "id": data["hepsiburadaSku"],
                            "sku": data["merchantSku"],
                            "qty": data["availableStock"],
                            "price": data["price"],
                        }
                    )
                else:
                    listings_list.append(
                        {"sku": data["merchantSku"], "data": data})

            self.logger.info(f"Fetched {len(listings_list)} products")

            return listings_list

        except Exception as e:

            self.logger.error(f"Error fetching product data: {e}")

            return []

