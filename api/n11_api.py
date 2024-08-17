import csv
from datetime import date
import logging
import os
import re
import time
import requests
import xmltodict
from zeep import Client, Settings, xsd
from zeep.exceptions import Error
from typing import Any, Tuple, Optional, List, Dict, Union


class N11API:

    def __init__(self):
        # URLS
        self.base_url = "https://api.n11.com/ws"
        self.headers = {'Content-Type': 'text/xml; charset=utf-8'}

        # Auth 
        self.api_key = os.getenv('N11_KEY')
        self.api_secret = os.getenv('N11_SECRET')
        self.auth = {"appKey": self.api_key,"appSecret": self.api_secret}
        
        self.logger = logging.getLogger(__name__)

    def __create_client(self, Service: str = 'ProductService', url: str = 'https://api.n11.com/ws') -> Client:
        """
            Create a SOAP client for the given service.

            Args:
                service (str): The name of the service. Defaults to 'ProductService'.
                url (str): The base URL for the WSDL. Defaults to 'http://example.com'.

            Returns:
                Client: A Zeep client object for the specified service.
        """

        wsdl_url = f"{url}/{Service}.wsdl"
        settings = Settings(strict=False, 
                            xml_huge_tree=True,
                            xsd_ignore_sequence_order=True)
        try:

            client = Client(wsdl=wsdl_url, settings=settings)
            return client

        except Error as e:

            print(f"An error occurred: {e}")
            return None

    def __assign_vars(raw_xml: str, 
                response_namespace: str, 
                list_name: str, 
                error_message: bool = False, 
                namespace_id: str = 'ns3') -> Optional[Tuple[Any, Any]]:
        """
        Parse the raw XML response and extract the desired elements.

        Args:
            raw_xml (str): The raw XML response as a string.
            response_namespace (str): The namespace of the response element.
            list_name (str): The name of the list element to extract.
            error_message (bool): Flag to indicate if error messages should be returned.    Defaults to False.
            namespace_id (str): The namespace identifier. Defaults to 'ns3'.

        Returns:
            Optional[Tuple[Any, Any]]: A tuple containing the list of items and the total   number of pages, or None.
        """

        try:
            # XML raw data trimming
            revised_response = (
                raw_xml.replace(
                    """<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/  envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body>""",
                    "")).replace("""</SOAP-ENV:Body></SOAP-ENV:Envelope>""", "")

            # Parse the XML response into a dictionary using xmltodict library.
            response_json = xmltodict.parse(revised_response)

            # Access the response elements using the response_namespace and list_name   variables.
            response_data = response_json.get(f"{namespace_id}:{response_namespace}", 
                                              response_json['SOAP-ENV:Envelope']    ['SOAP-ENV:Body'].get(f"{namespace_id}: {response_namespace}"))

            if response_data:
                if list_name in response_data and not error_message:

                    items_list = next(iter(response_data[list_name].values()))
                    items_total_pages = response_data['pagingData']['pageCount']
                    return items_list, items_total_pages

                if error_message:

                    return response_data

            return None, None

        except Exception as e:

            print(f"An error occurred: {e}")
            return None, None

    def __process_products(self, products_list: List[Dict], every_product: bool, raw_elements: List[Dict], all_products: List[Dict]):
        """
        Process the list of products and append to the respective lists.

        :param products_list: List of products fetched from the API.
        :param every_product: Flag to determine if full product data should be appended.
        :param raw_elements: List to store simplified product data.
        :param all_products: List to store full product data.
        """
        for product in products_list:

            product_code = product.get("productSellerCode")
            product_price = product.get("displayPrice")
            stock_items = product.get("stockItems", {}).get("stockItem")

            if every_product:

                all_products.append({'sku': product_code, 'data': product})

            else:

                product_qty = extract_quantity(stock_items, product_code)
                raw_elements.append({
                    "id": product.get("id"),
                    "sku": product_code,
                    "qty": product_qty,
                    "price": product_price,
                })

    def __extract_quantity(stock_items: Union[List[Dict], Dict], product_code: str) ->    Optional[int]:
        """
        Extract the quantity from stock items.

        :param stock_items: Stock item(s) of a product, can be a list or dict.
        :param product_code: Seller's product code.
        :return: The stock quantity as an integer, or None if not available.
        """
        if isinstance(stock_items, list):
            for stock_item in stock_items:
                if stock_item.get('sellerStockCode') == product_code:

                    return int(stock_item.get("quantity", 0))

        elif stock_items:

            return int(stock_items.get("quantity", 0))

        return None

    def __fetch_local_data(self) -> List[Dict]:
        """
        Placeholder function for fetching local data.
        """
        # Implement logic for fetching cached/local data if needed
        self.logger.info("Fetching local data is not yet implemented.")
        return []

    def __flatten_dict(self, data, prefix=""):
        """
        Recursively flatten a nested dictionary.

        :param data: The dictionary to flatten.
        :param prefix: The prefix to apply to each flattened key.
        :return: A flattened dictionary.
        """
        flattened = {}

        for key, value in data.items():

            new_prefix = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self.flatten_dict(value, new_prefix))

            elif isinstance(value, list):
                # Flatten lists and handle each item recursively
                for i, item in enumerate(value, start=1):

                    flattened.update(self.flatten_dict({f"{new_prefix}{i}": item}))
            else:
                # Directly add non-dict and non-list values
                flattened[new_prefix] = value

        return flattened

    def __looper(self, link, payload_dump, namespace, list_name, max_retries=10, backoff_factor=2):
        """
        Continuously makes API calls until a successful response is received or the retry   limit is reached.

        :param link: The URL to send the request to.
        :param payload_dump: The payload data to send in the request.
        :param namespace: The namespace to search for in the response.
        :param list_name: The name of the list to extract from the response.
        :param max_retries: The maximum number of retry attempts. Default is 10.
        :param backoff_factor: The backoff factor for retry delays (exponential growth).    Default is 2 seconds.

        :return: A tuple containing the orders list and the total orders.
        """
        retries = 0
        wait_time = 1

        while retries < max_retries:
            try:

                api_call_loop = requests.post(link, headers=self.headers, data=payload_dump,     timeout=30)

                # Check if the response is successful using a regex
                if re.search("success", api_call_loop.text, re.IGNORECASE):

                    orders_list, orders_total = self.assign_vars(api_call_loop.text, namespace,  list_name)
                    return orders_list, orders_total

            except requests.exceptions.RequestException as e:

                self.logger.error(f"Request failed: {e}")

            retries += 1
            self.logger.warning(f"Retrying... attempt {retries} of {max_retries}")
            time.sleep(wait_time)
            wait_time *= backoff_factor  # Exponential backoff

        # If the loop finishes without success
        self.logger.error("Max retries reached without success.")
        return None, None

    def __save_to_csv(self, data, filename="data"):
        """
        Saves a list of dictionaries to a CSV file with the specified filename.

        :param data: A list of dictionaries to save to the CSV file.
        :param filename: The base name of the output file (without extension). Default is   'data'.
        :return: None
        """
        if not data:

            self.logger.warning("No data provided to save.")
            return

        # Generate a default filename if none is provided
        filename = filename if filename else "data"

        # Ensure the filename is safe and valid
        filename = os.path.splitext(filename)[0]  # Remove any existing extension
        csv_filename = f"{filename}_data_list.csv"

        try:
            # Collect all keys across dictionaries to ensure the CSV has a consistent   header
            keys = set()

            for item in data:

                keys.update(item.keys())

            # Open the file and write the data to CSV
            with open(csv_filename, "w", newline='', encoding="utf-8") as csvfile:

                file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))
                file_writer.writeheader()

                for item in data:

                    file_writer.writerow(item)

            self.logger.info(f"Data successfully saved to {csv_filename}")

        except IOError as e:

            self.logger.error(f"Failed to write to {csv_filename}: {e}")

    def _get_detailed_order_list(self, link):
        """
        The function `get_n11_detailed_order_list` sends a SOAP request to the 
        N11 API to retrieve a list of detailed orders and processes the response
        to extract relevant information.
        """

        payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"xmlns:sch="http://www.n11.com/ws/schemas">
                <soapenv:Header/>
                <soapenv:Body>
                    <sch:DetailedOrderListRequest>
                        <auth>
                            <appKey>{self.api_key}</appKey>
                            <appSecret>{self.api_secret}</appSecret>
                        </auth>
                        <searchData>
                            <productId></productId>
                            <status>Completed</status>
                            <buyerName></buyerName>
                            <orderNumber></orderNumber>
                            <productSellerCode></productSellerCode>
                            <recipient></recipient>
                            <sameDayDelivery></sameDayDelivery>
                            <period>
                                <startDate></startDate>
                                <endDate></endDate>
                            </period>
                            <sortForUpdateDate>true</sortForUpdateDate>
                        </searchData>
                        <pagingData>
                            <currentPage>0</currentPage>
                            <pageSize>100</pageSize>
                        </pagingData>
                    </sch:DetailedOrderListRequest>
                </soapenv:Body>
            </soapenv:Envelope>
            """
        orders_url = f"{link}/orderService/"

        # This is used to send a SOAP request to the N11 API to retrieve a list of  products.
        api_call = requests.post(orders_url, 
                                 headers=self.headers, 
                                 data=payload, 
                                 timeout=30)
        current_page = 0

        # Status code of 200 means that the request was successful and the
        # server returned the expected response.
        if api_call.status_code == 200:

            orders_list, orders_total_pages = self.assign_vars(
                api_call, "DetailedOrderListResponse", "orderList")
            
            raw_elements = []

            # Process all pages found
            if orders_list is not None:
                while current_page < int(orders_total_pages):

                    for order in orders_list:
                        flattened_order = self.flatten_dict(order, "")
                        raw_elements.append(flattened_order)

                    current_page += 1
                    payload_dump = payload.replace(
                        "<currentPage>0</currentPage>",
                        f"<currentPage>{str(current_page)}</currentPage>",
                    )
                    orders_list, _ = self.looper(orders_url, 
                                            payload_dump, 
                                            "DetailedOrderListResponse", 
                                            "orderList")

            else:

                self.logger.error("No orders found in the response.")
        else:

            self.logger.error("Error:", api_call.text)

        if raw_elements:

            self.logger.info("Detailed orders list extraction is Successful. || Response:", api_call.reason)
        else:
            pass
        return raw_elements

    def _get_categories(self, save: bool = False):

        client = self.get_client('CategoryService')
        complete_list = {}

        TopLevelCategories = client.service.GetTopLevelCategories(auth=self.auth)
        categories_list = [{'id': x['id'], 
                            'name': x['name'], 
                            'subs': []}
                            for x in TopLevelCategories['categoryList']['category']]

        for item in categories_list:

            complete_list[item['name']] = item
            categoryId = item['id']

            SubCategories = client.service.GetSubCategories(auth=self.auth, 
                                                            categoryId=categoryId,
                                                            lastModifiedDate=xsd.SkipValue)

            if SubCategories['category']:

                SubCategories_list = [{'subCategory_id': x['id'], 
                                       'subCategory_name': x ['name'], 'sub_sub_category': [], 
                                       'attrs': []} 
                                       for x in SubCategories['category'][0]['subCategoryList']['subCategory']]

                for sub_item in SubCategories_list:

                    complete_list[item['name']]['subs'].append(sub_item)
                    categoryId = sub_item['subCategory_id']
                    SubSubCategories = client.service.GetSubCategories(auth=self.auth,
                                                                       categoryId=categoryId, 
                                                                       lastModifiedDate=xsd.SkipValue)

                    if SubSubCategories['category']:

                        SubSubCategories_list = [{'SubsubCategory_id': x['id'],
                                                  'SubsubCategory_name': x['name'], 'attrs': []} 
                                                  for x in SubSubCategories['category'][0]['subCategoryList']  ['subCategory']]

                        for sub_sub_item in SubSubCategories_list:

                            complete_list[item['name']]['subs'][SubCategories_list.index(sub_item)]['sub_sub_category'].append(sub_sub_item)
                            categoryId = sub_sub_item['SubsubCategory_id']

                            self.get_category_attrs(categoryId, 
                                                    complete_list, 
                                                    item, 
                                                    SubCategories_list.index   (sub_item))

                    self.get_category_attrs(categoryId)

    def _get_category_attrs(self, categoryId, item_list, item, index):

        client = self.__get_client('CategoryService')
        CategoryAttributes = client.service.GetCategoryAttributes(auth=self.auth,
                                                                  categoryId=categoryId,
                                                                  pagingData=1)

        if CategoryAttributes['category']:

            sub_categories_attr_list = [{'attr_name': x['name']}
                                        for x in CategoryAttributes['category'] ['attributeList']['attribute']]

            for attr in sub_categories_attr_list:

                item_list[item['name']]['subs'][index]['attrs'].append(
                    attr['attr_name'])

    def get_proucts(self,
                    every_product: bool = False,
                    local: bool = False,
                    page_size: int = 100,
                    timeout: int = 30
                    ) -> List[Dict[str, Union[str, int, Optional[float]]]]:
        """
        Fetch stock data from N11 API, either returning every product's detailed data
        or simplified stock and price information.

        :param every_product: Whether to return full data for every product.
        :param local: If True, use local data (placeholder for future implementation).
        :param page_size: Number of products per page.
        :param timeout: Request timeout in seconds.
        :return: A list of products with SKU, stock quantity, and price information.
        """
        if local:
            
            return fetch_local_data()

        payload_template = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
            <soapenv:Header/>
            <soapenv:Body>
                <sch:GetProductListRequest>
                    <auth>
                        <appKey>{api_key}</appKey>
                        <appSecret>{api_secret}</appSecret>
                    </auth>
                    <pagingData>
                        <currentPage>{current_page}</currentPage>
                        <pageSize>{page_size}</pageSize>
                    </pagingData>
                </sch:GetProductListRequest>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        link = self.base_url + "/ProductService/"
        current_page = 0
        all_products = []
        raw_elements = []

        # Status code of 200 means that the request was successful
        # and the server returned the expected response.
        while True:
            # Prepare the payload with the current page and page size
            payload = payload_template.format(api_key=self.api_key, api_secret=self.api_secret, current_page=current_page, page_size=page_size)

            try:

                response = requests.post(link, headers=self.headers, data=payload, timeout=timeout)
                response.raise_for_status()  # Raises an exception for 4xx/5xx status codes

            except requests.exceptions.RequestException as e:

                self.logger.error(f"Request failed: {e}")

                return []

            # Parse the response and extract products
            products_list, total_pages = assign_vars(response.text, "GetProductListResponse", "products")

            if products_list is None:

                self.logger.error("No products found in the response.")
                break

            process_products(products_list, every_product, raw_elements, all_products)

            current_page += 1

            if current_page >= int(total_pages):

                break

        self.logger.info(f"N11 fetched {len(raw_elements)} products")
        return all_products if every_product else raw_elements

    def add_proucts(self, data: Union[List[Dict], Dict]) -> None:
        
        current_date = date.today()
        formatted_date = current_date.strftime("%d/%m/%Y")

        for item in data:

            item_data = data[item][0]['data']
            groupCode = re.sub(r'\d+', '', item_data['productMainId'])
            attrs = {}

            for attr in item_data['attributes']:
                attr_name = ['Renk', 'Şekil', 'Boyut/Ebat',
                             'Taban', 'Hav Yüksekliği']

                for item in attr_name:
                    if re.search(attr['attributeName'], item):

                        attrs[attr['attributeName']] = attr['attributeValue']

            image_elements = []
            for i, image_url in enumerate(item_data['images'], start=1):

                image_elements.append(f"""<image>
                                      <url>{image_url['url']}</url>
                                      <order>{i}</order>
                                      </image>""")

            # Join all <image> elements into a single string
            images_string = "".join(image_elements)

            request_data = {
                "auth": {
                    "appKey": self.api_key,
                    "appSecret": self.api_secret,
                },
                "product": {
                    "productSellerCode": item_data['productMainId'],
                    "maxPurchaseQuantity": 5000,
                    "title": item_data['title'],
                    "description": re.sub(r'[\?]', '', item_data['description']),
                    "category": {"id": 1001621},
                    "price": item_data['listPrice'],
                    "domestic": True,
                    "currencyType": 1,
                    "images": [],
                    "approvalStatus": 1,
                    "attributes": {
                        "attribute": [
                            {"name": "Renk", "value": attrs.get('Renk', '')},
                            {"name": "Marka", "value": item_data['brand']},
                            #  {"name": "Şekil", "value": ""},
                            #  {"name": "Ölçüler", "value": ""},
                            #  {"name": "Taban Özelliği", "value": ""},
                            #  {"name": "Hav Yüksekliği", "value": ""}
                        ]
                    },
                    "productionDate": formatted_date,
                    "expirationDate": "",
                    "productCondition": 1,
                    "preparingDay": 3,
                    "discount": {"startDate": "", "endDate": "", "type": 1, "value": int(item_data['listPrice']) - int(item_data['salePrice'])},
                    "shipmentTemplate": "Kargo",
                    "stockItems": {
                        "stockItem": [
                            {
                                "gtin": item_data['barcode'],
                                "quantity": item_data['quantity'],
                                "sellerStockCode": item_data['productMainId'],
                                "optionPrice": item_data['listPrice'],
                                "n11CatalogId": "",
                                "attributes": [],
                                "images":
                                    image_elements,
                            }
                        ]
                    },
                    "groupAttribute": "Adet",
                    "groupItemCode": groupCode,
                    "itemName": "",
                    "sellerNote": "",
                    "unitInfo": {
                        "unitWeight": 0,
                        "unitType": 0,
                    },
                },
            }

            client = get_client()
            response = client.service.SaveProduct(**request_data)

            if response.status_code == 200:

                if re.search('errorMessage', response.text) or re.search('failure', response.text):

                    # error_message = assign_vars(
                    #     post_response, 'SaveProductResponse', '', True)

                    self.logger.error(f"""Request failure for product  {data['sku']} | Response: {response['result']['errorMessage']}""")

                else:

                    self.logger.error(f"""New product with code: {data["sku"]}""")

            elif response.status_code == 429:

                time.sleep(15)

            else:

                response.raise_for_status()
                self.logger.error(f"""Request for product {data['sku']} is unsuccessful | Response: {response.text}""")

    def update_proucts(self, data: Dict) -> None:
       
        post_payload = f"""
                            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
                              <soapenv:Header/>
                              <soapenv:Body>
                                <sch:UpdateStockByStockSellerCodeRequest>
                                  <auth>
                                    <appKey>{self.api_key}</appKey>
                                    <appSecret>{self.api_secret}</appSecret>
                                  </auth>
                                  <stockItems>
                                    <stockItem>
                                      <sellerStockCode>{data['sku']}</sellerStockCode>
                                      <quantity>{data['qty']}</quantity>
                                    </stockItem>
                                  </stockItems>
                                </sch:UpdateStockByStockSellerCodeRequest>
                              </soapenv:Body>
                            </soapenv:Envelope>
                            """

        post_response = requests.request(
            "POST", 
            self.base_url, 
            headers=self.headers, 
            data=post_payload, 
            timeout=30)

        if post_response.status_code == 200:

            if re.search('errorMessage', post_response.text) or re.search('failure', post_response.text):

                error_message = assign_vars(post_response.text, 'UpdateStockByStockSellerCodeResponse', '', True)
                self.logger.error(f"""Request failure for product {data['sku']} | Response: {error_message['result']['errorMessage']}""")

            else:

                self.logger.info(f"""Product with code: {data["sku"]}, New value: {data["qty"]}""")

        elif post_response.status_code == 429:

            time.sleep(15)

        else:

            post_response.raise_for_status()
            self.logger.error(f"""Request for product {data['sku']} is unsuccessful | Response: {post_response.text}""")

