from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
import shutil
import time
import requests
import os
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


def get_access_token():
    token_url = "https://api.amazon.com/auth/o2/token"
    payload = f'grant_type=refresh_token&client_id={client_id}&client_secret={
        client_secret}&refresh_token={refresh_token}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }

    token_response = requests.request(
        "POST", token_url, headers=headers, data=payload)
    response_content = json.loads(token_response.text)
    access_token = response_content['access_token']
    return access_token


def requestData(access_token, operation_uri, params: dict):

    Endpoint_url = f'https://sellingpartnerapi-eu.amazon.com{operation_uri}?'

    if params:
        uri = '&'.join([f'{k}={params[k]}' for k, v in params.items()])
    else:
        uri = ''

    # Get the current time
    current_time = datetime.now(timezone.utc)

    # Format the time in the desired format
    formatted_time = current_time.strftime('%Y%m%dT%H%M%SZ')
    report_header = {
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'x-amz-access-token': f'{access_token}',
        'x-amz-date': formatted_time
    }
    while True:

        orders_request = requests.get(
            f"{Endpoint_url}{uri}", headers=report_header, data=[])

        if orders_request.status_code == 200 or orders_request.status_code == 400:
            jsonify = json.loads(orders_request.text)
            break
        elif orders_request.status_code == 403:
            access_token = get_access_token()
            report_header['x-amz-access-token'] = access_token
        elif orders_request.status_code == 429:
            time.sleep(65)
        else:
            print(f"An error has occured || {Exception}")
            break

    return jsonify


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
                        county = order['ShippingAddress'].get('County', None)

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


def spapi_getOrders(rate_limit, max_requests):

    access_token = get_access_token()

    params = {
        'MarketplaceIds': MarketPlaceID,
        'OrderStatuses': 'Shipped',
        'MaxResultsPerPage': 100,
        'CreatedAfter': "2019-10-07T17:58:48.017Z"}

    rate = int(1 / rate_limit)

    formatted_data = requestData(
        access_token, "/orders/v0/orders/", params)['payload']
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
            futures = requestData(access_token, "/orders/v0/orders/", params)

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
            if request_count % max_requests == 0:
                print(f"Processing {count} orders please wait!")
                spapi_getOrderItems(0.5, 30, orders_dict, access_token)
                print(f"Processed {count} orders || Orders left: {
                      len(orders_dict)-count}")
                request_count = 0

            else:
                pass
    for data in orders_dict:
        if 'MarketplaceId' in data:
            spapi_getOrderItems(0.5, 30, orders_dict, access_token)
            break
        else:
            continue

    return orders_dict


def spapi_getOrderItems(rate_limit, max_requests, orders_list, access_token):

    count = 0
    params = {
        'MarketplaceIds': MarketPlaceID}

    rate = int(1 / rate_limit)

    items_dict = []
    item_request_count = 1

    with ThreadPoolExecutor(max_workers=7) as executor:

        futures = []

        for order in orders_list:
            if 'ASIN' not in order:
                futures.append(executor.submit(
                    requestData, access_token, f"/orders/v0/orders/{order['AmazonOrderId']}/orderItems", params))
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

    return orders_list, count


def spapi_getListings():

    access_token = get_access_token()
    params = {
        'MarketplaceIds': MarketPlaceID,
        'reportTypes': 'GET_MERCHANT_LISTINGS_ALL_DATA'}

    report_id_request = requestData(
        access_token, "/reports/2021-06-30/reports/", params)
    report_id = report_id_request['reports'][0]['reportId']
    verify_report_status_request = requestData(
        access_token, f'/reports/2021-06-30/reports/{report_id}', [])
    processingStatus = verify_report_status_request['processingStatus']
    while True:
        if processingStatus == 'DONE':
            reportDocumentId = verify_report_status_request['reportDocumentId']
            report_data = requestData(
                access_token, f'/reports/2021-06-30/documents/{reportDocumentId}', [])
            compression = report_data['compressionAlgorithm']
            report_link = report_data['url']
            break
        else:
            pass

    def download_and_save_file(url, save_path):
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

    print(f'{report_id} report has been created')

    return file_saved


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

        with open(f"{filename}_data_list.csv", "w", newline='', encoding="utf-8") as csvfile:
            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))
            file_writer.writeheader()
            for d in data:
                file_writer.writerow(d)


# report = spapi_getListings()
token = get_access_token()
links = requests.get('https://sellingpartnerapi-eu.amazon.com/catalog/2022-04-01/items/B0B45WZ39Z', params={"marketplaceIds": 'A33AVAJ2PDY3EV', 'IncludedData': ['attributes', 'dimensions', 'identifiers', 'images', 'productTypes', 'salesRanks', 'summaries', 'relationships', 'vendorDetails']}, headers={
    'Content-Type': 'application/json',
    'x-amz-access-token': token})
orders_list = spapi_getOrders(rate_limit=0.0166, max_requests=20)
save_to_csv(orders_list, 'amazon')
print('Done')
