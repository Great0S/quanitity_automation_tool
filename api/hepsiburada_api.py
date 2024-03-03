from datetime import datetime
import json
import re
import time
import requests
import os

# The code snippet is initializing some variables and setting up the headers for making API requests.
products = []

auth_hash = os.environ.get('HEPSIBURADAAUTHHASH')

store_id = os.environ.get('HEPSIBURADAMERCHENETID')

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {auth_hash}'
}


def request_data(subdomain, url_addons, request_type, payload_content):
    """
    The function `request_data` sends a request to a specified URL with specified headers, request type,
    and payload content.

    :param url_addons: The `url_addons` parameter is a string that represents any additional path or
    query parameters that need to be added to the base URL. It is appended to the base URL to form the
    complete URL for the API request
    :param request_type: The `request_type` parameter is the type of HTTP request to be made. It can be
    one of the following: "GET", "POST", "PUT", "DELETE", etc
    :param payload_content: The payload_content parameter is the data that you want to send in the
    request. It can be in various formats such as JSON, XML, or form data. The content of the payload
    will depend on the specific API you are working with and the data it expects
    :return: the response object from the API request.
    """
    payload = payload_content

    url = f"https://{subdomain}.hepsiburada.com{url_addons}"

    while True:

        api_request = requests.request(
            request_type, url, headers=headers, data=payload)

        if api_request.status_code == 200:
            return api_request
        elif api_request.status_code == 400:
            return None
        else:
            time.sleep(1)
            continue


def hbapi_stock_data(everyProduct: bool = False):

    listings_list = []

    data_request_raw = request_data(
        'listing-external', f"/Listings/merchantid/{store_id}?limit=1000", 'GET', [])

    formatted_data = json.loads(data_request_raw.text)

    for data in formatted_data['listings']:

        if not everyProduct:

            listings_list.append(
            {'id': data['hepsiburadaSku'], 'sku': data['merchantSku'], 'qty': data['availableStock']})

        else:

            listings_list.append(data)

    return listings_list


def hbapi_updateListing(product):

    stockUpdate_payload = json.dumps([{
        "hepsiburadaSku": product["id"],
        "merchantSku": product["sku"],
        "availableStock": product["qty"]
    }])

    stockUpdate_request_raw = request_data(
        'listing-external', f"/Listings/merchantid/{store_id}/stock-uploads", 'POST', stockUpdate_payload)

    update_stateId = json.loads(stockUpdate_request_raw.text)['id']

    checkStatus_request = request_data(
        'listing-external', f"/Listings/merchantid/{store_id}/stock-uploads/id/{update_stateId}", 'GET', [])

    checkStatus = json.loads(checkStatus_request.text)['status']

    if checkStatus == 'Done':
        print(
            f'Trendyol product with code: {product["sku"]}, New value: {product["qty"]}\n')

    else:
        print(
            f'Trendyol product with code: {product["sku"]} failed to update || Reason: {checkStatus}\n')


hbapi_updateListing()
