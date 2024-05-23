""" importing required libs for the script """
import os
import re
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

        if api_request.status_code == 400:

            error_message = json.loads(api_request.text)

            printr(
                f"""[orange_red1]HepsiBurada[/orange_red1] api [red]bad[/red] request || Payload: {
                    payload} || Message: {error_message['title']}""")

            return None

        printr(f"""[orange_red1]HepsiBurada[/orange_red1] api request failure || Message: {
            error_message}""")

        time.sleep(3)

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


def hpapi_add_listing(items):

    header = {
        "accept": "application/json",
        'Authorization': f'Basic {auth_hash}',
    }

    url = "https://mpop.hepsiburada.com/product/api/products/import?version=1"

    ready_data = []
    size = ''
    color = ''

    for data in items:

        data = items[data][0]['data']

        images = data['images']

        if len(images) < 5:
            for i in range(5 - len(images)):
                images.append({'url': 'None'})

        for atrr in data['attributes']:

            if re.search('Boyut/Ebat', atrr['attributeName']):

                size = atrr['attributeValue']

            if re.search('Renk', atrr['attributeName']):

                color = atrr['attributeValue']

        listing_details = {
            "categoryId": 60001364,
            "merchant": store_id,
            "attributes": {
                "merchantSku": data.get('productMainId', None),
                "VaryantGroupID": "",
                "Barcode": data.get('barcode', None),
                "UrunAdi": data.get('title', None),
                "UrunAciklamasi": data.get('description', None),
                "Marka": data.get('brand', "Myfloor"),
                "GarantiSuresi": 0,
                "kg": "1",
                "tax_vat_rate": "8",
                "price": data.get('salePrice', 0),
                "stock": data.get('quantity', 0),
                "Image1": images[0]['url'],
                "Image2": images[1]['url'],
                "Image3": images[2]['url'],
                "Image4": images[3]['url'],
                "Image5": images[4]['url'],
                "Video1": "",
                "renk_variant_property": color,
                "ebatlar_variant_property": size
            }
        }

        ready_data.append(listing_details)

        # Write to JSON file
    with open('integrator.json', 'w') as json_file:

        json.dump(ready_data[0], json_file)

    # printr(f"Creating new hepsiburada product with sku: {
            #    data['productMainId']}")

    files = { "file": ("integrator.json", open("integrator.json", "rb"), "application/json") }


    response = requests.post(url, files=files,headers=header)

    print(response.text)


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
