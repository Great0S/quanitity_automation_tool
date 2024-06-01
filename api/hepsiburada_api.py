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
    style = ''
    category_attrs = ''

    categories = get_categories()

    for data in items:

        data = items[data][0]['data']
        images = data['images']
        category = data['categoryName']
        product = data['title']

        for cat_data in categories:

            item_data = categories[cat_data]

            if re.search(cat_data, product):

                category = item_data['categoryId']
                attrs = item_data['baseAttributes'] + item_data['attributes'] + item_data['variantAttributes']
                category_attrs_list = [{x['id']: x['name']} for x in attrs]
                category_attrs = {
                    a: b for d in category_attrs_list for a, b in d.items()}

                break

            elif category == cat_data:

                category = item_data['categoryId']
                attrs = item_data['baseAttributes'] + item_data['attributes'] + item_data['variantAttributes']
                category_attrs_list = [{x['id']: x['name']} for x in attrs]
                category_attrs = {a: b
                                  for d in category_attrs_list
                                  for a, b in d.items()}

                break

        for i in enumerate(images):

            category_attrs[f"Image{i[0]+1}"] = i[1]['url']
            if i[0] == 5:

                pass

        source_product_attrs = data['attributes']

        for atrr in source_product_attrs:

            if re.search('Boyut/Ebat', atrr['attributeName']):

                size = atrr['attributeValue']

            if re.search('Renk', atrr['attributeName']):

                color = atrr['attributeValue']

            if re.search('Tema', atrr['attributeName']):

                style = atrr['attributeValue']

            if re.search('Şekil', atrr['attributeName']):

                shape = atrr['attributeValue']

            else:

                shape = 'Dikdörtgen'

        category_attrs["merchantSku"] = data.get('stockCode', None)
        category_attrs["VaryantGroupID"] = data.get('productMainId', None)
        category_attrs["Barcode"] = data.get('barcode', None)
        category_attrs["UrunAdi"] = data.get('title', None)
        category_attrs["UrunAciklamasi"] = data.get('description', None)
        category_attrs["Marka"] = data.get('brand', "Myfloor")
        category_attrs["GarantiSuresi"] = 24
        category_attrs["kg"] = "1"
        category_attrs["tax_vat_rate"] = "8"
        category_attrs["price"] = data.get('salePrice', 0)
        category_attrs["stock"] = data.get('quantity', 0)
        category_attrs["Video1"] = ''        

        attrs_state = False


        if re.search('dip çubuğu', data['title']):

            category_attrs["renk_variant_property"] = color
            category_attrs["secenek_variant_property"] = ''

            attrs_state = True


        elif re.search('Maket Bıçağ', data['title']):

            category_attrs["adet_variant_property"] = 1
            category_attrs["ebatlar_variant_property"] = size

            attrs_state = True

        elif re.search(r'Koko|Kauçuk|Nem Alıcı Paspas|Kapı önü Paspası|Halı|Tatami|Kıvırcık|Comfort|Hijyen|Halı Paspas|Halıfleks Paspas', data['title']):

            category_attrs["00004LW9"] = style  #Desen / Tema"
            category_attrs["00005JUG"] = 'Var'  #Kaymaz Taban
            category_attrs["sekil"] = shape
            category_attrs["renk_variant_property"] = color
            category_attrs["00001CM1"] = size  #Ebatlar

            attrs_state = True

        if not attrs_state:

            lastItem = "Video1"
            category_attr_temp = {a: '' for i, a in enumerate(category_attrs) if i > list(category_attrs).index(lastItem)}   # This to zero non essential attributes
            category_attrs.update(category_attr_temp)

        listing_details = {
            "categoryId": category,
            "merchant": store_id,
            "attributes": category_attrs
        }

        ready_data.append(listing_details)

        # Write to JSON file
    with open('integrator.json', 'w', encoding='utf-8') as json_file:

        json.dump(ready_data, json_file)

    # printr(f"Creating new hepsiburada product with sku: {
        #    data['productMainId']}")

    files = {"file": ("integrator.json", open(
        "integrator.json", "rb"), "application/json")}
    
    headers['Accept'] = 'application/json'
    headers.pop('Content-Type')

    response = requests.post(url, files=files, headers=headers)

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

    if os.path.exists(file_name):

        with open(file_name, 'r', encoding='utf-8') as json_file:

            file_data = json.load(json_file)

            for category in file_data:

                if file_data[category]['baseAttributes']:

                    categories[category] = file_data[category]

                    continue

                baseAttrs, attrs, variyantAttrs = get_category_attrs(
                    payload, file_data[category])
                file_data[category]['baseAttributes'] = baseAttrs
                file_data[category]['attributes'] = attrs
                file_data[category]['variantAttributes'] = variyantAttrs

                categories[category] = file_data[category]

        if len(categories) == len(file_data):

            with open(file_name, 'w', encoding='utf-8') as json_file:

                json.dump(categories, json_file)

        return file_data

    return None


def get_category_attrs(payload, category):

    property_url = f'https://mpop.hepsiburada.com/product/api/categories/{
        category['categoryId']}/attributes'
    property_response = requests.request(
        "GET", property_url, headers=headers, data=payload)
    property_data = json.loads(property_response.text)['data']

    if property_data:

        baseAttrs = property_data['baseAttributes']
        attrs = property_data['attributes']
        variyantAttrs = property_data['variantAttributes']

    return baseAttrs, attrs, variyantAttrs
