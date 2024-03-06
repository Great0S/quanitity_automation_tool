from datetime import datetime
import json
import re
import time
import requests
import os 

# The code snippet is initializing some variables and setting up the headers for making API requests.
page = 0

url_addon = ""

products = []

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

    :param url_addons: The `url_addons` parameter is a string that represents any additional path or
    query parameters that need to be added to the base URL. It is appended to the base URL to form the
    complete URL for the API request
    :param request_type: The `request_type` parameter is the type of HTTP request to be made. It can be
    one of the following: "GET", "POST", "PUT", "DELETE", etc
    :param payload_content: The payload_content parameter is the data that you want to send in the
    request. It can be in various formats such as JSON, XML, or form data. The content of the payload
    will depend on the specific API you are working with and the data it expects
    :return: the response object from the API request.
    """
    payload = payload_content

    url = f"https://api.trendyol.com/sapigw/suppliers/{store_id}/products{url_addons}"

    while True:

        api_request = requests.request(
            request_type, url, headers=headers, data=payload)
        
        if api_request.status_code == 200:

            return api_request
        
        elif api_request.status_code == 400:

            return None
        
        else:

            time.sleep(1)

            continue

def prepare_data(request_data):
    """
    The function prepares the data by decoding the response from a request.

    :param request_data: The parameter `request_data` is the data that is received from a request made
    to an API or a server. It could be in the form of a JSON string or any other format
    :return: the decoded data, which is a Python object obtained by parsing the response text as JSON.
    """
    response = request_data

    decoded_data = json.loads(response.text)

    return decoded_data

def get_trendyol_stock_data(everyProduct: bool =False):
    """
    The function `get_data` retrieves products data from multiple pages and appends it to a list.

    :param page: The `page` parameter is used to specify the page number of the data to retrieve. It is
    used in the URL to fetch data from different pages
    :param products: The `products` parameter is a list that will store the extracted data. Each item in
    the list will be a dictionary with two keys: "barcode" and "quantity". The "barcode" key will store
    the product's barcode, and the "quantity" key will store the quantity of the product
    """
    page = 0

    # if startDate and endDate is not None:
    #     stDate = datetime.strptime(startDate, "%d/%m/%Y").date()
    #     enDate = datetime.strptime(endDate, "%d/%m/%Y").date()
    #     startDate = int(datetime.fromordinal(stDate.toordinal()).timestamp())
    #     endDate = int(datetime.fromordinal(enDate.toordinal()).timestamp())
    #     url_addon = f"?page={page}&size=100&startDate={startDate}&endDate={endDate}"
    # else:
    
    all_products = []

    products = []

    url_addon = f"?page={page}&size=100"

    decoded_data = prepare_data(request_data(url_addon, "GET", {}))

    while page < int(decoded_data['totalPages']):        

        for element in range(len(decoded_data['content'])):

            data = decoded_data['content'][element]

            if everyProduct:

                all_products.append(data)

            else:

                item_id = data['barcode']

                if item_id == None:

                    pass

                item = data['productMainId']

                quantity = data['quantity']

                products.append({
                    "id": f"{item_id}",
                    "sku": f"{item}",
                    "qty": quantity
                })

        page += 1

        url_addon = f"?page={page}&size=100"

        decoded_data = prepare_data(request_data(url_addon, "GET", {}))

    print(f'Trendyol products data request is successful. Response: OK')

    if everyProduct:

        products = all_products

    return products

def post_trendyol_data(product):
    """
    The function `post_data` sends a POST request to a specified URL with a payload containing a list of
    products.

    :param products: The "products" parameter is a list of items that you want to post to the server.
    Each item in the list should be a dictionary containing the necessary information for the server to
    process
    """
    url_addon = "/price-and-inventory"

    post_payload = json.dumps(
        {
    "items": [
        {
            "barcode": product['id'],
            "quantity": int(product['qty'])
        }
    ]
})
    post_response = request_data(url_addon, "POST", post_payload)

    if post_response.status_code == 200:
        
        if re.search('failure', post_response.text):
        
            print(f"Request failure for trendyol product {product['code']} | Response: {post_response.text}")
        
        else:
           
            batchRequestId = json.loads(post_response.text)['batchRequestId']
            
            while True:
               
                batchId_request_raw = request_data(f'/batch-requests/{batchRequestId}', "GET", [])
                
                batchId_request = json.loads(batchId_request_raw.text)
               
                if batchId_request['items']:
                 
                    request_status = batchId_request['items'][0]['status']
                   
                    if request_status == 'SUCCESS':
                    
                        print(f'Trendyol product with code: {product["sku"]}, New value: {product["qty"]}')
                     
                        break
                 
                    elif request_status == 'FAILED':
                    
                        print(f'Trendyol product with code: {product["sku"]} failed to update || Reason: {batchId_request["items"]["failureReasons"]}')
                    
                        break
                else:
              
                    pass
   
    elif post_response.status_code == 429:
        
        time.sleep(15)
   
    else:
      
        post_response.raise_for_status()
       
        print(f"Request for trendyol product {product['sku']} is unsuccessful | Response: {post_response.text}")

# post_data(products, request_data, prepare_data)