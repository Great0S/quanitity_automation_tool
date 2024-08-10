import logging
import requests
import json


logger = logging.getLogger(__name__)


def get_access_token():

    url = "https://isortagimgiris.pazarama.com/connect/token"

    payload = 'grant_type=client_credentials&scope=merchantgatewayapi.fullaccess'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic OTQ5NWRlYjQzYmQ4NDQ4OTg0NTRhMzI5NTIzYzNhN2E6NWJmM2I5MmRjNGQyNGM3ZmE2NDY3MWEzMjhlZWVjYTE='
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    response_data = json.loads(response.text)

    if response_data['success'] == True:

        access_token = response_data['data']['accessToken']

        return access_token

    else:

        logger.error(f'Access token request has failed || Reason: {
                     response.text}')


def request_data(method='GET', uri='', params=None, payload=None):
    """
    This Python function sends a request to the Pazarama API with specified method, URI, parameters, and
    payload, handling authentication and returning the response data if successful.
    """

    url = f"https://isortagimapi.pazarama.com/{uri}?"

    access_token = get_access_token()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.request(
        method, url, headers=headers, params=params, data=payload)

    if response.status_code == 200:

        response_data = json.loads(response.text)

        return response_data

    else:

        logger.error(f'Request has failed || Status code: {response.status_code} || Reason: {response.text}')

        return None


def getPazarama_productsList(everyProduct: bool = False, local: bool = False):
    """
    This Python function retrieves a list of products from Pazarama API and returns a subset of product
    data based on a specified condition.

    """

    products = []

    params = {
        'Approved': 'true',
        'Size': 250
    }

    products_list = request_data(uri='product/products', params=params)['data']

    if products_list:

        for product in products_list:

            if not everyProduct:

                products.append(
                    {'id': product['code'],
                     'sku': product['stockCode'],
                     'qty': product['stockCount'],
                     'price': product['salePrice']
                     })
            else:

                products.append(
                    {'sku': product['stockCode'],
                     'data': product
                     })

        logger.info(f'Pazarama fetched {len(products)} products')

        return products


def pazarama_updateRequest(product):
    """
    The function `pazarama_updateRequest` updates the stock count of a product on Pazarama platform
    based on the provided product information.

    :param product: The `pazarama_updateRequest` function takes a `product` parameter, which is expected
    to be a dictionary containing the following keys:
    """

    product_id = product['id']

    sku = product['sku']

    qty = product['qty']

    update_payload = json.dumps({
        "items": [
            {
                "code": product_id,
                "stockCount": int(qty)
            }
        ]
    }, ensure_ascii=False)

    update_request = request_data(
        'POST', 'product/updateStock', payload=update_payload)

    if update_request:

        if update_request['success'] == True:

            logger.info(f"""Product with code: {
                product["sku"]}, New value: [green]{product["qty"]}[/green]""")

        else:

            logger.error(f'Product with code: {sku} failed to update || Reason: {
                         update_request['data'][0]['error']}')
