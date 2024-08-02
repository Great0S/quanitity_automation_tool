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

    :param method: The `method` parameter in the `request_data` function specifies the HTTP method to be
    used for the request. By default, it is set to 'GET', but it can be overridden by providing a
    different HTTP method such as 'POST', 'PUT', 'DELETE', etc, defaults to GET (optional)
    :param uri: The `uri` parameter in the `request_data` function represents the endpoint or path of
    the API that you want to send the request to. It is a string that specifies the resource you are
    interacting with on the server. For example, if you want to retrieve user data, the `uri`
    :param params: The `params` parameter in the `request_data` function is used to pass any query
    parameters that need to be included in the request URL. These parameters are typically used for
    filtering, sorting, or specifying additional information for the API endpoint. They are added to the
    URL as key-value pairs in the
    :param payload: The `payload` parameter in the `request_data` function is used to pass data that
    will be sent in the request body. It is typically used for sending data in POST, PUT, or PATCH
    requests. The `payload` parameter should be a dictionary or a list of tuples containing the data to
    :return: The function `request_data` returns the response data if the status code is 200 (OK). If
    the status code is not 200, it prints an error message and returns `None`.
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

        logger.info('Products data request is successful. Response: OK')

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
