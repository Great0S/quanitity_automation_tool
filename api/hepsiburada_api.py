""" importing required libs for the script """
import os
import time
import json
import requests
from rich import print as printr


# The code snippet is initializing some variables and
# setting up the headers for making API requests.
products = []

auth_hash = os.environ.get('HEPSIBURADAAUTHHASH')

store_id = os.environ.get('HEPSIBURADAMERCHENETID')

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {auth_hash}'
}


def request_data(subdomain, url_addons: str, request_type: str, payload_content: str):
    """
    The function `request_data` sends a request to a specified URL with 
    specified headers, request type,
    and payload content.
    """
    payload = payload_content

    url = f"https://{subdomain}.hepsiburada.com{url_addons}"

    while True:

        api_request = requests.request(
            request_type, url, headers=headers, data=payload, timeout=3000)

        if api_request.status_code == 200:

            return api_request

        error_message = json.loads(api_request.text)

        if api_request.status_code == 400:

            printr(
                f"""[orange_red1]HepsiBurada[/orange_red1] api [red]bad[/red] request || Payload: {
                    payload} || Message: {error_message['title']}""")

            return None

        printr(f"""[orange_red1]HepsiBurada[/orange_red1] api request failure || Message: {
            error_message}""")

        time.sleep(1)

        continue


def hbapi_stock_data(everyproduct: bool = False):
    """
    This Python function retrieves stock data for products from HepsiBurada, 
    with an option to include all product details.
    """

    listings_list = []

    data_request_raw = request_data(
        'listing-external', f"/Listings/merchantid/{store_id}?limit=1000", 'GET', [])

    formatted_data = json.loads(data_request_raw.text)

    for data in formatted_data['listings']:

        if not everyproduct:

            listings_list.append(
                {'id': data['hepsiburadaSku'],
                 'sku': data['merchantSku'],
                 'qty': data['availableStock'],
                 'price': data['price']
                 })

        else:

            listings_list.append({'sku': data['merchantSku'],
                                  'data': data})

    printr(
        """[orange_red1]HepsiBurada[/orange_red1] products request is successful. Reason: [orange3]OK[/orange3]""")

    return listings_list


def hbapi_update_listing(product):
    """
    This Python function updates stock information for a product on 
    HepsiBurada platform and checks for
    any errors during the process.

    :param product: The `hbapi_updateListing` function seems to be 
    updating stock information for a
    product on HepsiBurada platform. The function takes a `product` 
    object as a parameter, which likely
    contains information such as the product ID, SKU, and quantity
    """

    stock_update_payload = json.dumps([{
        "hepsiburadaSku": product["id"],
        "merchantSku": product["sku"],
        "availableStock": product["qty"]
    }])

    stock_update_request_raw = request_data(
        'listing-external', f"""/Listings/merchantid/{
            store_id}/stock-uploads""", 'POST', stock_update_payload)

    if stock_update_request_raw:

        update_state_id = json.loads(stock_update_request_raw.text)['id']

        while True:

            check_status_request = request_data(
                'listing-external', f"""/Listings/merchantid/{
                    store_id}/stock-uploads/id/{update_state_id}""", 'GET', [])

            if check_status_request:

                check_status = json.loads(check_status_request.text)

                if check_status['status'] == 'Done' and not check_status['errors']:

                    printr(f"""[orange_red1]HepsiBurada[/orange_red1] product with code: {
                           product["sku"]}, New value: [green]{product["qty"]}[/green]""")

                    break

                if check_status['errors']:

                    printr(f"""[orange_red1]HepsiBurada[/orange_red1] product with code: {
                           product["sku"]} [red]failed[/red] to update || Reason: [indian_red1]{
                        check_status["errors"]}[/indian_red1]""")

                    break

            else:

                continue
