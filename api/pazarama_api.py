import requests
import json


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

        print(f'Pazarama access token request has failed || Reason: {
              response.text}')


def request_data(method='GET', uri='', params={}, payload=[]):

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

        print(f'Pazarama request has failed || Reason: {response.text}')

        return None


def getPazarama_productsList(everyProduct: bool = False):

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
                    {'id': product['code'], 'sku': product['stockCode'], 'qty': product['stockCount']})

            print(f'Pazarama products data request is successful. Response: OK')
            
            return products

        else:

            return products_list


def pazarama_updateRequest(product):

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

            print(f'Pazarama product with code: {sku}, New value: {qty}')

        else:

            print(f'Pazarama product with code: {sku} failed to update || Reason: {update_request['data'][0]['error']}')
