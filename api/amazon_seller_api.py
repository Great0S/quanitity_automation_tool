""" importing necessary modules and libraries for performing various
 tasks related to handling data, making HTTP requests, and working with concurrency """

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from glob import glob
import logging
import textwrap
from urllib import parse
import json
import os
import re
import csv
import io
import time
import requests
from sp_api.api import DataKiosk
from sp_api.api import (
    ListingsItems,
    ProductTypeDefinitions,
    CatalogItems,
    CatalogItemsVersion,
    ReportsV2,
)
from sp_api.base.reportTypes import ReportType
from datetime import datetime
from app.config import logger


# DATA KIOSK API
client = DataKiosk()


client_id = os.environ.get("LWA_APP_ID")
client_secret = os.environ.get("LWA_CLIENT_SECRET")
refresh_token = os.environ.get("SP_API_REFRESH_TOKEN")
MarketPlaceID = os.environ.get("AMAZONTURKEYMARKETID")
AmazonSA_ID = os.environ.get("AMAZONSELLERACCOUNTID")
credentials = {
    "refresh_token": refresh_token,
    "lwa_app_id": client_id,
    "lwa_client_secret": client_secret,
}

session = requests.session()
# logger = logging.getLogger(__name__)


def get_access_token():
    """
    The function `get_access_token` retrieves an access token by sending a POST request to a specified
    URL with necessary parameters.
    :return: The function `get_access_token` is returning the access token obtained from the API
    response after making a POST request to the token URL with the provided payload containing the
    client ID, client secret, and refresh token.
    """

    token_url = "https://api.amazon.com/auth/o2/token"

    payload = f"""grant_type=refresh_token&client_id={client_id}&client_secret={
        client_secret}&refresh_token={refresh_token}"""

    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

    token_response = requests.request(
        "POST", token_url, headers=headers, data=payload, timeout=300
    )

    response_content = json.loads(token_response.text)

    access_token_data = response_content["access_token"]

    return access_token_data


def request_data(
    session_data=None,
    operation_uri="",
    params: dict = None,
    payload=None,
    method="GET",
    url=None,
):
    """
    The function `request_data` sends a request to a specified API endpoint with optional parameters and
    handles various response scenarios.
    """

    endpoint_url = f"https://sellingpartnerapi-eu.amazon.com{operation_uri}?"
    request_url = ""

    if params:

        uri = "&".join([f"{k}={params[k]}" for k, v in params.items()])

    else:

        uri = ""

    if url:

        request_url = url

    else:

        request_url = endpoint_url + uri

    # Get the current time
    current_time = datetime.now(timezone.utc)

    # Format the time in the desired format
    formatted_time = current_time.strftime("%Y%m%dT%H%M%SZ")

    access_token = get_access_token()

    headers = {
        "Accept-Encoding": "gzip",
        "Content-Type": "application/json",
        "x-amz-access-token": f"{access_token}",
        "x-amz-date": formatted_time,
    }
    while True:

        if session_data:

            session_data.headers = headers
            try:

                init_request = session_data.get(f"{request_url}", data=payload)
            except ConnectionError:

                logger.error(
                    "Amazon request had a ConnectionError, sleeping for 5 seconds!"
                )

                time.sleep(5)

        else:

            init_request = requests.request(
                method, f"{request_url}", headers=headers, data=payload, timeout=30
            )

        if init_request.status_code in (200, 400):

            if init_request.text:

                jsonify = json.loads(init_request.text)

            else:

                logger.error("SP-API Has encountred an error. Try again later!")
                jsonify = None

            return jsonify

        if init_request.status_code == 403:

            session_data.headers["x-amz-access-token"] = access_token

        elif init_request.status_code == 429:

            time.sleep(65)

        else:

            error_message = json.loads(init_request.text)["errors"][0]["message"]

            if re.search("not found", error_message):

                return None

            else:

                logger.error(f"An error has occured || {error_message}")

                return None


def spapi_get_orders():
    """
    The function `spapi_get_orders` retrieves orders with a status of 'Shipped' from a specified
    marketplace and processes them in batches of 30.
    """

    params = {
        "MarketplaceIds": MarketPlaceID,
        "OrderStatuses": "Shipped",
        "MaxResultsPerPage": 100,
        "CreatedAfter": "2019-10-07T17:58:48.017Z",
    }

    formatted_data = request_data("/orders/v0/orders/", params)["payload"]

    orders = formatted_data["Orders"]

    orders_dict = []

    request_count = 1

    count = 0

    next_token = formatted_data.get("NextToken")

    def spapi_getorderitems(max_requests, orders_list):
        """
        The function `spapi_getOrderItems` retrieves order items data for a list of orders and processes
        it to extract basic order information.

        :param max_requests: The `max_requests` parameter in the `spapi_getOrderItems` function
        represents the maximum number of requests that can be made before processing the collected data.
        In this case, it is used to control how many requests are made before processing the order items
        data
        :param orders_list: It seems like the code snippet you provided is incomplete. You mentioned
        that you wanted to provide information about the `orders_list`, but the code snippet cuts off
        before the `orders_list` is shown. Could you please provide the `orders_list` data so that I can
        assist you further with understanding the
        :return: The function `spapi_getOrderItems` returns the `orders_list` and `count` variables
        after processing the order items and extracting basic information about each order.
        """

        count = 0
        params = {"MarketplaceIds": MarketPlaceID}

        items_dict = []
        item_request_count = 1

        with ThreadPoolExecutor(max_workers=7) as executor:

            futures = []

            for order in orders_list:

                if "ASIN" not in order:

                    futures.append(
                        executor.submit(
                            request_data,
                            f"""/orders/v0/orders/{
                            order['AmazonOrderId']}/orderItems""",
                            params,
                        )
                    )

                    item_request_count += 1

                    if item_request_count % max_requests == 0:

                        for future in futures:

                            result = future.result()["payload"]

                            if result:
                                items_dict.append(result)

                        orderbasic_info(orders_list=orders_list, item_list=items_dict)

                        item_request_count = 0

                        items_dict = []

        return orders_list, count

    def orderbasic_info(item_list, orders_list):
        """
        The function `orderBasic_info` processes item and order data to extract relevant information and
        append it to a list.

        :param item_list: The `item_list` parameter is a list containing information about items, such
        as their ASIN, quantity shipped, price, seller SKU, title, etc. Each item in the list is
        represented as a dictionary with various key-value pairs
        :param orders_list: The function `orderbasic_info` takes two parameters: `item_list` and
        `orders_list`. The `item_list` parameter is a list of items with their information, and the
        `orders_list` parameter is a list of orders with order details
        :return: The function `orderbasic_info` returns two values:
        1. The updated `orders_list` after processing the item and order data.
        2. The count of items processed and added to the `orders_list`.
        """

        city = None
        county = None
        count = 0

        for order in orders_list:

            for item_data in item_list:

                if item_data["AmazonOrderId"] == order["AmazonOrderId"]:

                    try:
                        if (
                            "ShippingAddress" in order
                            and order["FulfillmentChannel"] == "MFN"
                            and isinstance(order["ShippingAddress"], dict)
                        ):
                            city = order["ShippingAddress"]["City"]
                            county = order["ShippingAddress"].get("County", None)

                        # Create a dictionary for each item's information and append it to data_list
                        if "ASIN" not in order:

                            for item in item_data["OrderItems"]:

                                data = {
                                    "AmazonOrderId": order.get("AmazonOrderId", None),
                                    "OrderStatus": order.get("OrderStatus", None),
                                    "EarliestShipDate": order.get(
                                        "EarliestShipDate", None
                                    ),
                                    "LatestShipDate": order.get("LatestShipDate", None),
                                    "PurchaseDate": order.get("PurchaseDate", None),
                                    "City": city,
                                    "County": county,
                                    "ASIN": item.get("ASIN", None),
                                    "QuantityShipped": item.get(
                                        "QuantityShipped", None
                                    ),
                                    "Amount": item["ItemPrice"]["Amount"],
                                    "SellerSKU": item.get("SellerSKU", None),
                                    "Title": item.get("Title", None),
                                }
                                orders_list.append(data)
                                count += 1

                    except KeyError:

                        if order in orders_list:

                            orders_list.remove(order)

        for index, order in enumerate(orders_list):
            for item_data in item_list:
                if (
                    item_data["AmazonOrderId"] == order["AmazonOrderId"]
                    and "ASIN" not in order
                ):
                    del orders_list[index]

        return orders_list, count

    while orders:

        futures = []

        if next_token:
            params = {
                "MarketplaceIds": MarketPlaceID,
                "NextToken": parse.quote(formatted_data["NextToken"]),
            }

            futures = request_data("/orders/v0/orders/", params)

            result = futures["payload"]

            next_token = result.get("NextToken", None)

            orders = result.get("Orders")

            request_count += 1

            for oi in orders:

                if orders_dict:

                    for io in orders_dict:

                        if io["AmazonOrderId"] == oi["AmazonOrderId"]:

                            break

                        count += 1

                        orders_dict.append(oi)

                        break
                else:
                    count += 1
                    orders_dict.append(oi)

            logger.info(f"{count} orders has been added")

            if request_count % 30 == 0:
                logger.info(f"Processing {count} orders please wait!")

                spapi_getorderitems(30, orders_dict)

                logger.info(
                    f"Processed {count} orders || Orders left: {len(orders_dict) - count}"
                )

                request_count = 0

            else:
                pass

    for data in orders_dict:

        if "MarketplaceId" in data:

            spapi_getorderitems(30, orders_dict)

            break

    return orders_dict


def spapi_getlistings(every_product: bool = False, local: bool = False):
    """
    The function `spapi_getListings` retrieves a report from an API, downloads and decompresses the
    report file, converts it from CSV to JSON format, and returns the inventory items as a list of
    dictionaries.
    """

    def process_list_in_chunks(my_list, chunk_size=20):
        """Processes a list in chunks of specified size.

        Args:
          my_list: The list to process.
          chunk_size: The size of each chunk. Defaults to 20.

        Yields:
          A chunk of the list.
        """
        for i in range(0, len(my_list), chunk_size):
            yield my_list[i : i + chunk_size]

    if local:

        dir_path = os.getcwd()
        matching_files = glob(os.path.join(dir_path, f"*{file_saved}*"))

        for file in matching_files:

            if re.search(r"\.csv", file):

                file_saved = file

    products = []
    report_items_request = ReportsV2().create_report(
        reportType=ReportType.GET_MERCHANT_LISTINGS_ALL_DATA,
        marketplaceIds=[MarketPlaceID],
    )

    while True:

        report_items_response = ReportsV2().get_report(
            reportId=report_items_request.payload["reportId"]
        )

        if report_items_response.payload["processingStatus"] == "DONE":

            break

        time.sleep(1)

    get_report_items_document = ReportsV2().get_report_document(
        reportDocumentId=report_items_response.payload["reportDocumentId"],
        download=True,
        decrypt=True,
    )
    report_string = get_report_items_document.payload["document"]

    if report_string.startswith("\ufeff"):

        report_string = report_string[1:]

    report_items_document = io.StringIO(report_string)
    report_reader = csv.DictReader(report_items_document, delimiter="\t")
    report_items_data = list(report_reader)
    products = [
    {
        "id": i["product-id"],
        "sku": i["seller-sku"],
        "listing-id": i["listing-id"],
        "quantity": int(i["quantity"]),
        "price": float(i['price']) if i['price'] else 0
    }
    for i in report_items_data
    if "quantity" in i and not re.search(r"\_fba", i["seller-sku"])]

    if not every_product:
        return products
    items_skus = [
        item["seller-sku"]
        for item in report_items_data
        if not re.search(r"\_fba", item["seller-sku"])
    ]

    catalog_item = CatalogItems()
    catalog_item.version = CatalogItemsVersion.V_2022_04_01
    items_skus_string_list = process_list_in_chunks(items_skus, 20)
    start_time = time.time()
    end_time = start_time + 2

    while time.time() < end_time:

        for sku_string in items_skus_string_list:

            sku_strings = ",".join(sku_string)
            catalog_items_request = catalog_item.search_catalog_items(
                marketplaceIds=[MarketPlaceID],
                includedData="attributes,identifiers,images,productTypes,summaries",
                locale="tr_TR",
                sellerId=AmazonSA_ID,
                identifiersType="SKU",
                identifiers=sku_strings,
                pageSize=20,
            )

            if catalog_items_request:
                for item in catalog_items_request.payload["items"]:

                    sku = [
                        i["identifier"]
                        for i in item["identifiers"][0]["identifiers"]
                        if i["identifierType"] == "SKU"
                    ]

                    summaries = item["summaries"][0]

                    identifiers = {
                        f"""{k}{item['identifiers'][0]['identifiers'].index(i)}""": v
                        for i in item["identifiers"][0]["identifiers"]
                        for k, v in i.items()
                    }

                    attributes = item["attributes"]

                    images = {
                        f"""link{item['images'][0]['images'].index(i)}""": i["link"]
                        for i in item["images"][0]["images"]
                        for k, v in i.items()
                        if v == "MAIN"
                    }

                    combined_dict = {**identifiers, **summaries, **attributes, **images}

                    products[sku[0]]["data"].update(combined_dict)

            time.sleep(1)

    products = [
        {"sku": k, "data": f} for k, v in products.items() for c, f in v.items()
    ]
    logger.info(f"Amazon fetched {len(products)} products")

    return products



def filter_order_data(orders_list, order, result, items):
    """
    The function `filter_orderData` updates order data in a list based on specified items and order
    information.
    """

    for item in items:

        try:

            logger.info(result.get("AmazonOrderId", None))

            data = {
                "ASIN": item.get("ASIN", None),
                "QuantityShipped": item.get("QuantityShipped", None),
                "Amount": item["ItemPrice"]["Amount"],
                "SellerSKU": item.get("SellerSKU", None),
                "Title": item.get("Title", None),
            }

            for order_item in orders_list:

                if result["AmazonOrderId"] == order_item["AmazonOrderId"]:

                    orders_list.remove(order_item)

                    order_item.update(data)

                    orders_list.append(order_item)

                    break

        except KeyError:

            if order in orders_list:

                orders_list.remove(order)

            continue

    return orders_list


def save_to_csv(data, filename=""):
    """
    The function `save_to_csv` takes a list of dictionaries, extracts keys from the dictionaries, and
    writes the data to a CSV file.

    :param data: The `data` parameter in the `save_to_csv` function is expected to be a list of
    dictionaries where each dictionary represents a row of data to be written to the CSV file. Each
    dictionary should have keys that represent the column headers in the CSV file, and the values
    represent the data for each
    :param filename: The `filename` parameter in the `save_to_csv` function is a string that represents
    the name of the CSV file where the data will be saved. If no filename is provided, the default value
    is an empty string
    """

    if data:

        keys = set()

        for item in data:

            keys.update(item.keys())

        with open(
            f"{filename}_data_list.csv", "w", newline="", encoding="utf-8"
        ) as csvfile:

            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))

            file_writer.writeheader()

            for d in data:

                file_writer.writerow(d)


def spapi_add_listing(data):

    for data_item in data.items():

        data_items = data_item[1]

        for product in data_items:
            
            product_data = product["data"]
            product_sku = product_data['stockCode']
            source_product_attrs = product_data["attributes"]
            product_images = {}
            bullet_points_list = textwrap.wrap(
                product_data["description"], width=len(product_data["description"]) // 5
            )
            bullet_points = [{"value": bullet_point} for bullet_point in bullet_points_list]
            size_match = [1, 1]
            size = 1
            color = None
            feature = None
            materyal = None
            style = None
            thickness = 1
            shape = None

            for i in enumerate(product_data["images"]):

                if i[0] == 0:

                    product_images["main_product_image_locator"] = [
                        {"media_location": i[1]["url"]}
                    ]

                else:

                    product_images[f"other_product_image_locator_{i[0]}"] = [
                        {"media_location": i[1]["url"]}
                    ]

            for atrr in source_product_attrs:

                if re.search("Boyut/Ebat", atrr["attributeName"]) or re.search(
                    "Beden", atrr["attributeName"]
                ):
                    if isinstance(atrr["attributeValue"], (int, float)):
                        size = atrr["attributeValue"]
                        size_match = atrr["attributeValue"].split("x")

                if re.search(r"Renk|Color", atrr["attributeName"]):

                    color = atrr["attributeValue"]

                if re.search("Özellik", atrr["attributeName"]):

                    feature = atrr["attributeValue"]

                if re.search("Materyal", atrr["attributeName"]):

                    materyal = atrr["attributeValue"]

                if re.search("Tema", atrr["attributeName"]):

                    style = atrr["attributeValue"]

                if re.search("Hav Yüksekliği", atrr["attributeName"]):

                    thickness = atrr["attributeValue"]
                    match = re.search(r"\d+", thickness)

                    if match:

                        result = match.group()
                        thickness = result

                if re.search("Şekil", atrr["attributeName"]):

                    shape = atrr["attributeValue"]

                else:

                    shape = "Dikdörtgen"

            while True:
                try:

                    product_definitions = ProductTypeDefinitions().search_definitions_product_types(
                        itemName=product_data["categoryName"],
                        marketplaceIds=MarketPlaceID,
                        searchLocale="tr_TR",
                        locale="tr_TR",
                    )
                    
                    if product_definitions.payload['productTypes'] is not []:
                        
                        break

                except Exception as e:

                    time.sleep(3)
                    continue            

            product_attrs = ProductTypeDefinitions().get_definitions_product_type(
                productType=product_definitions.payload["productTypes"][0]["name"],
                marketplaceIds=MarketPlaceID,
                requirements="LISTING",
                locale="tr_TR",
            )
            if product_attrs:
                file_path = f'amazon_{product_attrs.payload["productType"]}_attrs.json'
                if os.path.isfile(file_path):
                    pass
                else:
                    product_scheme = requests.get(
                        url=product_attrs.payload["schema"]["link"]["resource"]
                    )
                    scheme_json = json.loads(product_scheme.text)
                    category_attrs = extract_category_item_attrs(
                        file_data=scheme_json,
                        file_name=product_attrs.payload["productType"],
                    )
                data_payload = {
                    "productType": product_attrs.payload["productType"],
                    "requirements": "LISTING",
                    "attributes": {
                        "item_name": [{"value": product_data["title"]}],  #
                        "brand": [{"value": product_data["brand"]}],  #
                        "supplier_declared_has_product_identifier_exemption": [
                            {"value": True}
                        ],  #
                        "recommended_browse_nodes": [{"value": "13028044031"}],  #
                        "bullet_point": bullet_points,  #
                        "condition_type": [{"value": "new_new"}],  #
                        "fulfillment_availability": [
                            {
                                "fulfillment_channel_code": "DEFAULT",
                                "quantity": product_data["quantity"],
                                "lead_time_to_ship_max_days": "5",
                            }
                        ],  #
                        "gift_options": [
                            {"can_be_messaged": "false", "can_be_wrapped": "false"}
                        ],  #
                        "generic_keyword": [
                            {"value": product_data["title"].split(" ")[0]}  #
                        ],
                        "list_price": [
                            {
                                "currency": "TRY",
                                "value_with_tax": product_data["listPrice"],
                            }
                        ],  #
                        "manufacturer": [
                            {"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti."}
                        ],
                        "material": [{"value": materyal}],  #
                        "model_number": [{"value": product_data["productMainId"]}],  #
                        "number_of_items": [{"value": 1}],  #
                        "color": [{"value": color}],  #
                        "size": [{"value": size}],  #
                        "style": [{"value": style}],  #
                        "part_number": [{"value": product_sku}],  #
                        "pattern": [{"value": "Düz"}],  #
                        "product_description": [
                            {"value": product_data["description"]}
                        ],  #
                        "purchasable_offer": [
                        {
                            "currency": "TRY",
                            "our_price": [
                                {
                                    "schedule": [
                                        {
                                            "value_with_tax": product_data[
                                                "salePrice"
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    ],  #
                        "country_of_origin": [{"value": "TR"}],  #
                         #
                        "package_level": [{"value": "unit"}],
                        "customer_package_type": [{"value": "Standart Paketleme"}],
                    },
                    "offers": [
                        {
                            "offerType": "B2C",
                            "price": {
                                "currency": "TRY",
                                "currencyCode": "TRY",
                                "amount": product_data["salePrice"],
                            },
                        }
                    ],
                }
                category_attrs_list = {
                    "RUG": {
                        "product_site_launch_date": [
                            {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
                        ], 
                         "included_components": [
                            {"value": f"Tek adet {product_data['title']}"}
                        ],  #
                         "item_dimensions": [
                            {
                                "length": {"value": thickness, "unit": "millimeters"},
                                "width": {
                                    "value": size_match[1],
                                    "unit": "centimeters",
                                },
                                "height": {
                                    "value": size_match[0],
                                    "unit": "centimeters",
                                },
                            }
                        ],
                        "special_feature": [{"value": feature}],
                        "item_shape": [{"value": shape}],
                        "pile_height": [{"value": "Düşük Hav"}],
                        "item_thickness": [
                            {"decimal_value": thickness, "unit": "millimeters"}
                        ],
                        "item_length_width": [
                            {
                                "length": {
                                    "unit": "centimeters",
                                    "value": size_match[0],
                                },
                                "width": {
                                    "unit": "centimeters",
                                    "value": size_match[1],
                                },
                            }
                        ],
                        "rug_form_type": [{"value": "doormat"}],
                    },
                    "LITTER_BOX": {
                        "included_components": [
                            {"value": f"Tek adet {product_data['title']}"}
                        ],  
                        "target_audience_keyword": [
                            {
                                "value": "Kediler",
                            }
                        ],
                        "model_name": [
                            {
                                "value": product_data["productMainId"],
                            }
                        ],
                        "litter_box_type": [{"value": "disposable_litter_box"}],
                        "directions": [{"value": "Kedi tuvalet matı, kum taneciklerinin evin diğer bölgelerine yayılmasını önler. Tuvalet kabının önüne yerleştirilir ve düzenli olarak temizlenir. Haftada en az bir kez yıkanmalı ve ayda bir kez derinlemesine temizlenmelidir. Matın boyutu, tuvalet kabına uygun olmalı ve su geçirmez bir malzeme tercih edilmelidir."}],
                        "item_length_width_height": [
                        {
                            "length": {
                                "value": thickness,
                                "unit": "millimeters",
                            },
                            "width": {
                                "value": size_match[1],
                                "unit": "centimeters",
                            },
                            "height": {
                                "value": size_match[0],
                                "unit": "centimeters",
                            },
                        }
                    ],
                        "specific_uses_for_product": [{"value": "Cats"}],
                        "supplier_declared_dg_hz_regulation": [{"value": "not_applicable"}],
                        "rtip_manufacturer_contact_information": [{"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti; +90 552 361 11 11"}],
                        "warranty_description": [{"value": "30 Days"}],
                        "is_oem_authorized": [{"value": True}],
                        "oem_equivalent_part_number": [{"value": product_data["productMainId"]}],
                        "unit_count": [{"type": {"language_tag":"tr_TR", "value":"Adet"}, "value": 1}]
                    },
                    "EXERCISE_MAT": {
                        "supplier_declared_dg_hz_regulation": [{"value": "not_applicable"}],
                        "sport_type": [{"value": "Pilates"}],
                        "item_length_width_thickness": [
                            {
                                "thickness": {
                                    "value": thickness,
                                    "unit": "millimeters",
                                },
                                "width": {
                                    "value": size_match[1],
                                    "unit": "centimeters",
                                },
                                "length": {
                                    "value": size_match[0],
                                    "unit": "centimeters",
                                },
                            }
                        ],
                    },
                    "UTILITY_KNIFE": {
                        "supplier_declared_dg_hz_regulation": "not_applicable",
                    },
                }
                data_payload["attributes"].update(product_images)
                data_payload["attributes"].update(
                    category_attrs_list[product_attrs.payload["productType"]]
                )
                while True:
                    try:
                        listing_add_request = ListingsItems().put_listings_item(
                            sellerId=AmazonSA_ID,
                            sku=product_sku,
                            marketplaceIds=["A33AVAJ2PDY3EV"],
                            body=data_payload,
                        )
                        break
                    except Exception as e:
                        time.sleep(3)
                        continue
                if (
                    listing_add_request
                    and listing_add_request.payload["status"] == "ACCEPTED"
                ):
                    logger.info(
                        f"""New product added with code: {
                        product_sku}, qty: {product_data['quantity']}"""
                    )
                else:
                    logger.error(
                        f"""New product with code: {product_sku} creation has failed
                            || Reason: {listing_add_request}"""
                    )


def extract_category_item_attrs(file_data, file_name=""):

    amazon_attrs = file_data
    processed_attrs = {}
    temporary_attr = {}

    # Get the 'properties' from the loaded JSON
    properties = amazon_attrs.get("properties", {})

    for attribute_name, attribute_details in properties.items():

        sub_attributes = attribute_details
        temporary_attr[attribute_name] = {}

        if "items" in sub_attributes:
            items_attributes = sub_attributes["items"]
            items_properties = items_attributes.get("properties", {})

            for property_name, property_details in items_properties.items():
                temporary_attr[attribute_name][property_name] = {}

                if "examples" in property_details:
                    temporary_attr[attribute_name][property_name] = (
                        property_details.get("examples", [None])[0]
                    )
                else:
                    if "items" in property_details:
                        nested_items = property_details["items"]

                        if "required" in nested_items:
                            for required_obj in nested_items.get("required", []):
                                temporary_attr[attribute_name][property_name][
                                    required_obj
                                ] = {}

                                if "properties" in nested_items.get("properties", {}):
                                    obj_properties = nested_items["properties"].get(
                                        required_obj, {}
                                    )
                                    temporary_attr[attribute_name][property_name][
                                        required_obj
                                    ] = obj_properties.get("examples", [None])[0]
                                else:
                                    nested_properties = (
                                        nested_items["properties"]
                                        .get(required_obj, {})
                                        .get("items", {})
                                    )

                                    if "properties" in nested_properties:
                                        for sub_required in nested_properties.get(
                                            "required", []
                                        ):
                                            sub_property_details = nested_properties[
                                                "properties"
                                            ].get(sub_required, {})
                                            temporary_attr[attribute_name][
                                                property_name
                                            ][required_obj][
                                                sub_required
                                            ] = sub_property_details.get(
                                                "examples", [None]
                                            )[
                                                0
                                            ]
                    else:
                        if "properties" in property_details:
                            for (
                                inner_property_name,
                                inner_property_details,
                            ) in property_details["properties"].items():
                                temporary_attr[attribute_name][property_name][
                                    inner_property_name
                                ] = inner_property_details.get("examples", [None])[0]

        # Determine the type of the attribute
        attribute_type = sub_attributes.get("type")

        if attribute_type == "array":
            processed_attrs[attribute_name] = [temporary_attr[attribute_name]]
        else:
            processed_attrs[attribute_name] = temporary_attr[attribute_name]

    # Save the result to a new JSON file
    with open(f"amazon_{file_name}_attrs.json", "w", encoding="utf-8") as attrFile:
        json.dump(processed_attrs, attrFile, indent=4)
    return processed_attrs

class AmazonListingManager:

    def __init__(self) -> None:
        
        self.marketplace_id = os.environ.get("AMAZONTURKEYMARKETID")
        self.seller_id = os.environ.get("AMAZONSELLERACCOUNTID")

    def retry_with_backoff(self, func, *args, retries=5, **kwargs):
        """
        Retries a function with exponential backoff.

        Args:
            func (function): The function to retry.
            *args: Positional arguments for the function.
            retries (int): Number of retry attempts.
            **kwargs: Keyword arguments for the function.

        Returns:
            Any: The result of the function if successful.

        Raises:
            Exception: If the function fails after all retries.
        """
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
                attempt += 1
        raise Exception(f"All {retries} retries failed for function {func.__name__}")

    def fetch_category_attributes(self, category_name):
        """
        Fetches category-specific attributes based on the product type.

        Args:
            category_name (str): The name of the product category.

        Returns:
            dict: Category attributes for the product.
        """
        while True:
            product_definitions = self.retry_with_backoff(
                ProductTypeDefinitions().search_definitions_product_types,
                itemName=category_name,
                marketplaceIds=self.marketplace_id,
                searchLocale="tr_TR",
                locale="tr_TR",
            )
            if len(product_definitions.payload['productTypes']) > 0:
                break
            time.sleep(3)

        product_type = product_definitions.payload["productTypes"][0]["name"]

        product_attrs = self.retry_with_backoff(
            ProductTypeDefinitions().get_definitions_product_type,
            productType=product_type,
            marketplaceIds=self.marketplace_id,
            requirements="LISTING",
            locale="tr_TR",
        )

        return self.download_attribute_schema(product_attrs.payload)

    def get_category_type_attrs(self, product_type, product_data, features: dict):

        thickness = features['thickness']
        size_match = features['size_match']
        feature = features['feature']
        shape = features['shape']

        category_attrs_list = {
                    "RUG": {
                        "product_site_launch_date": [
                            {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
                        ], 
                         "included_components": [
                            {"value": f"Tek adet {product_data['title']}"}
                        ],  #
                         "item_dimensions": [
                            {
                                "length": {"value": thickness, "unit": "millimeters"},
                                "width": {
                                    "value": size_match[1],
                                    "unit": "centimeters",
                                },
                                "height": {
                                    "value": size_match[0],
                                    "unit": "centimeters",
                                },
                            }
                        ],
                        "special_feature": [{"value": feature}],
                        "item_shape": [{"value": shape}],
                        "pile_height": [{"value": "Düşük Hav"}],
                        "item_thickness": [
                            {"decimal_value": thickness, "unit": "millimeters"}
                        ],
                        "item_length_width": [
                            {
                                "length": {
                                    "unit": "centimeters",
                                    "value": size_match[0],
                                },
                                "width": {
                                    "unit": "centimeters",
                                    "value": size_match[1],
                                },
                            }
                        ],
                        "rug_form_type": [{"value": "doormat"}],
                    },
                    "LITTER_BOX": {
                        "included_components": [
                            {"value": f"Tek adet {product_data['title']}"}
                        ],  
                        "target_audience_keyword": [
                            {
                                "value": "Kediler",
                            }
                        ],
                        "model_name": [
                            {
                                "value": product_data["productMainId"],
                            }
                        ],
                        "litter_box_type": [{"value": "disposable_litter_box"}],
                        "directions": [{"value": "Kedi tuvalet matı, kum taneciklerinin evin diğer bölgelerine yayılmasını önler. Tuvalet kabının önüne yerleştirilir ve düzenli olarak temizlenir. Haftada en az bir kez yıkanmalı ve ayda bir kez derinlemesine temizlenmelidir. Matın boyutu, tuvalet kabına uygun olmalı ve su geçirmez bir malzeme tercih edilmelidir."}],
                        "item_length_width_height": [
                        {
                            "length": {
                                "value": thickness,
                                "unit": "millimeters",
                            },
                            "width": {
                                "value": size_match[1],
                                "unit": "centimeters",
                            },
                            "height": {
                                "value": size_match[0],
                                "unit": "centimeters",
                            },
                        }
                    ],
                        "specific_uses_for_product": [{"value": "Cats"}],
                        "supplier_declared_dg_hz_regulation": [{"value": "not_applicable"}],
                        "rtip_manufacturer_contact_information": [{"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti; +90 552 361 11 11"}],
                        "warranty_description": [{"value": "30 Days"}],
                        "is_oem_authorized": [{"value": True}],
                        "oem_equivalent_part_number": [{"value": product_data["productMainId"]}],
                        "unit_count": [{"type": {"language_tag":"tr_TR", "value":"Adet"}, "value": 1}]
                    },
                    "EXERCISE_MAT": {
                        "supplier_declared_dg_hz_regulation": [{"value": "not_applicable"}],
                        "sport_type": [{"value": "Pilates"}],
                        "item_length_width_thickness": [
                            {
                                "thickness": {
                                    "value": thickness,
                                    "unit": "millimeters",
                                },
                                "width": {
                                    "value": size_match[1],
                                    "unit": "centimeters",
                                },
                                "length": {
                                    "value": size_match[0],
                                    "unit": "centimeters",
                                },
                            }
                        ],
                    },
                    "UTILITY_KNIFE": {
                        "supplier_declared_dg_hz_regulation": "not_applicable",
                    },
                }
        return category_attrs_list[product_type]

    def download_attribute_schema(self, raw_category_attrs):
        """
        Downloads and caches the attribute schema for a product type.

        Args:
            raw_category_attrs (dict): The product attribute data.

        Returns:
            dict: The schema for the product attributes.
        """
        file_path = f'amazon_{raw_category_attrs["productType"]}_attrs.json'
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                return raw_category_attrs, json.load(file)
        else:
            product_scheme = requests.get(url=raw_category_attrs["schema"]["link"]["resource"])
            scheme_json = product_scheme.json()
            category_attrs = extract_category_item_attrs(file_data=scheme_json, file_name=raw_category_attrs["productType"])
            with open(file_path, 'w') as file:
                json.dump(category_attrs, file)
            return raw_category_attrs, category_attrs

    def extract_category_item_attrs(self, file_data, file_name=""):
        """
        Extracts and processes the attribute properties from Amazon category item data.

        Args:
            file_data (dict): The JSON data containing Amazon item attributes.
            file_name (str): The name to be used when saving the extracted attributes to a file.

        Returns:
            dict: A dictionary of processed attributes.
        """

        processed_attrs = {}

        # Get the 'properties' from the loaded JSON
        properties = file_data.get("properties", {})

        def process_property_details(property_details):
            """
            Processes the property details, extracting examples or nested required properties.

            Args:
                property_details (dict): The details of a property.

            Returns:
                dict or any: Processed property details or the example value if available.
            """
            if "examples" in property_details:
                return property_details.get("examples", [None])[0]
            if "items" in property_details:
                nested_items = property_details["items"]
                nested_properties = nested_items.get("properties", {})
                return {
                    required: nested_properties.get(required, {}).get("examples", [None])[0]
                    for required in nested_items.get("required", [])
                }
            if "properties" in property_details:
                return {
                    inner_property: process_property_details(inner_details)
                    for inner_property, inner_details in property_details["properties"].items()
                }
            return {}

        for attribute_name, attribute_details in properties.items():
            attribute_type = attribute_details.get("type")
            processed_attr = process_property_details(attribute_details)

            if attribute_type == "array":
                processed_attrs[attribute_name] = [processed_attr]
            else:
                processed_attrs[attribute_name] = processed_attr

        # Save the result to a new JSON file
        with open(f"amazon_{file_name}_attrs.json", "w", encoding="utf-8") as attrFile:
            json.dump(processed_attrs, attrFile, indent=4)

        return processed_attrs
    
    def extract_attributes(self, attributes):
        """
        Extracts relevant attributes from the product's attributes.

        Args:
            attributes (list): List of product attributes.

        Returns:
            dict: Extracted attributes.
        """
        size_match = [1, 1]
        size, color, feature, materyal, style, thickness, shape = 1, None, None, None, None, 1, "Dikdörtgen"

        for attr in attributes:
            attr_name = attr["attributeName"]
            attr_value = attr["attributeValue"]
            if re.search(r"Boyut/Ebat|Beden", attr_name):
                if isinstance(attr_value, (int, float)):
                    size = attr_value
                    size_match = str(attr_value).split("x")
            elif re.search(r"Renk|Color", attr_name):
                color = attr_value
            elif re.search(r"Özellik", attr_name):
                feature = attr_value
            elif re.search(r"Materyal", attr_name):
                materyal = attr_value
            elif re.search(r"Tema", attr_name):
                style = attr_value
            elif re.search(r"Hav Yüksekliği", attr_name):
                match = re.search(r"\d+", attr_value)
                if match:
                    thickness = match.group()
            elif re.search(r"Şekil", attr_name):
                shape = attr_value

        return {
            "size": size,
            "size_match": size_match,
            "color": color,
            "feature": feature,
            "style": style,
            "material": materyal,
            "thickness": thickness,
            "shape": shape,
        }

    def build_image_payload(self, images):
        """
        Builds the image payload for the listing.

        Args:
            images (list): List of image URLs.

        Returns:
            dict: Image payload dictionary.
        """
        product_images = {}
        for i, image in enumerate(images):
            if i == 0:
                product_images["main_product_image_locator"] = [{"media_location": image["url"]}]
            else:
                product_images[f"other_product_image_locator_{i}"] = [{"media_location": image["url"]}]
        return product_images
   
    def build_payload(self, product_data):
        """
        Builds the payload required for adding a listing to Amazon.

        Args:
            product_data (dict): The product data.

        Returns:
            dict: The payload required for the SP-API request.
        """
        # Prepare bullet points
        bullet_points_list = textwrap.wrap(product_data["description"], width=len(product_data["description"]) // 5)
        bullet_points = [{"value": bullet_point} for bullet_point in bullet_points_list]

        # Prepare product images
        product_images = self.build_image_payload(product_data["images"])

        # Extract attributes        
        self.attributes = self.extract_attributes(product_data["attributes"])

        # Fetch category attributes and build the complete payload
        raw_category_attrs, category_attrs = self.fetch_category_attributes(product_data["categoryName"])

        payload = {
            "productType": raw_category_attrs["productType"],
            "requirements": "LISTING",
            "attributes": {
                "item_name": [{"value": product_data["title"]}],
                "brand": [{"value": product_data["brand"]}],
                "supplier_declared_has_product_identifier_exemption": [{"value": True}],
                "recommended_browse_nodes": [{"value": "13028044031"}],
                "bullet_point": bullet_points,  
                "condition_type": [{"value": "new_new"}],  
                "fulfillment_availability": [{"fulfillment_channel_code": "DEFAULT","quantity": product_data["quantity"],"lead_time_to_ship_max_days": "5"}],
                "gift_options": [{"can_be_messaged": "false", "can_be_wrapped": "false"}], 
                "generic_keyword": [{"value": product_data["title"].split(" ")[0]}],
                "list_price": [{"currency": "TRY","value_with_tax": product_data["listPrice"],}],
                "manufacturer": [{"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti."}],
                "material": [{"value": self.attributes["material"]}],
                "model_number": [{"value": product_data["productMainId"]}],
                "number_of_items": [{"value": 1}], 
                "color": [{"value": self.attributes["color"]}],
                "size": [{"value": self.attributes["size"]}],
                "style": [{"value": self.attributes["style"]}],
                "part_number": [{"value": product_data["productMainId"]}],
                "pattern": [{"value": "Düz"}],
                "product_description": [{"value": product_data["description"]}],
                "purchasable_offer": [{"currency": "TRY","our_price": [{"schedule": [{"value_with_tax": product_data["salePrice"]}]}],}],
                "country_of_origin": [{"value": "TR"}],
                "package_level": [{"value": "unit"}],
                "customer_package_type": [{"value": "Standart Paketleme"}],
                **product_images,
            },
            "offers": [
                {
                    "offerType": "B2C",
                    "price": {"currency": "TRY", "currencyCode": "TRY", "amount": product_data["salePrice"]},
                }
            ],
        }

        specific_attrs = self.get_category_type_attrs(raw_category_attrs["productType"], product_data, self.attributes)
        payload["attributes"].update(specific_attrs)

        return payload

    def submit_listing(self, product_sku, payload):
        """
        Submits the listing to Amazon.

        Args:
            product_sku (str): The SKU of the product.
            payload (dict): The payload for the SP-API request.

        Returns:
            None
        """
        listing_add_request = self.retry_with_backoff(
            ListingsItems().put_listings_item,
            sellerId=self.seller_id,
            sku=product_sku,
            marketplaceIds=self.marketplace_id,
            body=payload,
        )
        if listing_add_request and listing_add_request.payload["status"] == "ACCEPTED":
            logger.info(f"New product added with code: {product_sku}, qty: {payload['attributes']['fulfillment_availability'][0]['quantity']}")
        else:
            logger.error(f"New product with code: {product_sku} creation has failed || Reason: {listing_add_request}")

    def add_listings(self, product_data):
        """
        Adds product listings to Amazon.

        Args:
            data (dict): A dictionary containing product data to be listed on Amazon.

        Returns:
            None
        """
        for _, data_items in product_data.items():
            for product in data_items:
                product_data = product["data"]
                product_sku = product_data['stockCode']
                try:
                    payload = self.build_payload(product_data)
                    self.submit_listing(product_sku, payload)
                except Exception as e:
                    logger.error(f"Failed to process product {product_sku}: {e}", exc_info=True)

    def update_listing(self, product_data: dict):
        """
        The function `spapi_updateListing` updates a product listing on Amazon Seller Central with a new
        quantity value.

        :param product: The `spapi_updateListing` function is designed to update a listing on Amazon
        Seller Central using the Selling Partner API
        """

        sku = product_data["sku"]    
        qty = product_data["quantity"]
        price = product_data["price"]
        params = {"marketplaceIds": MarketPlaceID, "issueLocale": "en_US"}

        data_payload = json.dumps(
            {
                "productType": "HOME_BED_AND_BATH",
                "patches": [
                    {
                        "op": "replace",
                        "path": "/attributes/fulfillment_availability",
                        "value": [
                            {
                                "fulfillment_channel_code": "DEFAULT",
                                "quantity": qty,
                                "marketplace_id": "A33AVAJ2PDY3EV",
                            }
                        ],
                    }
                ],
            },
            {
                    "op": 'replace',
                    "path": '/attributes/purchasable_offer',
                    "value": [{
                        "purchasable_offer": [{
                            "currency": "TRY",
                            "our_price": [{
                                "schedule": [{
                                    "value_with_tax": price
                                }]
                            }],
                            "marketplace_id": 'A33AVAJ2PDY3EV'
                        }],
                    }]
                }
        )

        listing_update_request = request_data(
            operation_uri=f"/listings/2021-08-01/items/{AmazonSA_ID}/{sku}",
            params=params,
            payload=data_payload,
            method="PATCH",
        )

        if listing_update_request and listing_update_request["status"] == "ACCEPTED":

            logger.info(
                f"""Product with code: {
                product_data["sku"]}, New value: {product_data["quantity"]}, New price: {product_data["price"]} updated successfully"""
            )

        else:

            logger.error(
                f"""Product with code: {product_data["sku"]} failed
                  to update || Reason: {listing_update_request}"""
            )



