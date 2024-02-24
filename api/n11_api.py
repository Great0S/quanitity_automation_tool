import json
import os
import re
import time
import requests
import lxml.etree as ET
from dotenv import load_dotenv
import xmltodict

load_dotenv()
API_KEY = os.getenv('N11_KEY')
API_SECRET = os.getenv('N11_SECRET')
url = "https://api.n11.com/ws"

# Authenticate with your appKey and appSecret
headers = {"Content-Type": "text/xml; charset=utf-8"}

# Function for parsing the XML response received from the N11 API


def assign_vars(response, response_namespace, list_name):
    """
    The function `assign_vars` extracts product information and the number of pages from an XML
    response.

    :param response: The `response` parameter is expected to be the response object returned from an API
    call. It should contain the XML response data
    :return: two values: `products_list` and `products_total`.
    """
    # Access the response elements
    raw_xml = response.text
    main_list = ""
    sub_list = ""

    # `tree = ET.fromstring(raw_xml)` is creating an ElementTree object from the raw XML response
    # received from the N11 API. The `fromstring()` function is a method of the `lxml.etree` module
    # that parses the XML string and returns an ElementTree object. This object represents the XML
    # structure and allows for easy navigation and manipulation of the XML data.
    revised_response = (raw_xml.replace(f"""<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body>""", "")).replace(f"""</SOAP-ENV:Body></SOAP-ENV:Envelope>""", "")
    response_json = xmltodict.parse(revised_response)
    
    if list_name in response_json[f"ns3:{response_namespace}"]:
        items_list = next(iter(response_json[f"ns3:{response_namespace}"][list_name].values()))
        items_total = response_json[f"ns3:{response_namespace}"]['pagingData']['totalCount']
           
        return items_list, items_total
  

def get_n11_stock_data(url):
    """
    The function `get_n11_stock_data` makes a POST request to retrieve stock data from the N11 API and
    returns a list of product IDs and their corresponding stock quantities.
    :return: The function `get_n11_stock_data` returns a list of dictionaries containing the product ID
    and stock quantity for each product found in the response.
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
    url = url+"/ProductService/"

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(url, headers=headers, data=payload)
    current_page = 0

    # Status code of 200 means that the request was successful and the server returned the expected response.
    if api_call.status_code == 200:
        products_list, products_total = assign_vars(api_call, "GetProductListResponse", "products")
        raw_elements = []

        # Process all pages found
        while current_page < int(products_total):
            if products_list is not None:
                # Process the product data
                for product in products_list:
                    product_id = product.find("id").text
                    product_code = product.find("productSellerCode").text
                    product_qty = int(product.find("stockItems").find(
                        "stockItem").find("quantity").text)
                    raw_elements.append({
                        "id": product_id,
                        "code": product_code,
                        "stok": product_qty,
                    })
            else:
                print("No products found in the response.")

            current_page += 1
            payload_dump = payload.replace(
                f"<currentPage>0</currentPage>",
                f"<currentPage>{str(current_page)}</currentPage>",
            )
            api_call_loop = requests.post(
                url, headers=headers, data=payload_dump)
            products_list, products_total = assign_vars(api_call_loop, "GetProductListResponse", "product")
    else:
        print("Error:", api_call.text)

    print("N11 SOAP Request is Successful. Response:", api_call.reason)
    return raw_elements


def get_n11_detailed_order_list(url):

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
    orders_url = f"{url}/orderService/"

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(orders_url, headers=headers, data=payload)
    current_page = 0

    # Status code of 200 means that the request was successful and the server returned the expected response.
    if api_call.status_code == 200:
        orders_list, orders_total = assign_vars(api_call, "DetailedOrderListResponse", "orderList")
        raw_elements = []

        # Process all pages found
        while current_page < int(orders_total):
            if orders_list is not None:
                # Process the product data
                for order in orders_list:       
                    item = {}
                    val = order.items()
                    for item_key, item_value in order.items():
                        if isinstance(item_value, dict):
                            for sub_key, sub_value in item_value.items():
                                if isinstance(sub_value, dict): 
                                    for low_key, low_value in sub_value.items():
                                        if isinstance(low_value, dict):
                                            data_val = (f"{low_key}_{inner_key}: {low_value[inner_key]}" for inner_key in low_value.keys())
                                            item.update(data_val)
                                        else:
                                            item[f"{sub_key}_{low_key}"] = low_value 
                                else:
                                    item[f"{item_key}_{sub_key}"] = sub_value 
                        else:
                            item[item_key] = item_value

                    raw_elements.append(item)
            else:
                print("No orders found in the response.")

            current_page += 1
            payload_dump = payload.replace(
                f"<currentPage>0</currentPage>",
                f"<currentPage>{str(current_page)}</currentPage>",
            )
            orders_list, orders_total = looper(orders_url, payload_dump, "DetailedOrderListResponse", "orderList")
    else:
        print("Error:", api_call.text)

    print("N11 detailed orders list extraction is Successful. || Response:", api_call.reason)
    return raw_elements

def looper(link, payload_dump, namespace, list_name):
    while True:
        api_call_loop = requests.post(
                link, headers=headers, data=payload_dump)
        if re.search("success", api_call_loop.text):            
            orders_list, orders_total = assign_vars(api_call_loop, namespace, list_name)

            return orders_list, orders_total
        else:
            time.sleep(1)

get_n11_detailed_order_list(url)
# get_n11_stock_data(url)

def save_to_csv(data):
    keys = set()
    for item in data:
        if isinstance(item, "dict"):
            keys.update(item.keys())


def post_n11_data(data):

    for data_item in data:
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
                              <stockItems>
                                <stockItem>
                                  <sellerStockCode>{data_item['code']}</sellerStockCode>
                                  <quantity>{data_item['qty']}</quantity>
                                </stockItem>
                              </stockItems>
                            </sch:UpdateProductBasicRequest>
                          </soapenv:Body>
                        </soapenv:Envelope>
                        """
        post_response = requests.request(
            "POST", url, headers=headers, data=post_payload)
        if post_response.status_code == 200:
            if re.search('failure', post_response.text):
                print(f"Request failure for code {
                      data_item['code']} | Response: {post_response.text}\n")
            else:
                print(
                    f'N11 product with code: {data_item["code"]}, New value: {data_item["qty"]}\n')
        elif post_response.status_code == 429:
            time.sleep(15)
        else:
            post_response.raise_for_status()
            print(f"Request for product {
                  data_item['code']} is unsuccessful | Response: {post_response.text}\n")

    print('N11 product updates is finished.')
