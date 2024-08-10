import logging
import requests
import json
import time

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
    payload_dump = json.dumps(payload, ensure_ascii=False)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    while True:

        response = requests.request(
            method, url, headers=headers, params=params, data=payload_dump)

        if response.status_code == 200:

            response_data = json.loads(response.text)

            return response_data
        
        if response.status_code == 429:

            time.sleep(1)

        else:

            logger.error(f'Request has failed for product {payload['items'][0]['code']} || Status code: {response.status_code} || Reason: {response.reason}')

            return None

def getPazarama_productsList(everyProduct: bool = False, local: bool = False):
    """
    This Python function retrieves a list of products from Pazarama API and returns a subset of product
    data based on a specified condition.

    """

    products_items = []

    params = {
        'Approved': 'true',
        'Size': 250
    }

    products_list, elapsed_time = request_processing(uri='product/products', params=params)
    products = products_list['data']

    if products:
        for product in products:
            if not everyProduct:

                products_items.append(
                    {'id': product['code'],
                     'sku': product['stockCode'],
                     'qty': product['stockCount'],
                     'price': product['salePrice']
                     })
            else:

                products_items.append(
                    {'sku': product['stockCode'],
                     'data': product
                     })

        logger.info(f'Pazarama fetched {len(products_items)} products in {elapsed_time:.2f} seconds.')

        return products_items

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

    update_payload = {
        "items": [{
                "code": product_id,
                "stockCount": int(qty)
            }]}
   
    update_request, elapsed_time = request_processing('product/updateStock-v2', update_payload, 'POST')

    if update_request:

        if update_request['success'] == True:

            logger.info(f"""Product with code: {product["sku"]}, New value: {product["qty"]}, Elapsed time: {elapsed_time:.2f} seconds.""")

        else:

            logger.error(f'Product with code: {sku} failed to update || Reason: {update_request['data'][0]['error']} || Elapsed time: {elapsed_time:.2f} seconds.')

def request_processing(uri: str, payload: dict = {}, params: dict = {}, method: str = 'GET'):

    start_time = time.time()
    request = request_data(method = method,
                           uri = uri,
                           params = params,
                           payload=payload)
    end_time = time.time()
    elapsed_time = end_time - start_time

    return request, elapsed_time