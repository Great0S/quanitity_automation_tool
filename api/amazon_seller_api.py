""" importing necessary modules and libraries for performing various
 tasks related to handling data, making HTTP requests, and working with concurrency """

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib import parse
import csv
import gzip
import json
import os
import re
import shutil
import time
import requests
from rich import print as printr



client_id = os.environ.get('LWA_APP_ID')
client_secret = os.environ.get('LWA_CLIENT_SECRET')
refresh_token = os.environ.get('SP_API_REFRESH_TOKEN')
MarketPlaceID = os.environ.get("AMAZONTURKEYMARKETID")
AmazonSA_ID = os.environ.get('AMAZONSELLERACCOUNTID')
credentials = {
    'refresh_token': refresh_token,
    'lwa_app_id': client_id,
    'lwa_client_secret': client_secret
}

session = requests.session()


def get_access_token():
    """
    The function `get_access_token` retrieves an access token by sending a POST request to a specified
    URL with necessary parameters.
    :return: The function `get_access_token` is returning the access token obtained from the API
    response after making a POST request to the token URL with the provided payload containing the
    client ID, client secret, and refresh token.
    """

    token_url = "https://api.amazon.com/auth/o2/token"

    payload = f"""grant_type=refresh_token&client_id={client_id}&client_secret={
        client_secret}&refresh_token={refresh_token}"""

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }

    token_response = requests.request(
        "POST", token_url, headers=headers, data=payload, timeout=30)

    response_content = json.loads(token_response.text)

    access_token_data = response_content['access_token']

    return access_token_data


access_token = get_access_token()


def request_data(session_data=None, operation_uri='', params: dict = None, payload=None, method='GET'):
    """
    The function `request_data` sends a request to a specified API endpoint with optional parameters and
    handles various response scenarios.

    :param session: The `session` parameter is used to pass an existing session object for making HTTP
    requests. This can be helpful for maintaining the state of the session across multiple requests,
    such as handling cookies or other session-related data. If `session` is provided, the function will
    use it to make the request;
    :param operation_uri: The `operation_uri` parameter in the `request_data` function is used to specify
    the URI path for the API operation you want to call. It is a string that represents the specific
    endpoint or resource you are targeting within the Selling Partner API. This parameter is appended to
    the base endpoint URL to construct the
    :param params: The `params` parameter in the `request_data` function is a dictionary that contains
    key-value pairs of parameters that will be included in the API request URL as query parameters.
    These parameters are used to specify additional information or filters for the API request
    :type params: dict
    :param payload: The `payload` parameter in the `request_data` function is used to pass data that
    needs to be sent with the request. It can be a dictionary, list, or any other data structure that
    you want to include in the request body. This data will be sent along with the request to the
    specified
    :param method: The `method` parameter in the `request_data` function specifies the HTTP method to be
    used for the request. It has a default value of 'GET', but you can also specify other HTTP methods
    like 'POST', 'PUT', 'DELETE', etc, defaults to GET (optional)
    :return: The function `request_data` returns a JSON object if the initial request status code is
    either 200 or 400. If the status code is 403, it updates the session header with the access token
    and retries the request. If the status code is 429, it sleeps for 65 seconds and then retries the
    request. If the status code indicates an error other than 403 or 429,
    """

    endpoint_url = f'https://sellingpartnerapi-eu.amazon.com{operation_uri}?'

    if params:
        uri = '&'.join([f'{k}={params[k]}' for k, v in params.items()])
    else:
        uri = ''

    # Get the current time
    current_time = datetime.now(timezone.utc)

    # Format the time in the desired format
    formatted_time = current_time.strftime('%Y%m%dT%H%M%SZ')

    headers = {
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'x-amz-access-token': f'{access_token}',
        'x-amz-date': formatted_time
    }
    while True:

        if session_data:

            session_data.headers = headers

            init_request = session_data.get(f"{endpoint_url}{uri}",
                                       data=payload)

        else:

            init_request = requests.request(method,
                                            f"{endpoint_url}{uri}",
                                            headers=headers,
                                            data=payload,
                                            timeout=30)

        if init_request.status_code in (200, 400):

            jsonify = json.loads(init_request.text)

            return jsonify

        if init_request.status_code == 403:

            session_data.headers['x-amz-access-token'] = access_token

        elif init_request.status_code == 429:

            time.sleep(65)

        else:

            error_message = json.loads(init_request.text)[
                'errors'][0]['message']

            if re.search('not found', error_message):

                return None

            else:

                printr(f"An error has occured || {error_message}")

                return None


def spapi_get_orders():
    """
    The function `spapi_get_orders` retrieves orders with a status of 'Shipped' from a specified
    marketplace and processes them in batches of 30.
    """

    params = {
        'MarketplaceIds': MarketPlaceID,
        'OrderStatuses': 'Shipped',
        'MaxResultsPerPage': 100,
        'CreatedAfter': "2019-10-07T17:58:48.017Z"}

    formatted_data = request_data("/orders/v0/orders/", params)['payload']

    orders = formatted_data['Orders']

    orders_dict = []

    request_count = 1

    count = 0

    next_token = formatted_data.get('NextToken')

    def spapi_getorderitems(max_requests, orders_list):
        """
        The function `spapi_getOrderItems` retrieves order items data for a list of orders and processes
        it to extract basic order information.

        :param max_requests: The `max_requests` parameter in the `spapi_getOrderItems` function
        represents the maximum number of requests that can be made before processing the collected data.
        In this case, it is used to control how many requests are made before processing the order items
        data
        :param orders_list: It seems like the code snippet you provided is incomplete. You mentioned
        that you wanted to provide information about the `orders_list`, but the code snippet cuts off
        before the `orders_list` is shown. Could you please provide the `orders_list` data so that I can
        assist you further with understanding the
        :return: The function `spapi_getOrderItems` returns the `orders_list` and `count` variables
        after processing the order items and extracting basic information about each order.
        """

        count = 0
        params = {
            'MarketplaceIds': MarketPlaceID}

        items_dict = []
        item_request_count = 1

        with ThreadPoolExecutor(max_workers=7) as executor:

            futures = []

            for order in orders_list:

                if 'ASIN' not in order:

                    futures.append(executor.submit(
                        request_data, f"""/orders/v0/orders/{
                            order['AmazonOrderId']}/orderItems""", params))

                    item_request_count += 1

                    if item_request_count % max_requests == 0:

                        for future in futures:

                            result = future.result()['payload']

                            if result:
                                items_dict.append(result)

                        orderbasic_info(
                            orders_list=orders_list, item_list=items_dict)

                        item_request_count = 0

                        items_dict = []

        return orders_list, count

    def orderbasic_info(item_list, orders_list):
        """
        The function `orderBasic_info` processes item and order data to extract relevant information and
        append it to a list.

        :param item_list: The `item_list` parameter is a list containing information about items, such
        as their ASIN, quantity shipped, price, seller SKU, title, etc. Each item in the list is
        represented as a dictionary with various key-value pairs
        :param orders_list: The function `orderbasic_info` takes two parameters: `item_list` and
        `orders_list`. The `item_list` parameter is a list of items with their information, and the
        `orders_list` parameter is a list of orders with order details
        :return: The function `orderbasic_info` returns two values: 
        1. The updated `orders_list` after processing the item and order data.
        2. The count of items processed and added to the `orders_list`.
        """

        city = None
        county = None
        count = 0

        for order in orders_list:

            for item_data in item_list:

                if item_data['AmazonOrderId'] == order['AmazonOrderId']:

                    try:
                        if "ShippingAddress" in order and order['FulfillmentChannel'] == "MFN" and isinstance(order['ShippingAddress'], dict):
                            city = order['ShippingAddress']['City']
                            county = order['ShippingAddress'].get(
                                'County', None)

                        # Create a dictionary for each item's information and append it to data_list
                        if 'ASIN' not in order:

                            for item in item_data['OrderItems']:

                                data = {
                                    "AmazonOrderId": order.get('AmazonOrderId', None),
                                    "OrderStatus": order.get('OrderStatus', None),
                                    "EarliestShipDate": order.get('EarliestShipDate', None),
                                    "LatestShipDate": order.get('LatestShipDate', None),
                                    "PurchaseDate": order.get('PurchaseDate', None),
                                    "City": city,
                                    "County": county,
                                    "ASIN": item.get('ASIN', None),
                                    "QuantityShipped": item.get('QuantityShipped', None),
                                    "Amount": item['ItemPrice']['Amount'],
                                    "SellerSKU": item.get('SellerSKU', None),
                                    "Title": item.get('Title', None)
                                }
                                orders_list.append(data)
                                count += 1

                    except KeyError:

                        if order in orders_list:

                            orders_list.remove(order)

        for index, order in enumerate(orders_list):
            for item_data in item_list:
                if item_data['AmazonOrderId'] == order['AmazonOrderId'] and 'ASIN' not in order:
                    del orders_list[index]

        return orders_list, count

    while orders:

        futures = []

        if next_token:
            params = {'MarketplaceIds': MarketPlaceID,
                      "NextToken": parse.quote(formatted_data['NextToken'])}

            futures = request_data("/orders/v0/orders/", params)

            result = futures['payload']

            next_token = result.get('NextToken', None)

            orders = result.get('Orders')

            request_count += 1

            for oi in orders:

                if orders_dict:

                    for io in orders_dict:

                        if io['AmazonOrderId'] == oi['AmazonOrderId']:

                            break

                        count += 1

                        orders_dict.append(oi)

                        break
                else:
                    count += 1
                    orders_dict.append(oi)

            printr(f'{count} orders has been added')

            if request_count % 30 == 0:
                printr(f"Processing {count} orders please wait!")

                spapi_getorderitems(30, orders_dict)

                printr(
                    f"Processed {count} orders || Orders left: {len(orders_dict)-count}")

                request_count = 0

            else:
                pass

    for data in orders_dict:

        if 'MarketplaceId' in data:

            spapi_getorderitems(30, orders_dict)

            break

    return orders_dict


def spapi_getlistings(every_product: bool = False):
    """
    The function `spapi_getListings` retrieves a report from an API, downloads and decompresses the
    report file, converts it from CSV to JSON format, and returns the inventory items as a list of
    dictionaries.
    :return: The `spapi_getListings` function returns a list of inventory items in JSON format after
    processing and downloading data from an Amazon API endpoint.
    """

    params = {
        'MarketplaceIds': MarketPlaceID,
        'reportTypes': 'GET_MERCHANT_LISTINGS_ALL_DATA'}

    report_id_request = request_data(
        session,
        "/reports/2021-06-30/reports/",
        params)

    report_id = report_id_request['reports'][0]['reportId']

    verify_report_status_request = request_data(session,
                                                f"""/reports/2021-06-30/reports/{
                                                    report_id}""",
                                                [])

    processing_status = verify_report_status_request['processingStatus']

    while True:

        if processing_status == 'DONE':

            report_document_id = verify_report_status_request['reportDocumentId']

            report_data = request_data(session,
                                       f"""/reports/2021-06-30/documents/{
                                           report_document_id}""",
                                       [])

            compression = report_data['compressionAlgorithm']

            report_link = report_data['url']

            break

    def download_and_save_file(url, save_path):
        """
        The function `download_and_save_file` downloads a file 
        from a given URL and saves it to a
        specified path on the local system.

        :param url: The `url` parameter in the `download_and_save_file` 
        function is the URL from which you want to download a file. This 
        URL will be used to send a GET request to retrieve the file
        content
        :param save_path: The `save_path` parameter in the `download_and_save_file` 
        function is the path where you want to save the downloaded file. It should 
        be a string representing the file path including the file name and extension 
        where you want to save the downloaded content. 
        """
        # Send a GET request to the URL
        response = requests.get(url, stream=True, timeout=30)

        # Raise an exception if the request was not successful
        response.raise_for_status()

        # Open the file for writing in binary mode
        with open(save_path, 'wb') as f:
            # Iterate over the content of the response and write it to the file
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def decompress_gzip_file(gzip_file_path, decompressed_file_path):
        """
        The function decompresses a gzip file to a specified decompressed file path.

        :param gzip_file_path: The `gzip_file_path` parameter is the file path to the 
        gzip-compressed file that you want to decompress. This file should be in gzip 
        format for the `gzip.open()`
        function to be able to decompress it
        :param decompressed_file_path: The `decompressed_file_path` parameter is the 
        path where you want to save the decompressed file after decompressing the gzip 
        file located at `gzip_file_path`. This parameter should be a string representing 
        the file path where you want to store the decompressed content
        """
        with gzip.open(gzip_file_path, 'rb') as f_in:

            with open(decompressed_file_path, 'wb') as f_out:

                shutil.copyfileobj(f_in, f_out)

    if report_link:
        file_saved = 'amazon-all-inventory.csv'

        if compression:
            file_download = f'amazon-all-inventory-{report_id}.{compression}'
            file_saved = f'amazon-all-inventory-{report_id}.csv'
            download_and_save_file(report_link, file_download)
            decompress_gzip_file(file_download, file_saved)

    def csv_to_json(filename=""):
        """
        The `csv_to_json` function reads a CSV file, removes the Byte Order Mark (BOM) character if
        present, and converts the data into a list of dictionaries.
        """

        def remove_bom(text):
            """
            The function `remove_bom` removes the Byte Order Mark (BOM) character from the beginning 
            of a text if present.
            """

            # Remove the BOM character if present
            if text.startswith('\ufeff'):

                return text[1:]

            return text

        with open(filename, mode='r', newline='', encoding='utf-8-sig') as csv_file:

            csv_reader = csv.DictReader(csv_file, delimiter='\t')

            dict_list = []

            for row in csv_reader:

                clean_row = {remove_bom(key): remove_bom(val)
                             for key, val in row.items()}

                dict_list.append(clean_row)

        return dict_list

    inv_items = csv_to_json(file_saved)

    def get_item_details(session_data, included_data, every_product: bool = False):

        request_count = 0

        amazon_products = []

        params = {"marketplaceIds": MarketPlaceID,
                  "issueLocale": 'en_US',
                  "includedData": included_data}

        with ThreadPoolExecutor(max_workers=5) as executor:

            futures = []

            for item in inv_items:

                if not re.search('_fba', item['seller-sku']):

                    sku = item['seller-sku']

                else:

                    continue

                futures.append(executor.submit(
                    request_data, session_data, f"""/listings/2021-08-01/items/{AmazonSA_ID}/{
                        sku}""", params))

                request_count += 1

                if request_count >= 10:

                    for future in futures:

                        result = future.result()

                        if not every_product and result:

                            # price = item_request['attributes']['purchasable_offer'][0]['our_price'][0]['schedule'][0]['value_with_tax']

                            if 'quantity' in result['fulfillmentAvailability'][0]:

                                quanitity = result['fulfillmentAvailability'][0]['quantity']

                                if result['summaries']:

                                    asin = result['summaries'][0]['asin']

                            else:

                                continue

                            amazon_products.append(
                                {'sku': result['sku'], 'id': asin, 'qty': quanitity})

                        elif every_product and result:

                            amazon_products.append(result)

                    time.sleep(5)

                    request_count = 0

                    futures = []

        return amazon_products

    products = get_item_details(
        session, included_data='summaries,attributes,fulfillmentAvailability',
        every_product=every_product)

    printr('[white]Amazon[/white] products data request is successful. Response: OK')

    return products


def filter_order_data(orders_list, order, result, items):
    """
    The function `filter_orderData` updates order data in a list based on specified items and order
    information.

    :param orders_list: The `orders_list` parameter in the `filter_orderData` function seems to be a
    list of orders. The function appears to iterate over each item in the `items` parameter, extract
    specific data from each item, and then update the corresponding order in the `orders_list` with this
    extracted data
    :param order: The `order` parameter seems to be missing in the provided code snippet. Could you
    please provide the definition or explanation of the `order` parameter so that I can assist you
    further with the `filter_orderData` function?
    :param result: The `result` parameter in the `filter_orderData` function seems to be a dictionary
    containing order data. The function iterates over a list of items and updates the order data in the
    `orders_list` based on certain conditions. The `result` dictionary is used to retrieve the
    'AmazonOrderId
    :param items: The `items` parameter in the `filter_orderData` function seems to be a list of items
    that contain information about an order, such as ASIN, QuantityShipped, Amount, SellerSKU, and
    Title. The function iterates over these items and updates the corresponding order information in the
    `
    :return: The function `filter_orderData` is returning the updated `orders_list` after filtering and
    updating the order data based on the provided items.
    """

    for item in items:

        try:

            printr(result.get('AmazonOrderId', None))

            data = {
                "ASIN": item.get('ASIN', None),
                "QuantityShipped": item.get('QuantityShipped', None),
                "Amount": item['ItemPrice']['Amount'],
                "SellerSKU": item.get('SellerSKU', None),
                "Title": item.get('Title', None)
            }

            for order_item in orders_list:

                if result['AmazonOrderId'] == order_item['AmazonOrderId']:

                    orders_list.remove(order_item)

                    order_item.update(data)

                    orders_list.append(order_item)

                    break

        except KeyError:

            if order in orders_list:

                orders_list.remove(order)

            continue

    return orders_list


def save_to_csv(data, filename=""):
    """
    The function `save_to_csv` takes a list of dictionaries, extracts keys from the dictionaries, and
    writes the data to a CSV file.

    :param data: The `data` parameter in the `save_to_csv` function is expected to be a list of
    dictionaries where each dictionary represents a row of data to be written to the CSV file. Each
    dictionary should have keys that represent the column headers in the CSV file, and the values
    represent the data for each
    :param filename: The `filename` parameter in the `save_to_csv` function is a string that represents
    the name of the CSV file where the data will be saved. If no filename is provided, the default value
    is an empty string
    """

    if data:

        keys = set()

        for item in data:

            keys.update(item.keys())

        with open(f"{filename}_data_list.csv",
                  "w",
                  newline='',
                  encoding="utf-8") as csvfile:

            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))

            file_writer.writeheader()

            for d in data:

                file_writer.writerow(d)


def spapi_update_listing(product):
    """
    The function `spapi_updateListing` updates a product listing on Amazon Seller Central with a new
    quantity value.

    :param product: The `spapi_updateListing` function is designed to update a listing on Amazon 
    Seller Central using the Selling Partner API
    """

    sku = product['sku']

    qty = product['qty']

    params = {
        'marketplaceIds': MarketPlaceID,
        'issueLocale': 'en_US'}

    data_payload = json.dumps({
        "productType": "HOME_BED_AND_BATH",
        "patches": [
            {
                "op": "replace",
                "path": "/attributes/fulfillment_availability",
                "value": [
                    {
                        "fulfillment_channel_code": "DEFAULT",
                        "quantity": qty,
                        "marketplace_id": "A33AVAJ2PDY3EV"
                    }
                ]
            }
        ]
    })

    listing_update_request = request_data(
        operation_uri=f"/listings/2021-08-01/items/{AmazonSA_ID}/{sku}",
        params=params,
        payload=data_payload,
        method='PATCH')

    if listing_update_request and listing_update_request['status'] == 'ACCEPTED':

        printr(f"""[white]Amazon[/white] product with code: {
                           product["sku"]}, New value: [green]{product["qty"]}[/green]""")

    else:

        printr(f"""[white]Amazon[/white] product with code: {product["sku"]} failed
              to update || Reason: [red]{listing_update_request}[/red]""")
