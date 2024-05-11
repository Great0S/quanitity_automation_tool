import csv
import os
import re
import time
import requests
import xmltodict
from rich import print as printr


# Setting api value
API_KEY = os.getenv('N11_KEY')
API_SECRET = os.getenv('N11_SECRET')
URL = "https://api.n11.com/ws"

# Authenticate with your appKey and appSecret
headers = {"Content-Type": "text/xml; charset=utf-8"}


def assign_vars(response, response_namespace, list_name, error_message=False):
    """
    The function `assign_vars` parses XML response data, extracts specific elements 
    based on provided namespace and list name, and returns a list of items and total
    pages if the list exists, otherwise returns None.
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


def get_n11_stock_data(every_product: bool = False):
    """
    The function `get_n11_stock_data` sends a SOAP request to the N11 API 
    to retrieve a list of products and their stock information.
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

                    product_id = product.get("id")
                    product_code = product.get("productSellerCode")
                    product_price = product.get("displayPrice")

                    if every_product:

                        all_products.append(
                            {'sku': product_code, 'data': product})

                    else:

                        if "stockItems" in product and isinstance(product['stockItems']['stockItem'],
                                                                  list):

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
                            "price": product_price,
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

        printr("Error: ", api_call.text)

    printr(f"""[purple4]N11[/purple4] products data request is successful. Response: [orange3]{
           api_call.reason}[/orange3]""")

    if every_product:
        raw_elements = all_products

    return raw_elements


def get_n11_detailed_order_list(link):
    """
    The function `get_n11_detailed_order_list` sends a SOAP request to the 
    N11 API to retrieve a list of detailed orders and processes the response
    to extract relevant information.
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
        printr("[purple4]N11[/purple4] detailed orders list extraction is Successful. || Response:",
               api_call.reason)
    else:
        pass
    return raw_elements


def flatten_dict(data, prefix=""):
    """
    The `flatten_dict` function recursively flattens a nested dictionary 
    into a single-level dictionary with keys concatenated based on the original structure.
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
                                    data_item, f"{prefix}_{sub_key}{count}"
                                    if prefix else f"{sub_key}{count}")
                                item.update(data_val)

                            else:

                                if prefix:
                                    item[f"""{prefix}_{sub_key}{
                                        count}"""] = data_item

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
    """
    while True:
        api_call_loop = requests.post(
            link, headers=headers, data=payload_dump, timeout=30)
        if re.search("success", api_call_loop.text):
            orders_list, orders_total = assign_vars(
                api_call_loop, namespace, list_name)

            return orders_list, orders_total
        time.sleep(1)


def save_to_csv(data, filename=""):
    """
    The function `save_to_csv` takes a list of dictionaries and saves it to a CSV file with the
    specified filename.
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


def post_n11_data(data):
    """
    The `post_n11_data` function sends a SOAP request to 
    update the stock quantity of a product on the
    N11 platform and handles the response accordingly.
    """

    # The `post_payload` variable is a string that contains an XML request payload for updating the
    # stock quantity of a product on the N11 platform.
    post_payload = f"""
                        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
                          <soapenv:Header/>
                          <soapenv:Body>
                            <sch:UpdateStockByStockSellerCodeRequest>
                              <auth>
                                <appKey>{API_KEY}</appKey>
                                <appSecret>{API_SECRET}</appSecret>
                              </auth>
                              <stockItems>
                                <stockItem>
                                  <sellerStockCode>{data['sku']}</sellerStockCode>
                                  <quantity>{data['qty']}</quantity>
                                </stockItem>
                              </stockItems>
                            </sch:UpdateStockByStockSellerCodeRequest>
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
                post_response, 'UpdateStockByStockSellerCodeResponse', '', True)

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


def create_n11_data(data):
    """
    The `create_n11_data` function sends a SOAP request to 
    create a product on the
    N11 platform and handles the response accordingly.
    """

    for item in data:

        item_data = data[item][0]['data']
        images = []

        for image in item_data['images']:

            images.append(f"""<image>
                        <url>{image['url']}</url>
                        <order>{item_data['images'].index(image)}</order>
                        </image>
                     """)

        post_payload = f"""
                        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
                          <soapenv:Header/>
                          <soapenv:Body>
                            <sch:SaveProductRequest>
                              <auth>
                                <appKey>{API_KEY}</appKey>
                                <appSecret>{API_SECRET}</appSecret>
                              </auth>
                              <product>
                                <productSellerCode>{item_data['productMainId']}</productSellerCode>
                                <title>{item_data['title']}</title>
                                <description>{item_data['description']}</description>
                                <category>
                                    <fullName>Ev Tekstili &gt; Halı &amp; Kilim &gt; Paspas</fullName>
                                    <id>1000722</id>
                                    <name>Paspas</name>
                                </category>
                                <specialProductInfoList/>
                                <price>{item_data['listPrice']}</price>
                                 <domestic>true</domestic>
                                <currencyType>1</currencyType>
                                <images>
                                   {images}
                                </images>
                                <approvalStatus>1</approvalStatus>
                                <attributes>
                                    <attribute>
                                        <id>354080325</id>
                                        <name>Renk</name>
                                        <value>{item_data['attributes'].get('Renk', None)}</value>
                                    </attribute>
                                    <attribute>
                                        <id>354285900</id>
                                        <name>Marka</name>
                                        <value>{item_data['brand']}</value>
                                    </attribute>
                                    <attribute>
                                        <id>354853703</id>
                                        <name>Şekil</name>
                                        <value>{item_data['attributes'].get('Şekil', None)}</value>
                                    </attribute>
                                    <attribute>
                                        <id>354235901</id>
                                        <name>Ölçüler</name>
                                        <value>{item_data['attributes'].get('Boyut/Ebat', None)}</value>
                                    </attribute>
                                    <attribute>
                                        <id>354282390</id>
                                        <name>Taban Özelliği</name>
                                        <value>{item_data['attributes'].get('Taban', None)}</value>
                                    </attribute>
                                </attributes>
                                <productionDate>01/03/2024</productionDate>
                                <productCondition>1</productCondition>
                                <preparingDay>3</preparingDay>
                                <discount>
                                    <type>1</type>
                                    <value>413.0</value>
                                </discount>
                                <shipmentTemplate>Kargo</shipmentTemplate>
                                <stockItems>
                                    <stockItem>
                                        <bundle>false</bundle>
                                        <currencyAmount>{item_data['listPrice']}</currencyAmount>
                                        <displayPrice>{item_data['salePrice']}</displayPrice>
                                        <optionPrice>{item_data['listPrice']}</optionPrice>
                                        <n11CatalogId>150024204</n11CatalogId>
                                        <sellerStockCode>{item_data['productMainId']}</sellerStockCode>
                                        <attributes/>
                                        <id>127240326224</id>
                                        <images/>
                                        <quantity>{item_data['quantity']}</quantity>
                                        <version>1</version>
                                    </stockItem>
                                </stockItems>
                                <groupAttribute>Renk</groupAttribute>
                                <groupItemCode>{item_data['productMainId']}</groupItemCode>
                            </product>
                            </sch:SaveProductRequest>
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
                post_response, 'SaveProductResponse', '', True)

            printr(f"""Request failure for [purple4]N11[/purple4] product {
                data['sku']} | Response: {error_message['result']['errorMessage']}""")

        else:

            printr(f"""[purple4]N11[/purple4] new product with code: {
                data["sku"]}""")
    elif post_response.status_code == 429:

        time.sleep(15)

    else:

        post_response.raise_for_status()
        printr(
            f"""Request for [purple4]N11[/purple4] product {
                data['sku']} is unsuccessful | Response: [red]{post_response.text}[/red]""")
