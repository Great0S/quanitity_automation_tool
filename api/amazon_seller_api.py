from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
import re
import shutil
import time
import requests
from simple_dotenv import GetEnv
from sp_api.api import Catalog, Reports, Orders
from sp_api.base import SellingApiException, Marketplaces
from sp_api.base.reportTypes import ReportType
from datetime import datetime, timedelta, timezone

from urllib import parse


client_id = str(GetEnv('LWA_APP_ID'))
client_secret = str(GetEnv('LWA_CLIENT_SECRET'))
refresh_token = str(GetEnv('SP_API_REFRESH_TOKEN'))
MarketPlaceID = str(GetEnv("AMAZONTURKEYMARKETID"))
AmazonSA_ID = str(GetEnv('AMAZONSELLERACCOUNTID'))
credentials = {
    'refresh_token': refresh_token,
    'lwa_app_id': client_id,
    'lwa_client_secret': client_secret
}

session = requests.session()


def get_access_token():

    token_url = "https://api.amazon.com/auth/o2/token"

    payload = f'grant_type=refresh_token&client_id=
    {client_id}&client_secret=
    {client_secret}&refresh_token=
    {refresh_token}'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }

    token_response = requests.request(
        "POST", token_url, headers=headers, data=payload)

    response_content = json.loads(token_response.text)

    access_token = response_content['access_token']

    return access_token


access_token = get_access_token()


def requestData(session = None, operation_uri = '', params: dict = {}, payload=[], method='GET'):

    Endpoint_url = f'https://sellingpartnerapi-eu.amazon.com{operation_uri}?'

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

        if session:

            session.headers = headers

            init_request = session.get(f"{Endpoint_url}{uri}", 
                                       data=payload)

        else:

            init_request = requests.request(method,
                                            f"{Endpoint_url}{uri}", 
                                            headers=headers, 
                                            data=payload)

        if init_request.status_code == 200 or init_request.status_code == 400:

            jsonify = json.loads(init_request.text)

            return jsonify
        
        elif init_request.status_code == 403:

            session.headers['x-amz-access-token'] = access_token

        elif init_request.status_code == 429:

            time.sleep(65)

        else:

            error_message = json.loads(init_request.text)[
                'errors'][0]['message']
            
            if re.search('not found', error_message):

                return None
            
            else:

                print(f"An error has occured || {error_message}")

                return None


def spapi_getOrders():

    params = {
        'MarketplaceIds': MarketPlaceID,
        'OrderStatuses': 'Shipped',
        'MaxResultsPerPage': 100,
        'CreatedAfter': "2019-10-07T17:58:48.017Z"}

    # rate = int(1 / rate_limit)

    formatted_data = requestData("/orders/v0/orders/", params)['payload']

    orders = formatted_data['Orders']

    orders_dict = []

    request_count = 1

    count = 0

    next_token = formatted_data.get('NextToken')

    while orders:

        futures = []

        if next_token:
            params = {'MarketplaceIds': MarketPlaceID,
                      "NextToken": parse.quote(formatted_data['NextToken'])}

            futures = requestData("/orders/v0/orders/", params)

            result = futures['payload']

            next_token = result.get('NextToken', None)

            orders = result.get('Orders')

            request_count += 1

            for oi in orders:
                if orders_dict:
                    for io in orders_dict:
                        if io['AmazonOrderId'] == oi['AmazonOrderId']:
                            break
                        else:
                            count += 1
                            orders_dict.append(oi)
                            break
                else:
                    count += 1
                    orders_dict.append(oi)

            print(f'{count} orders has been added')

            if request_count % 30 == 0:
                print(f"Processing {count} orders please wait!")

                spapi_getOrderItems(30, orders_dict)

                print(
                    f"Processed {count} orders || Orders left: {len(orders_dict)-count}")

                request_count = 0

            else:
                pass

    for data in orders_dict:

        if 'MarketplaceId' in data:

            spapi_getOrderItems(30, orders_dict)

            break
        else:
            continue

    def spapi_getOrderItems(max_requests, orders_list):
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
                        requestData, f"/orders/v0/orders/{order['AmazonOrderId']}/orderItems", params))

                    item_request_count += 1

                    if item_request_count % max_requests == 0:

                        for future in futures:

                            result = future.result()['payload']

                            if result:
                                items_dict.append(result)

                        orderBasic_info(
                            orders_list=orders_list, item_list=items_dict)

                        item_request_count = 0

                        items_dict = []

        def orderBasic_info(item_list, orders_list):

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
                            pass

            for index, order in enumerate(orders_list):
                for item_data in item_list:
                    if item_data['AmazonOrderId'] == order['AmazonOrderId'] and 'ASIN' not in order:
                        del orders_list[index]

            return orders_list, count

        return orders_list, count

    return orders_dict


def spapi_getListings(everyProduct: bool = False):
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

    report_id_request = requestData(
        session, 
        "/reports/2021-06-30/reports/", 
        params)

    report_id = report_id_request['reports'][0]['reportId']

    verify_report_status_request = requestData(session,
                                               f'/reports/2021-06-30/reports/{report_id}', 
                                               [])

    processingStatus = verify_report_status_request['processingStatus']

    while True:

        if processingStatus == 'DONE':

            reportDocumentId = verify_report_status_request['reportDocumentId']

            report_data = requestData(session,
                                      f'/reports/2021-06-30/documents/{reportDocumentId}', 
                                      [])

            compression = report_data['compressionAlgorithm']

            report_link = report_data['url']

            break
        else:
            pass

    def download_and_save_file(url, save_path):
        """
        The function `download_and_save_file` downloads a file from a given URL and saves it to a
        specified path on the local system.

        :param url: The `url` parameter in the `download_and_save_file` function is the URL from which
        you want to download a file. This URL will be used to send a GET request to retrieve the file
        content
        :param save_path: The `save_path` parameter in the `download_and_save_file` function is the path
        where you want to save the downloaded file. It should be a string representing the file path
        including the file name and extension where you want to save the downloaded content. For
        example, if you want to save the
        """
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

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

        :param gzip_file_path: The `gzip_file_path` parameter is the file path to the gzip-compressed
        file that you want to decompress. This file should be in gzip format for the `gzip.open()`
        function to be able to decompress it
        :param decompressed_file_path: The `decompressed_file_path` parameter is the path where you want
        to save the decompressed file after decompressing the gzip file located at `gzip_file_path`.
        This parameter should be a string representing the file path where you want to store the
        decompressed content
        """
        with gzip.open(gzip_file_path, 'rb') as f_in:

            with open(decompressed_file_path, 'wb') as f_out:

                shutil.copyfileobj(f_in, f_out)

    if report_link:
        file_saved = f'amazon-all-inventory.csv'

        if compression:
            file_download = f'amazon-all-inventory-{report_id}.{compression}'
            file_saved = f'amazon-all-inventory-{report_id}.csv'
            download_and_save_file(report_link, file_download)
            decompress_gzip_file(file_download, file_saved)

    def csv_to_json(filename=""):
        """
        The `csv_to_json` function reads a CSV file, removes the Byte Order Mark (BOM) character if
        present, and converts the data into a list of dictionaries.

        :param filename: The `csv_to_json` function you provided is designed to read a CSV file with
        tab-delimited values, remove the Byte Order Mark (BOM) character if present, and convert the
        data into a list of dictionaries where each dictionary represents a row in the CSV file
        :return: The `csv_to_json` function is returning a list of dictionaries where each dictionary
        represents a row of data from the CSV file specified by the `filename` parameter. The function
        reads the CSV file, removes the Byte Order Mark (BOM) character if present, and converts each
        row into a dictionary where the keys are the column headers and the values are the corresponding
        values in the row.
        """

        def remove_bom(text):
            """
            The function `remove_bom` removes the Byte Order Mark (BOM) character from the beginning of
            a text if present.

            :param text: The `remove_bom` function is designed to remove the Byte Order Mark (BOM)
            character from the beginning of a text if it is present. The BOM character is a special
            Unicode character (U+FEFF) that is sometimes added at the beginning of a text file to
            indicate the
            :return: The function `remove_bom` is returning the input text with the Byte Order Mark
            (BOM) character removed if it is present at the beginning of the text. If the BOM character
            is not present, the function returns the original text unchanged.
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

    def get_item_details(session, includedData, everyProduct: bool = False):

        request_count = 0

        amazon_products = []

        params = {"marketplaceIds": MarketPlaceID,
                  "issueLocale": 'en_US',
                  "includedData": includedData}

        with ThreadPoolExecutor(max_workers=5) as executor:

            futures = []

            for item in inv_items:

                if not re.search('_fba', item['seller-sku']):

                    sku = item['seller-sku']

                else:

                    continue

                futures.append(executor.submit(
                    requestData, session, f'/listings/2021-08-01/items/{AmazonSA_ID}/{sku}', params))

                request_count += 1

                if request_count >= 10:

                    for future in futures:

                        result = future.result()

                        if not everyProduct and result:

                            # price = item_request['attributes']['purchasable_offer'][0]['our_price'][0]['schedule'][0]['value_with_tax']

                            if 'quantity' in result['fulfillmentAvailability'][0]:

                                quanitity = result['fulfillmentAvailability'][0]['quantity']

                                if result['summaries']:

                                    asin = result['summaries'][0]['asin']

                            else:

                                continue

                            amazon_products.append(
                                {'sku': result['sku'], 'id': asin, 'qty': quanitity})

                        elif everyProduct and result:

                            amazon_products.append(result)

                    time.sleep(5)

                    request_count = 0

                    futures = []

        return amazon_products

    products = get_item_details(
        session, 'summaries,attributes,fulfillmentAvailability', everyProduct)
    
    print(f'Amazon products data request is successful. Response: OK')

    return products


def filter_orderData(orders_list, order, result, items):

    for item in items:

        try:

            print(result.get('AmazonOrderId', None))

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

        except KeyError as ex:

            if order in orders_list:

                orders_list.remove(order)

            continue

    return orders_list


def save_to_csv(data, filename=""):

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


def spapi_updateListing(product):

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

    listing_update_request = requestData(
        operation_uri=f"/listings/2021-08-01/items/{AmazonSA_ID}/{sku}", 
        params=params, 
        payload=data_payload, 
        method='PATCH')

    if listing_update_request and listing_update_request['status'] == 'ACCEPTED':

        print(f'Amazon product with code: {sku}, New value: {qty}')

    else:

        print(
            f'Amazon product with code: {product["sku"]} failed to update || Reason: {listing_update_request}')