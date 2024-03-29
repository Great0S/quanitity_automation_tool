""" importing required libs for the script """
import os
import time
import json
import requests
from rich import print as printr
from rich import inspect


# The code snippet is initializing some variables and
# setting up the headers for making API requests.
products = []

auth_hash = os.environ.get('HEPSIBURADAAUTHHASH')

store_id = os.environ.get('HEPSIBURADAMERCHENETID')

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
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
            request_type, url, headers=headers, data=payload, timeout=30)

        if api_request.status_code == 200:

            return api_request

        if api_request.status_code == 400:

            printr(
                f"""[orange_red1]HepsiBurada[/orange_red1] product request has [red]failed[/red] ||
                Reason: {inspect(api_request)}""")

            return None

        time.sleep(1)

        continue


def hbapi_stock_data(every_product: bool = False):
    """
    This Python function retrieves stock data for products from HepsiBurada, 
    with an option to include all product details.

    :param every_product: The `every_product` parameter in the `hbapi_stock_data` 
    function is a boolean parameter that determines whether to retrieve data for 
    every product or just specific product information. When set to `True`, the 
    function will return data for all products available. When set to `False`, 
    the function will only, defaults to False. 
    :type every_product: bool (optional)
    :return: The function `hbapi_stock_data` returns a list of product data from 
    HepsiBurada. The data includes the product ID, SKU, and quantity available in 
    stock. If the `every_product` parameter is set to True, the function returns 
    all product data without filtering.
    """

    listings_list = []

    data_request_raw = request_data(
        'listing-external', f"/Listings/merchantid/{store_id}?limit=1000", 'GET', [])

    formatted_data = json.loads(data_request_raw.text)

    for data in formatted_data['listings']:

        if not every_product:

            listings_list.append(
                {'id': data['hepsiburadaSku'],
                 'sku': data['merchantSku'],
                 'qty': data['availableStock']})

        else:

            listings_list.append(data)

    printr("""[orange_red1]HepsiBurada[/orange_red1] products data request is successful.
           Response: OK""")

    return listings_list


def hbapi_update_listing(product):
    """
    This Python function updates stock information for a product on HepsiBurada platform and checks for
    any errors during the process.

    :param product: The `hbapi_updateListing` function seems to be updating stock information for a
    product on HepsiBurada platform. The function takes a `product` object as a parameter, which likely
    contains information such as the product ID, SKU, and quantity
    """

    stock_update_payload = json.dumps([{
        "hepsiburadaSku": product["id"],
        "merchantSku": product["sku"],
        "availableStock": product["qty"]
    }], ensure_ascii=False)

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
