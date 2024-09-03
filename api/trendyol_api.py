""" The lines `import json`, `import re`, `import time`, `import os`, and `import requests` are
 importing necessary modules in Python for working with JSON data, regular expressions, time-related
 functions, operating system functionalities, and making HTTP requests, respectively."""
import json
import logging
import re
import time
import os
import requests


logger = logging.getLogger(__name__)
auth_hash = os.environ.get('TRENDYOLAUTHHASH')
store_id = os.environ.get('TRENDYOLSTOREID')
headers = {
    'User-Agent': f'{store_id} - SelfIntegration',
    'Content-Type': 'application/json',
    'Authorization': f'Basic {auth_hash}'
}


def request_data(url_addons, request_type, payload_content):
    """
    The function `request_data` sends a request to a specified URL with specified headers, request type,
    and payload content.
    """
    payload = payload_content

    url = f"https://api.trendyol.com/sapigw/suppliers/{store_id}/products{url_addons}"

    while True:

        api_request = requests.request(request_type, url, headers=headers, data=payload, timeout=3000)

        if api_request.status_code == 200:

            return api_request

        if api_request.status_code == 400:

            return None

        time.sleep(1)

        continue


def prepare_data(data):
    """
    The function prepares the data by decoding the response from a request.

    :param request_data: The parameter `request_data` is the data that is received from a request made
    to an API or a server. It could be in the form of a JSON string or any other format
    :return: the decoded data, which is a Python object obtained by parsing the response text as JSON.
    """
    response = data

    decoded_data = json.loads(response.text)

    return decoded_data


def get_trendyol_stock_data(every_product: bool = False, local: bool = False, Filters=''):
    """
    The function `get_data` retrieves products data from multiple pages and appends it to a list.

    """
    page = 0

    all_products = []

    products = []

    uri_addon = f"?page={page}&size=100" + Filters

    decoded_data = prepare_data(request_data(uri_addon, "GET", {}))

    while page < int(decoded_data['totalPages']):

        for element in range(len(decoded_data['content'])):

            data = decoded_data['content'][element]

            item = data['stockCode']

            if item:

                pass

            else:

                item = data['productMainId']

            if every_product:

                all_products.append({'sku': item, 'data': data})

            else:

                item_id = data['barcode']

                if item_id is None:

                    pass

                quantity = data['quantity']

                price = data['salePrice']

                products.append({
                    "id": f"{item_id}",
                    "sku": f"{item}",
                    "qty": quantity,
                    "price": price
                })

        page += 1

        uri_addon = re.sub(r"\?page=\d", f"?page={page}", uri_addon)

        decoded_data = prepare_data(request_data(uri_addon, "GET", {}))

    if every_product:

        products = all_products

    logger.info(f"Trendyol fetched {len(products)} products")   

    return products


def post_trendyol_data(product: dict):
    """
    The function `post_data` sends a POST request to a specified URL with a payload containing a list of
    products.
    """
    uri_addon = "/price-and-inventory"

    post_payload = json.dumps(
        {
            "items": [
                {
                    "barcode": product['id'],
                    "quantity": int(product['qty'])
                }
            ]
        })
    post_response = request_data(uri_addon, "POST", post_payload)

    if post_response.status_code == 200:

        if re.search('failure', post_response.text):

            logger.error(f"Request failure for product {product['code']} | Response: {post_response.text}")

        else:

            batch_requestid = json.loads(post_response.text)['batchRequestId']

            while True:

                batchid_request_raw = request_data(f'/batch-requests/{batch_requestid}', "GET", [])

                batchid_request = json.loads(batchid_request_raw.text)

                if batchid_request['items']:

                    request_status = batchid_request['items'][0]['status']

                    if request_status == 'SUCCESS':

                        logger.info(f'Product with code: {product["sku"]}, New value: {product["qty"]}')

                        break

                    elif request_status == 'FAILED':

                        logger.error(f"""Product with code: {
                            product["sku"]} failed to update || Reason: {
                            batchid_request["items"][0]["failureReasons"]}""")

                        break
                else:

                    pass

    elif post_response.status_code == 429:

        time.sleep(15)

    else:

        post_response.raise_for_status()

        logger.error(f"""Request for product {
               product['sku']} is unsuccessful | Response: {
                   post_response.text}""")


def delete_trendyol_product(ids, include_keyword, exclude_keyword=''):

    url = "https://api.trendyol.com/sapigw/suppliers/120101/v2/products"
    batch_url = "https://api.trendyol.com/sapigw/suppliers/120101/products/batch-requests/"
    items = []

    for item in ids:

        if re.search(include_keyword, item['data']['title']):

            if exclude_keyword:

                if not re.search(exclude_keyword, item['data']['title']):

                    items.append({"barcode": item['data']['barcode']})

            items.append({"barcode": item['data']['barcode']})

    payload = json.dumps({
        "items": items
    })

    response = requests.request("DELETE", url, headers=headers, data=payload)

    if response.status_code == 200:

        response_json = json.loads(response.text)

        while True:

            request_response = requests.request(
                "GET", batch_url + response_json['batchRequestId'], headers=headers, data=payload)

            if request_response.status_code == 200:

                batch_feedback = json.loads(request_response.text)
                failed = []

                if batch_feedback['status'] == 'IN_PROGRESS':

                    time.sleep(5)

                if batch_feedback['status'] == 'COMPLETED':                

                    for item_report in batch_feedback['items']:

                        if item_report['status'] == 'FAILED':

                            failed.append({'barcode': item_report['requestItem']['barcode'], 'reason': item_report['failureReasons'][0]})

                    if failed:

                        logger.info(f"Successfully deleted products: {batch_feedback['itemCount']-len(failed)}\t\t\tFailed to delete: {len(failed)}")
                        logger.error(f"Failed items:")
                        for i, item in enumerate(failed):

                            logger.error(f"{i+1}. {item['barcode']}: {item['reason']}")

                        break

                    else:

                        logger.info(f"Successfully deleted products: {batch_feedback['itemCount']}")

                        break


# products = get_trendyol_stock_data(True, '&archived=True')
# delete_trendyol_product(products, include_keyword="'lı", exclude_keyword="16'lı")
