import json
import os
from woocommerce import API
from rich import print as printr

wcapi = API(
    url="https://www.emanzemin.com",
    consumer_key=os.getenv('EMANZEMIN_KEY'),
    consumer_secret=os.getenv('EMANZEMIN_SECRET'),
    version="wc/v3"
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
            products_request = wcapi.get(
                'products', params={"per_page": 100, "page": count}).json()

            if len(products_request) == 100:

                pass

            else:

                return products

    else:

        print(f"Products request failed || Message: {products_request.text}")

        return None


def get_wordpress_products(everyproduct: bool = False):

    products = products_request()

    filtered_products = []

    for item in products:

        if everyproduct:

            filtered_products.append({'sku': item['sku'],
                                      'data': item})

        filtered_products.append({'id': item['id'],
                                  'sku': item['sku'],
                                  'price': int(item['price']),
                                  'qty': item['stock_quantity'],
                                  "stock_check": item['stock_status']})

    printr("[grey66]Wordpress[/grey66] products data request is successful. Response: [orange3]OK[/orange3]")

    return filtered_products


def update_wordpress_products(data):

    stock_status = ''

    if isinstance(data, dict):

        if int(data['qty']) > 0:

            stock_status = 'instock'

        else:

            stock_status = 'outofstock'

        update_request = wcapi.put(f"products/{data['id']}",
                                   {'stock_quantity': data['qty'],
                                    'stock_status': stock_status}).json()

        if update_request['stock_quantity'] == int(data['qty']):

            printr(f"""[grey66]Wordpress[/grey66] product success, sku: {
                data['sku']}, New stock: {
                data['qty']}""")

        else:

            printr(f"""[grey66]Wordpress[/grey66] product update failed, sku: {
                data['sku']}, New stock: {
                    data['qty']}""")
