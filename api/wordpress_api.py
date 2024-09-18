import json
import os
import re
from woocommerce import API
from app.config import logger


wcapi = API(
    url="https://www.emanzemin.com",
    consumer_key=os.getenv('EMANZEMIN_KEY'),
    consumer_secret=os.getenv('EMANZEMIN_SECRET'),
    version="wc/v3",
    timeout=3000
)


def products_request():

    products_request = wcapi.get('products', params={"per_page": 100}).json()
    products = []
    count = 1

    if products_request:

        while products_request:

            for product in products_request:

                products.append(product)

            count += 1
            products_request_raw = wcapi.get('products', params={"per_page": 100, "page": count})
            products_request = products_request_raw.json()

            if len(products_request) == 100:

                pass

            else:

                return products

    else:

        print(f"Products request failed || Message: {products_request.text}")

        return None


def get_wordpress_products(everyproduct: bool = False, local: bool = False):

    products = products_request()

    filtered_products = []

    for item in products:

        qty = 0

        if item['stock_quantity']:

            qty = item['stock_quantity']

        if everyproduct:

            filtered_products.append({'sku': item['sku'],
                                      'data': item})
        else:

            filtered_products.append({'id': item['id'],
                                      'sku': item['sku'],
                                      'price': float(item['price']),
                                      'qty': qty})

    logger.info(f"Wordpress fetched {len(filtered_products)} products")

    return filtered_products


def update_wordpress_products(product_data: dict):

    stock_status = ''

    if isinstance(product_data, dict):

        if int(product_data['qty']) > 0:

            stock_status = 'instock'

        else:

            stock_status = 'outofstock'

        update_request = wcapi.put(f"products/{product_data['id']}",
                                   {'stock_quantity': product_data['qty'],
                                    'stock_status': stock_status}).json()

        if update_request['stock_quantity'] == int(product_data['qty']):

            logger.info(f"""Product success, sku: {
                product_data['sku']}, New stock: {
                product_data['qty']}""")

        else:

            logger.error(f"""Product update failed, sku: {
                product_data['sku']}, New stock: {
                    product_data['qty']}""")


def create_wordpress_products(product_data):

    if isinstance(product_data, dict):

        categories = get_products_categories()

        for item in product_data:

            item_data = product_data[item][0]['data']

            category = ''

            if re.search('Merdiven', item_data['title']):

                category = [{'id': 24}, {'id': 17}]

            elif re.search('Çim|çim', item_data['title']):

                category = [{'id': 24}, {'id': 23}]

            elif re.search('Renkli&Kapı', item_data['title']):

                category = [{'id': 24}, {'id': 29}]

            elif re.search('kapı|Kapı', item_data['title']):

                category = [{'id': 24}, {'id': 29}]

            elif re.search('Minder|Tatami', item_data['title']):

                category = [{'id': 24}, {'id': 20}]

            elif re.search('Bıçak|Yapıştır', item_data['title']):

                category = [{'id': 18}]

            else:

                category = [{'id': 6}]

            attrs = """\n\nÜrün özellikleri: \n"""

            for attr in item_data['attributes']:

                if re.search('NoColor', attr['attributeValue']):

                    continue

                attrs += f"{attr['attributeName']}: {attr['attributeValue']}\n"

            images = [{'src': x['url'], 'name': item_data['title'],
                       'alt': item_data['title']} for x in item_data['images']]
            
            manage_stock = True
            stock_status = 'instock'
            
            if item_data['quantity'] == 0:

                stock_status = 'outofstock'
                manage_stock = False

            product_data = {
                "name": item_data['title'],
                "type": "simple",
                "sku": item_data['stockCode'],
                "manage_stock": manage_stock,
                "stock_quantity": item_data['quantity'],
                "stock_status": stock_status,
                "tax_status	": "taxable",
                "sale_price": str(item_data['salePrice']),
                "regular_price": str(item_data['listPrice']),
                "description": re.sub(r"[?]", '', item_data['description']) + attrs,
                "short_description": item_data['title'],
                "categories": category,
                "images": images,
            }

            create_product_request = wcapi.post(f"products",
                                                product_data)

            if create_product_request.status_code == 201:

                logger.info(f"""New product request is success, sku: {
                    item_data['stockCode']}, Details: {create_product_request.ok, create_product_request.reason}""")

            elif create_product_request.status_code == 400:

                error = json.loads(create_product_request.text)

                logger.error(f"""New product request failed for {item_data['stockCode']}!, message: {error['code']}, Details: {error['message']}""")

            else:

                logger.error(f"""Product request failed, sku: {
                    item_data['stockCode']}, Details: {create_product_request.text}""")


def get_products_categories():

    cats_list = []

    request_json = wcapi.get("products/categories").json()

    for item in request_json:

        cats_list.append({'id': item['id'], 'name': item['name']})

    return cats_list
