import re
import time
import requests
import lxml.etree as ET

url = "https://api.n11.com/ws/ProductService/"

# Authenticate with your appKey and appSecret
headers = {"Content-Type": "text/xml; charset=utf-8"}
payload = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:GetProductListRequest>
            <auth>
                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>
                <appSecret>BmDozr9ORpNlhjNp</appSecret>
            </auth>
            <pagingData>
                <currentPage>0</currentPage>
                <pageSize>100</pageSize>
            </pagingData>
        </sch:GetProductListRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""
api_call = requests.post(url, headers=headers, data=payload)

# Function for parsing the XML response received from the N11 API


def assign_vars(response):
    """
    The function `assign_vars` extracts product information and the number of pages from an XML
    response.

    :param response: The `response` parameter is expected to be the response object returned from an API
    call. It should contain the XML response data
    :return: two values: `products_list` and `products_pages`.
    """
    # Access the response elements
    raw_xml = response.text

    # `tree = ET.fromstring(raw_xml)` is creating an ElementTree object from the raw XML response
    # received from the N11 API. The `fromstring()` function is a method of the `lxml.etree` module
    # that parses the XML string and returns an ElementTree object. This object represents the XML
    # structure and allows for easy navigation and manipulation of the XML data.
    tree = ET.fromstring(raw_xml)

    # The line `namespaces = {"ns3": "http://www.n11.com/ws/schemas"}` is creating a dictionary that
    # maps a namespace prefix (`ns3`) to a namespace URI (`http://www.n11.com/ws/schemas`).
    namespaces = {"ns3": "http://www.n11.com/ws/schemas"}

    # The line `products_raw_response = tree.find(".//ns3:GetProductListResponse", namespaces)` is
    # finding the element in the XML response that corresponds to the "GetProductListResponse" tag.
    products_raw_response = tree.find(
        ".//ns3:GetProductListResponse", namespaces)

    # The code snippet `products_list = products_raw_response.find("products").findall("product")` is
    # finding the element in the XML response that corresponds to the "products" tag and then finding
    # all child elements with the tag "product". This will return a list of XML elements representing
    # each product in the response.
    products_list = products_raw_response.find("products").findall("product")
    products_pages = products_raw_response.find(
        "pagingData").find("pageCount").text

    return products_list, products_pages


def get_n11_stock_data():
    """
    The function `get_n11_stock_data` makes a POST request to retrieve stock data from the N11 API and
    returns a list of product IDs and their corresponding stock quantities.
    :return: The function `get_n11_stock_data` returns a list of dictionaries containing the product ID
    and stock quantity for each product found in the response.
    """

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(url, headers=headers, data=payload)
    current_page = 0

    # Status code of 200 means that the request was successful and the server returned the expected response.
    if api_call.status_code == 200:
        products_list, products_pages = assign_vars(api_call)
        raw_elements = []

        # Process all pages found
        while current_page < int(products_pages):
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
            products_list, products_pages = assign_vars(api_call_loop)
    else:
        print("Error:", api_call.text)

    print("N11 SOAP Request is Successful. Response:", api_call.reason)
    return raw_elements


def post_n11_data(data):

    for data_item in data:
        # The `post_payload` variable is a string that contains an XML request payload for updating the
        # stock quantity of a product on the N11 platform.
        post_payload = f"<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:sch=\"http://www.n11.com/ws/schemas\">\n    <soapenv:Header/>\n    <soapenv:Body>\n        <sch:UpdateStockByStockSellerCodeRequest>\n            <auth>\n                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>\n                <appSecret>BmDozr9ORpNlhjNp</appSecret>\n            </auth>\n            <stockItems>\n                <stockItem>\n                    <sellerStockCode>{data_item['code']}</sellerStockCode>\n                    <quantity>{data_item['qty']}</quantity>\n                </stockItem>\n            </stockItems>\n        </sch:UpdateStockByStockSellerCodeRequest>\n    </soapenv:Body>\n</soapenv:Envelope>"
        post_response = requests.post(url, headers=headers, data=post_payload)
        if post_response.status_code == 200:
            if re.search('failure', post_response.text):
                print(f"Request failure for code {data_item['code']} | Response: {post_response.text}\n")
            else:
                print(
                f'N11 product with code: {data_item["code"]}, New value: {data_item["qty"]}\n')
        elif post_response.status_code == 429:
            time.sleep(15)
        else:
            post_response.raise_for_status()
            print(f"Request for product {data_item['code']} is unsuccessful | Response: {post_response.text}\n")

    print('N11 product updates is finished.')
