from concurrent.futures import ThreadPoolExecutor
import csv
import json
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

    uri = '&'.join([f'{k}={params[k]}' for k, v in params.items()])

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
            jsonify = json.loads(orders_request.text)['payload']
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
                except KeyError:
                    if order in orders_list:
                        orders_list.remove(order)
                    pass
    
    for order in orders_list:
        for item_data in item_list:
            if item_data['AmazonOrderId'] == order['AmazonOrderId'] and 'ASIN' not in order:
                orders_list.remove(order)

    return orders_list


def spapi_getOrders(rate_limit, max_requests):

    access_token = get_access_token()

    params = {
        'MarketplaceIds': MarketPlaceID,
        'CreatedAfter': "2019-10-07T17:58:48.017Z"}

    rate = int(1 / rate_limit)

    formatted_data = requestData(access_token, "/orders/v0/orders/", params)
    orders = formatted_data['Orders']
    orders_dict = []
    request_count = 1
    next_token = formatted_data.get('NextToken')

    with ThreadPoolExecutor(max_workers=7) as executor:
        while orders:
            futures = []
            if next_token:
                params = {'MarketplaceIds': MarketPlaceID,
                          "NextToken": parse.quote(formatted_data['NextToken'])}
                futures.append(executor.submit(
                    requestData, access_token, "/orders/v0/orders/", params))
                next_token = None

            for future in futures:
                result = future.result()
                next_token = result.get('NextToken', None)
                orders = result.get('Orders')
                request_count += 1
                if request_count % max_requests == 0:
                    spapi_getOrderItems(0.5, 30, orders, access_token)
                    time.sleep(rate+5)
                    request_count = 0
                else:
                    pass

        spapi_getOrderItems(0.5, 30, orders_dict, access_token)

    return orders_dict


def spapi_getOrderItems(rate_limit, max_requests, orders_list, access_token):

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
                        result = future.result()
                        if result:
                            items_dict.append(result)
                    orderBasic_info(
                                orders_list=orders_list, item_list=items_dict)
                    item_request_count = 0
                    items_dict = []

    return orders_list


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


orders_list = spapi_getOrders(rate_limit=0.0166, max_requests=20)
save_to_csv(orders_list, 'amazon')
print('Done')
