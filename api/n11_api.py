import csv
from datetime import date
import os
import re
import time
import requests
import xmltodict
from rich import print as printr
from zeep import Client, Settings, xsd




# Setting api value
API_KEY = os.getenv('N11_KEY')
API_SECRET = os.getenv('N11_SECRET')
URL = "https://api.n11.com/ws"
headers = {
  'Content-Type': 'text/xml; charset=utf-8'
}
auth = {
                "appKey": API_KEY,
                "appSecret": API_SECRET,
            }

def get_client(Service: str = 'ProductService'):

    wsdl_url = f"{URL}/{Service}.wsdl"
    settings = Settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True)
    client = Client(wsdl=wsdl_url, settings=settings)
    

    return client

def assign_vars(raw_xml, response_namespace, list_name, error_message=False, namespace_id='ns3'):
    """
    The function `assign_vars` parses XML response data, extracts specific elements 
    based on provided namespace and list name, and returns a list of items and total
    pages if the list exists, otherwise returns None.
    """

    # XML raw data trimming
    revised_response = (
        raw_xml.replace(
            """<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body>""",
            "")).replace("""</SOAP-ENV:Body></SOAP-ENV:Envelope>""", "")

    # Parse the XML response into a dictionary using xmltodict library.
    response_json = xmltodict.parse(revised_response)

    # Access the response elements using the response_namespace and list_name variables.
    if f"{namespace_id}:{response_namespace}" in response_json:
        response_data = response_json[f"{namespace_id}:{response_namespace}"]
    else:
        response_data = response_json['SOAP-ENV:Envelope']['SOAP-ENV:Body'][f"{
            namespace_id}:{response_namespace}"]

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

    link = URL + "/ProductService/"

    # This is used to send a SOAP request to the N11 API to retrieve a list of products.
    api_call = requests.post(link, headers=headers, data=payload, timeout=30)
    current_page = 0
    all_products = []

    # Status code of 200 means that the request was successful
    # and the server returned the expected response.
    if api_call.status_code == 200:

        products_list, products_total_pages = assign_vars(
            api_call.text, "GetProductListResponse", "products")
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
                api_call_loop.text, "GetProductListResponse", "products")

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
                api_call_loop.text, namespace, list_name)

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
                post_response.text, 'UpdateStockByStockSellerCodeResponse', '', True)

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

# post_n11_data({'sku':'ghggjg', 'qty': 765})


def create_n11_data(data):
    """
    The `create_n11_data` function sends a SOAP request to 
    create a product on the
    N11 platform and handles the response accordingly.
    """

    current_date = date.today()
    formatted_date = current_date.strftime("%d/%m/%Y")

    for item in data:

        item_data = data[item][0]['data']
        groupCode = re.sub(r'\d+', '', item_data['productMainId'])
        attrs = {}

        for attr in item_data['attributes']:
            attr_name = ['Renk', 'Şekil', 'Boyut/Ebat',
                         'Taban', 'Hav Yüksekliği']

            for item in attr_name:
                if re.search(attr['attributeName'], item):

                    attrs[attr['attributeName']] = attr['attributeValue']

        image_elements = []
        for i, image_url in enumerate(item_data['images'], start=1):
            image_elements.append(f"""<image>
                    <url>{image_url['url']}</url>
                    <order>{i}</order>
                </image>""")

        # Join all <image> elements into a single string
        images_string = "".join(image_elements)

        request_data = {
            "auth": {
                "appKey": API_KEY,
                "appSecret": API_SECRET,
            },
            "product": {
                "productSellerCode": item_data['productMainId'],
                "maxPurchaseQuantity": 5000,
                "title": item_data['title'],
                "description": re.sub(r'[\?]', '', item_data['description']),
                "category": {"id": 1001621},
                "price": item_data['listPrice'],
                "domestic": True,
                "currencyType": 1,
                "images": [],
                "approvalStatus": 1,
                "attributes": {
                    "attribute": [
                        {"name": "Renk", "value": attrs.get('Renk', '')},
                        {"name": "Marka", "value": item_data['brand']},
                        #  {"name": "Şekil", "value": ""},
                        #  {"name": "Ölçüler", "value": ""},
                        #  {"name": "Taban Özelliği", "value": ""},
                        #  {"name": "Hav Yüksekliği", "value": ""}
                    ]
                },
                "productionDate": formatted_date,
                "expirationDate": "",
                "productCondition": 1,
                "preparingDay": 3,
                "discount": {"startDate": "", "endDate": "", "type": 1, "value": int(item_data['listPrice']) - int(item_data['salePrice'])},
                "shipmentTemplate": "Kargo",
                "stockItems": {
                    "stockItem": [
                        {
                            "gtin": item_data['barcode'],
                            "quantity": item_data['quantity'],
                            "sellerStockCode": item_data['productMainId'],
                            "optionPrice": item_data['listPrice'],
                            "n11CatalogId": "",
                            "attributes": [],
                            "images":
                                image_elements,
                        }
                    ]
                },
                "groupAttribute": "Adet",
                "groupItemCode": groupCode,
                "itemName": "",
                "sellerNote": "",
                "unitInfo": {
                    "unitWeight": 0,
                    "unitType": 0,
                },
            },
        }

        client = get_client()
        response = client.service.SaveProduct(**request_data)

        if response.status_code == 200:

            if re.search('errorMessage',
                         response.text) or re.search('failure',
                                                          response.text):

                # error_message = assign_vars(
                #     post_response, 'SaveProductResponse', '', True)

                printr(f"""Request failure for [purple4]N11[/purple4] product {
                    data['sku']} | Response: {response['result']['errorMessage']}""")

            else:

                printr(f"""[purple4]N11[/purple4] new product with code: {
                    data["sku"]}""")
        elif response.status_code == 429:

            time.sleep(15)

        else:

            response.raise_for_status()
            printr(
                f"""Request for [purple4]N11[/purple4] product {
                    data['sku']} is unsuccessful | Response: [red]{response.text}[/red]""")


def get_n11_categories(save: bool = False):

    client = get_client('CategoryService')
    complete_list = {}

    
    
    TopLevelCategories = client.service.GetTopLevelCategories(auth=auth)
    categories_list = [{'id': x['id'], 'name': x['name'], 'subs': []} for x in TopLevelCategories['categoryList']['category']]

    for item in categories_list:

        complete_list[item['name']] = item
        categoryId = item['id']        

        SubCategories = client.service.GetSubCategories(auth=auth, categoryId=categoryId, lastModifiedDate=xsd.SkipValue)

        if SubCategories['category']:

            SubCategories_list = [{'subCategory_id': x['id'], 'subCategory_name': x['name'], 'sub_sub_category': [], 'attrs': []} for x in SubCategories['category'][0]['subCategoryList']['subCategory']]

            for sub_item in SubCategories_list:

                complete_list[item['name']]['subs'].append(sub_item)
                categoryId = sub_item['subCategory_id']

                SubSubCategories = client.service.GetSubCategories(auth=auth, categoryId=categoryId, lastModifiedDate=xsd.SkipValue)

                if SubSubCategories['category']:

                    SubSubCategories_list = [{'SubsubCategory_id': x['id'], 'SubsubCategory_name': x['name'], 'attrs': []} for x in SubSubCategories['category'][0]['subCategoryList']['subCategory']]

                    for sub_sub_item in SubSubCategories_list:

                        complete_list[item['name']]['subs'][SubCategories_list.index(sub_item)]['sub_sub_category'].append(sub_sub_item)
                        categoryId = sub_sub_item['SubsubCategory_id']



                        get_category_attrs(categoryId, complete_list, item, SubCategories_list.index(sub_item))




                get_category_attrs(categoryId)

def get_category_attrs(categoryId, item_list, item, index):

    client = get_client('CategoryService')
    CategoryAttributes = client.service.GetCategoryAttributes(auth=auth, categoryId=categoryId, pagingData=1)

    if CategoryAttributes['category']:
        sub_categories_attr_list = [{'attr_name': x['name']} for x in CategoryAttributes['category']['attributeList']['attribute']]

        for attr in sub_categories_attr_list:
            item_list[item['name']]['subs'][index]['attrs'].append(attr['attr_name'])
          

# cats = get_n11_categories()
# print('Done')