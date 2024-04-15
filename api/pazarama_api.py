import requests
import json
from rich import print as printr


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

        printr(f'[magenta]Pazarama[/magenta] access token request has failed || Reason: {
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

        printr(f'Pazarama request has failed || Reason: {response.text}')

        return None


def getPazarama_productsList(everyProduct: bool = False):
    """
    This Python function retrieves a list of products from Pazarama API and returns a subset of product
    data based on a specified condition.

    :param everyProduct: The `everyProduct` parameter is a boolean parameter that determines whether to
    return a list of all products or a simplified list with specific product details. When
    `everyProduct` is set to `False`, the function will iterate over the products list and extract the
    product ID, SKU, and quantity information for, defaults to False
    :type everyProduct: bool (optional)
    :return: If the `everyProduct` parameter is set to `False`, the function will return a list of
    dictionaries containing product information with keys 'id', 'sku', and 'qty'. If the `everyProduct`
    parameter is set to `True`, the function will return the entire `products_list` obtained from the
    API request.
    """

    products = []

    params = {
        'Approved': 'true',
        'Size': 250
    }

    products_list = request_data(uri='product/products', params=params)['data']

    if products_list:

        if not everyProduct:

            for product in products_list:

                products.append(
                    {'id': product['code'],
                     'sku': product['stockCode'],
                     'qty': product['stockCount'],
                     'price': product['salePrice']
                     })

            printr(
                '[magenta]Pazarama[/magenta] products data request is successful. Response: [orange3]OK[/orange3]')

            return products

        return products_list


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

            printr(f"""[magenta]Pazarama[/magenta] product with code: {
                product["sku"]}, New value: [green]{product["qty"]}[/green]""")

        else:

            printr(f'[magenta]Pazarama[/magenta] product with code: {
                   sku} failed to update || Reason: {update_request['data'][0]['error']}')
