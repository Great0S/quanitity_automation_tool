import csv
import re
import time
import requests
from simple_dotenv import GetEnv
import xmltodict
from rich import print as printr


# Setting api value
API_KEY = str(GetEnv('N11_KEY'))
API_SECRET = str(GetEnv('N11_SECRET'))
URL = "https://api.n11.com/ws"

# Authenticate with your appKey and appSecret
headers = {"Content-Type": "text/xml; charset=utf-8"}

# Function for parsing the XML response received from the N11 API


def assign_vars(response, response_namespace, list_name, error_message=False):
    """
    The function `assign_vars` parses XML response data, extracts specific elements 
    based on provided namespace and list name, and returns a list of items and total
    pages if the list exists, otherwise returns None.

    :param response: The `response` parameter is the HTTP response object received 
    from a request to a web service. It contains the data that needs to be processed
    :param response_namespace: The `response_namespace` parameter in the `assign_vars`
    function is used to specify the namespace of the response elements that need to be
    accessed from the XML response data. It is used to navigate through the XML structure
    and extract the relevant data based on the provided namespace
    :param list_name: The `list_name` parameter in the `assign_vars` function refers to
    the name of the list within the XML response data that you want to access. It is used
    to check if this list exists in the response data and has at least one element. 
    If the list exists and has elements, the :return: The function `assign_vars` returns
    either a list of items and the total number of pages if the `list_name` exists in
    the response data and has at least one element, or it returns `None, None`
    if the `list_name` does not exist in the response data or if it is empty.
    """

    # Access the response elements
    raw_xml = response.text

    # XML raw data trimming
    revised_response = (
        raw_xml.replace(
            """<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body>""",
                        "")).replace("""</SOAP-ENV:Body></SOAP-ENV:Envelope>""", "")

    # Parse the XML response into a dictionary using xmltodict library.
    response_json = xmltodict.parse(revised_response)

    # Access the response elements using the response_namespace and list_name variables.
    response_data = response_json[f"ns3:{response_namespace}"]

    # Check if the list_name exists in the response data and has at least one element.
    # If so, return the list of items and the total number of pages.
    # Otherwise, return None.
    if list_name in response_data and not error_message:

        if response_data[list_name]:

            items_list = next(iter(response_data[list_name].values()))
            items_total_pages = response_data['pagingData']['pageCount']

            return items_list, items_total_pages

        return None, None

    if error_message:

        return response_data

    return None, None

# Function for retrieving stock data from the N11 API.


def get_n11_stock_data(every_product: bool = False):

    """
    The function `get_n11_stock_data` sends a SOAP request to the N11 API 
    to retrieve a list of products and their stock information.

    :param url: The `get_n11_stock_data` function you provided seems to 
    be making a SOAP request to the N11 API to retrieve stock data for 
    products. However, there are a few things missing in the code
    snippet you shared
    :return: The function `get_n11_stock_data` is returning a list of 
    dictionaries containing information about products retrieved from 
    the N11 API. Each dictionary in the list includes keys for
    "id" (product ID), "code" (product seller code), and "stok" (product quantity in stock).
    """

    payload = f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:GetProductListRequest>
            <auth>
                <appKey>{API_KEY}</appKey>
                <appSecret>{API_SECRET}</appSecret>
            </auth>
            <pagingData>
                <currentPage>0</currentPage>
                <pageSize>100</pageSize>
            </pagingData>
        </sch:GetProductListRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""
    link_base = "https://api.n11.com/ws"
    link = link_base+"/ProductService/"

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(link, headers=headers, data=payload, timeout=30)
    current_page = 0
    all_products = []

    # Status code of 200 means that the request was successful 
    # and the server returned the expected response.
    if api_call.status_code == 200:
        products_list, products_total_pages = assign_vars(
            api_call, "GetProductListResponse", "products")
        raw_elements = []

        # Process all pages found
        while current_page < int(products_total_pages):
            if products_list is not None:
                # Process the product data
                for product in products_list:
                    if every_product:
                        all_products.append(product)
                    else:
                        product_id = product.get("id")
                        product_code = product.get("productSellerCode")
                        if "stockItems" in product and isinstance(product['stockItems']['stockItem'], list):
                            for stock_item in product['stockItems']['stockItem']:
                                if stock_item['sellerStockCode'] == product_code:
                                    product_qty = int(stock_item["quantity"])
                                    break
                        elif "stockItems" in product:
                            product_qty = int(
                                product['stockItems']['stockItem']['quantity'])
                        else:
                            product_qty = None
                        raw_elements.append({
                            "id": product_id,
                            "sku": product_code,
                            "qty": product_qty,
                        })
            else:
                printr("No products found in the response.")

            current_page += 1
            payload_dump = payload.replace(
                "<currentPage>0</currentPage>",
                f"<currentPage>{str(current_page)}</currentPage>",
            )
            api_call_loop = requests.post(
                URL, headers=headers, data=payload_dump, timeout=30)
            products_list, _ = assign_vars(
                api_call_loop, "GetProductListResponse", "products")
    else:
        printr("Error:", api_call.text)

    printr('N11 products data request is successful. Response: ', api_call.reason)

    if every_product:
        raw_elements = all_products

    return raw_elements

# Function for retrieving order data from the N11 API.


def get_n11_detailed_order_list(link):
    """
    The function `get_n11_detailed_order_list` sends a SOAP request to the 
    N11 API to retrieve a list of detailed orders and processes the response
    to extract relevant information.

    :param url: It looks like the code snippet you provided is a function
    that sends a SOAP request to the N11 API to retrieve a detailed list 
    of orders. The function takes a URL as a parameter where the API is located
    :return: The function `get_n11_detailed_order_list` is returning a list of 
    detailed order information extracted from the N11 API. The function sends a 
    SOAP request to the N11 API to retrieve a list of orders, processes the response, 
    flattens the order data, and stores it in a list called `raw_elements`. This list 
    is then returned by the function.
    """

    payload = f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:DetailedOrderListRequest>
            <auth>
                <appKey>{API_KEY}</appKey>
                <appSecret>{API_SECRET}</appSecret>
            </auth>
            <searchData>
                <productId></productId>
                <status>Completed</status>
                <buyerName></buyerName>
                <orderNumber></orderNumber>
                <productSellerCode></productSellerCode>
                <recipient></recipient>
                <sameDayDelivery></sameDayDelivery>
                <period>
                    <startDate></startDate>
                    <endDate></endDate>
                </period>
                <sortForUpdateDate>true</sortForUpdateDate>
            </searchData>
            <pagingData>
                <currentPage>0</currentPage>
                <pageSize>100</pageSize>
            </pagingData>
        </sch:DetailedOrderListRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""
    orders_url = f"{link}/orderService/"

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(
        orders_url, headers=headers, data=payload, timeout=30)
    current_page = 0

    # Status code of 200 means that the request was successful and the 
    # server returned the expected response.
    if api_call.status_code == 200:
        orders_list, orders_total_pages = assign_vars(
            api_call, "DetailedOrderListResponse", "orderList")
        raw_elements = []

        # Process all pages found
        if orders_list is not None:
            while current_page < int(orders_total_pages):

                for order in orders_list:
                    flattened_order = flatten_dict(order, "")
                    raw_elements.append(flattened_order)

                current_page += 1
                payload_dump = payload.replace(
                    "<currentPage>0</currentPage>",
                    f"<currentPage>{str(current_page)}</currentPage>",
                )
                orders_list, _ = looper(
                    orders_url, payload_dump, "DetailedOrderListResponse", "orderList")

        else:
            printr("No orders found in the response.")
    else:
        printr("Error:", api_call.text)

    if raw_elements:
        printr("[purple4]N11[/purple4] detailed orders list extraction is Successful. || Response:", api_call.reason)
    else:
        pass
    return raw_elements


def flatten_dict(data, prefix=""):
    """
    The `flatten_dict` function recursively flattens a nested dictionary 
    into a single-level dictionary with keys concatenated based on the original structure.

    :param data: The `data` parameter in the `flatten_dict` function is a dictionary that 
    you want to flatten. This function takes a nested dictionary as input and flattens it 
    into a single-level dictionary where the keys are concatenated with underscores to 
    represent the nested structure 
    :param prefix: The `prefix` parameter in the `flatten_dict` function is used to 
    specify a prefix string that will be added to the keys of the flattened dictionary. 
    This prefix is helpful when you want to differentiate keys that are derived from 
    nested structures or to avoid key conflicts when flattening nested dictionaries
    :return: The `flatten_dict` function takes a nested dictionary `data` as input 
    and flattens it into a single-level dictionary where the keys are concatenated 
    with underscores to represent the nested structure. 
    The function returns the flattened dictionary `item`.
    """

    item = {}

    for item_key, item_value in data.items():
        if isinstance(item_value, dict):
            for sub_key, sub_value in item_value.items():
                if isinstance(sub_value, dict):
                    data_val = flatten_dict(
                        sub_value, f"{prefix}_{sub_key}" if prefix else sub_key)
                    item.update(data_val)
                elif isinstance(sub_value, list):
                    count = 1
                    while count < len(sub_value):
                        for data_item in sub_value:
                            if isinstance(data_item, dict):
                                data_val = flatten_dict(
                                    data_item, f"{prefix}_{sub_key}{count}" if prefix else f"{sub_key}{count}")
                                item.update(data_val)
                            else:
                                if prefix:
                                    item[f"{prefix}_{sub_key}{
                                        count}"] = data_item
                                else:
                                    item[f"{sub_key}{count}"] = data_item
                            count += 1
                else:
                    if prefix:
                        item[f"{prefix}_{sub_key}"] = sub_value
                    else:
                        item[f"{sub_key}"] = sub_value
        else:
            if prefix:
                item[f"{prefix}_{item_key}"] = item_value
            else:
                item[f"{item_key}"] = item_value
    return item


def looper(link, payload_dump, namespace, list_name):
    """
    The function `looper` continuously makes API calls until a successful response is received, then
    assigns variables based on the response.

    :param link: The `link` parameter is the URL endpoint where the API call is being made. It is the
    target URL to which the POST request is sent in the `looper` function
    :param payload_dump: The `payload_dump` parameter in the `looper` function is typically a dictionary
    or string containing the data that will be sent in the POST request to the specified `link`. It
    usually includes the necessary information for the API call to be successful, such as authentication
    tokens, parameters, and any other
    :param namespace: The `namespace` parameter in the `looper` function is typically used to specify a
    specific context or scope within which variables, functions, or objects exist. It helps in
    organizing and managing the elements within a program by providing a unique identifier or name for a
    particular set of elements
    :param list_name: The `list_name` parameter in the `looper` function is used to specify the name of
    the list where the orders will be stored. It is passed as an argument to the `assign_vars` function
    along with other parameters
    :return: The `looper` function is returning `orders_list` and `orders_total` variables when the API
    call response contains the word "success".
    """
    while True:
        api_call_loop = requests.post(
            link, headers=headers, data=payload_dump, timeout=30)
        if re.search("success", api_call_loop.text):
            orders_list, orders_total = assign_vars(
                api_call_loop, namespace, list_name)

            return orders_list, orders_total
        time.sleep(1)

# Function for saving data to a CSV file.


def save_to_csv(data, filename=""):
    """
    The function `save_to_csv` takes a list of dictionaries and saves it to a CSV file with the
    specified filename.

    :param data: The `data` parameter in the `save_to_csv` function is expected to be a list of
    dictionaries. Each dictionary in the list represents a row of data to be written to the CSV file.
    The keys of the dictionaries will be used as the column headers in the CSV file
    :param filename: The `filename` parameter in the `save_to_csv` function is a string that represents
    the name of the CSV file where the data will be saved. If no filename is provided, the default value
    is an empty string
    """
    if data:
        keys = set()
        for item in data:
            keys.update(item.keys())

        with open(f"{filename}_data_list.csv", "w", newline='', encoding="utf-8") as csvfile:
            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))
            file_writer.writeheader()
            for d in data:
                file_writer.writerow(d)

# Function for updating product data on N11


def post_n11_data(data):
    """
    The `post_n11_data` function sends a SOAP request to update the stock quantity of a product on the
    N11 platform and handles the response accordingly.

    :param data: It looks like the code snippet you provided is a function `post_n11_data` that is
    responsible for updating the stock quantity of a product on the N11 platform using a SOAP request.
    The function takes a `data` parameter which seems to be a dictionary containing information about
    the product to be updated
    """

    # The `post_payload` variable is a string that contains an XML request payload for updating the
    # stock quantity of a product on the N11 platform.
    post_payload = f"""
                        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
                          <soapenv:Header/>
                          <soapenv:Body>
                            <sch:UpdateProductBasicRequest>
                              <auth>
                                <appKey>{API_KEY}</appKey>
                                <appSecret>{API_SECRET}</appSecret>
                              </auth>
                              <productId>{data['id']}</productId>
                              <stockItems>
                                <stockItem>
                                  <sellerStockCode>{data['sku']}</sellerStockCode>
                                  <quantity>{data['qty']}</quantity>
                                </stockItem>
                              </stockItems>
                            </sch:UpdateProductBasicRequest>
                          </soapenv:Body>
                        </soapenv:Envelope>
                        """

    post_response = requests.request(
        "POST", URL, headers=headers, data=post_payload, timeout=30)

    if post_response.status_code == 200:

        if re.search('errorMessage',
                     post_response.text) or re.search('failure',
                                                      post_response.text):

            error_message = assign_vars(
                post_response, 'UpdateProductBasicResponse', '', True)

            printr(f"""Request failure for [purple4]N11[/purple4] product {
                data['sku']} | Response: {error_message['result']['errorMessage']}""")

        else:

            printr(f"""[purple4]N11[/purple4] product with code: {
                data["sku"]}, New value: [green]{data["qty"]}[/green]""")
    elif post_response.status_code == 429:

        time.sleep(15)

    else:

        post_response.raise_for_status()
        printr(
            f"""Request for [purple4]N11[/purple4] product {
                data['sku']} is unsuccessful | Response: [red]{post_response.text}[/red]""")


# save_to_csv(get_n11_detailed_order_list(url), 'orders')
