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

    url = "https://mpop.hepsiburada.com/product/api/products/import?version=1"

    ready_data = []
    size = ''
    color = ''
    shape = ''
    category_baseAttrs = ''
    category_attrs = ''
    category_varyantAttrs = ''
    category_subs = ''

    for data in items:

        data = items[data][0]['data']
        images = data['images']
        category = data['categoryName']

        categories = get_categories()

        for cat_data in categories:
            
            item_data = categories[cat_data]
            category_subs = item_data['paths']

            if re.search(category, cat_data):
                
                category = item_data['parentCategoryId']                
                category_baseAttrs = item_data['baseAttributes']
                category_attrs = item_data['attributes']
                category_varyantAttrs = item_data['variantAttributes']

            else:

                for category_sub in category_subs:

                    if re.search(category, category_sub):

                        pass



        if len(images) < 5:
            for i in range(5 - len(images)):
                images.append({'url': 'None'})

        for atrr in data['attributes']:

            if re.search('Boyut/Ebat', atrr['attributeName']):

                size = atrr['attributeValue']

            if re.search('Renk', atrr['attributeName']):

                color = atrr['attributeValue']

            
            if re.search('Şekil', atrr['attributeName']):

                shape = atrr['attributeValue']

            else:

                shape = 'Dikdörtgen'

        listing_details = {
            "categoryId": category,
            "merchant": store_id,
            "attributes": {
                "merchantSku": data.get('stockCode', None),
                "VaryantGroupID": data.get('productMainId', None),
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
                "sekil_product_property": shape,
                "00005JUG": "Var",  # Kaymaz Taban Var/Yok
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


    response = requests.post(url, files=files,headers=headers)

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


def get_categories():

    url = "https://mpop.hepsiburada.com/product/api/categories/get-all-categories?size=10000"

    payload = {}
    categories = {}
    file_name = 'hp_categories.json'

    category_response = requests.request("GET", url, headers=headers, data=payload)
    category_response_data = json.loads(category_response.text)
    total_pages = category_response_data['totalPages']
    page = 1

    if os.path.exists(file_name):

        with open(file_name, 'r', encoding='utf-8') as json_file:

            file_data = json.load(json_file)

        return file_data

    while page <= total_pages:

        for category in category_response_data['data']:

            baseAttrs = []
            attrs = []
            variyantAttrs = []
            parentCategoryId = category['parentCategoryId']

            if parentCategoryId:

                property_url = f'https://mpop.hepsiburada.com/product/api/categories/{category['parentCategoryId']}/attributes'
                property_response = requests.request("GET", property_url, headers=headers, data=payload)
                property_data = json.loads(property_response.text)['data']

                if property_data:

                    baseAttrs = property_data['baseAttributes']
                    attrs = property_data['attributes']
                    variyantAttrs = property_data['variantAttributes']

                categories[category['displayName']] = {'parentCategoryId': category['parentCategoryId'],
                                                   'paths': category['paths'],
                                                   'baseAttributes': baseAttrs,
                                                   'attributes': attrs,
                                                   'variantAttributes': variyantAttrs}

        page += 1
        category_response = requests.request("GET", url+f'&page={page}', headers=headers, data=payload)
        category_response_data = json.loads(category_response.text)

    with open(file_name, 'w') as json_file:

        json.dump(categories, json_file)

    return file_name

