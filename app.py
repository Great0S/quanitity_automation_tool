""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

import logging
import re
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from tui import ProductManagerApp
from rich.logging import RichHandler
from rich.prompt import Prompt

from api.amazon_seller_api import spapi_add_listing,spapi_getlistings,spapi_update_listing
from api.hepsiburada_api import Hb_API
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getpttavm_procuctskdata, pttavm_updatedata
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import N11API
from api.wordpress_api import create_wordpress_products,get_wordpress_products,update_wordpress_products


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)])
logger = logging.getLogger(__name__)
hpapi = Hb_API()
n11api = N11API()


def get_data(
    every_product: bool = False,
    local: bool = False,
    source: str = None,
    targets: list = None,
    match: bool = False,
):
    """
    The `get_data()` function retrieves stock data
    from various platforms and returns specific data and
    lists related to the retrieved information.
    """

    # Retrieve stock data from APIs
    if targets:

        target = targets if isinstance(targets, list) else [targets]

        source_platform, source_codes = filter_data(every_product, local, [source])
        target_platforms, target_codes = filter_data(every_product, local, target)
        all_codes = list(set(target_codes + source_codes))

        # We add the source platform data to the target platforms so they stay on one list
        target_platforms[f"{source}_data"] = source_platform[f"{source}_data"]

        return target_platforms, all_codes

    data_content = {
        "trendyol_data": get_trendyol_stock_data(every_product),
        "n11_data": n11api.get_products(every_product),        
        "hepsiburada_data": hpapi.get_listings(every_product),
        "pazarama_data": getPazarama_productsList(every_product),
        "wordpress_data": get_wordpress_products(every_product),
        "pttavm_data": getpttavm_procuctskdata(every_product),
        "amazon_data": spapi_getlistings(every_product)
    }

    return data_content, []


def filter_data(every_product, local, targets):
    """
    The function `filter_data` filters and retrieves
    stock data for different platforms based on
    specified targets.
    """

    data_content = {}
    codes = []
    platform_to_function = {
        "n11": n11api.get_products,
        "hepsiburada": hpapi.get_listings,
        "amazon": spapi_getlistings,
        "pttavm": getpttavm_procuctskdata,
        "pazarama": getPazarama_productsList,
        "wordpress": get_wordpress_products,
        "trendyol": get_trendyol_stock_data,
    }

    for name in targets:

        for platform, function in platform_to_function.items():

            if re.search(platform, name):
                
                data_content[f"{name}_data"] = function(every_product)

    for _, item in data_content.items():

        for item_data in item:

            codes.append(item_data["sku"])

    return data_content, codes


def process_update_data(source=None, use_source = False, targets=None, options=None):
    """
    The function `process_update_data` retrieves data, processes
    stock updates from different platforms, and returns the
    platform updates.
    """

    all_data = False

    if options:

        if options == "full" or options == "info":

            data_lists, _ = get_data(
                every_product=True, source=source, targets=targets)

            all_data = True

    else:

        data_lists, _ = get_data(source=source, targets=targets)

    # Initializing empty lists. These lists will be used
    # to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates = filter_quantity_data(
        data=data_lists, source=source, use_source = use_source, target=targets, every_product=all_data
    )
    # Filter platform_updates by createdTime and updatedTime from source
    if use_source:

        for item in platform_updates:

            source_data = platform_updates[item][1]['data']
            product_createdTime = datetime.fromtimestamp(source_data['createDateTime'] / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            product_updatedTime = datetime.fromtimestamp(source_data['lastUpdateDate'] / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            platform_updates[item][1]['createDateTime'] = product_createdTime
            platform_updates[item][1]['lastUpdateDate'] = product_updatedTime


    logger.info(f"""Product updates count is {len(platform_updates)}""")



    return platform_updates


def filter_quantity_data(data = '', source = '', use_source = False, target = '', every_product: bool = False, no_match = False):
    """
    The function `filter_data_list` compares quantity values
    for items across different platforms and returns a list of
    changed values and matching values.
    """

    changed_values = []

    platforms = [
        "trendyol",
        "n11",
        "amazon",
        "hepsiburada",
        "pazarama",
        "wordpress",
        "pttavm",
    ]
    matching_items = {}
    non_matching_items = {}


    if no_match:

        use_source = True

    for platform in platforms:
        if platform != source and f"{platform}_data" in data:
                if use_source:

                    target_skus = list(item["sku"] for item in data[f"{target}_data"])
                    for target_item in data[f"{platform}_data"]:                   
                    
                        # source = list(data.keys())[1]
                        for source_item in data[f"{source}_data"]:
                            if no_match:                                
                                platform = target
                                target_item_sku = target_item["sku"]

                                if target_item_sku not in target_skus and target_item_sku not in non_matching_items:
                                    non_matching_items[target_item_sku] = [{"platform": platform, "data": target_item["data"]}]

                                continue

                            if source_item["sku"] == target_item["sku"]: 
                                    
                                    params = {'source_platform': source, 'target_platform': platform, 'source_item': source_item, 'target_item': target_item}
                                                                   
                                    add_to_matching_items(matching_items, params, every_product)
                                    break                    

                else:
                    for target_item in data[f"{platform}_data"]:
                    
                        add_items_without_source(every_product, matching_items, platform, target_item)

    if non_matching_items:

        matching_items = non_matching_items

    if matching_items:

        if not every_product:

            changed_values = generate_changed_values(matching_items, use_source)

        else:

            if use_source:

                changed_values = matching_items

            else:

                for item_key, item_val in matching_items.items():

                    products = item_val

                    if len(products) > 1:

                        changed_values.extend([product["data"] for product in products])

                    else:

                        changed_values = matching_items
                        break

    return changed_values

def generate_changed_values(matching_items, use_source):
    """Helper function to generate changed values from matching_items."""
    changed_values = []

    for sku, products in matching_items.items():
        
        if len(products) > 1:
            
            if use_source:
                source_val = products[0]
            else:
                source_val = min(products, key=lambda x: x["qty"])

            

            for product in products:
                if source_val["qty"] != product["qty"]:
                    if source_val['qty'] == 0:

                        pass

                    changed_values.append({
                        "id": product["id"],
                        "sku": sku,
                        "price": source_val.get("price", 0),
                        "qty": str(source_val["qty"]),
                        "platform": product["platform"],
                    })
    
    return changed_values

def add_items_without_source(every_product, matching_items, platform, target_item):
    """Helper function to add items without considering the source."""
    
    qty = int(target_item.get('data', {}).get("quantity", 0)) if "data" in target_item else target_item.get("qty", 0)
    item_id = target_item.get('data', {}).get("id", target_item.get("id"))
    price = target_item.get("price", 0)

    if target_item["sku"] in matching_items:
        if every_product:
            matching_items[target_item["sku"]].append({"platform": platform, "data": target_item["data"]})
        else:
            matching_items[target_item["sku"]].append({"platform": platform, "id": item_id, "price": price, "qty": qty})
    else:
        if every_product:
            matching_items[target_item["sku"]] = [{"platform": platform, "data": target_item["data"]}]
        else:
            matching_items[target_item["sku"]] = [{"platform": platform, "id": item_id, "price": price, "qty": qty}]

def add_to_matching_items(matching_items, params, every_product):
    """Helper function to add matching items to the matching_items dictionary."""

    source_item = params['source_item']
    target_item = params['target_item']
    target = params['target_platform']
    source = params['source_platform']

    if every_product:
        matching_items[source_item["sku"]] = [
                                            {"platform": target, "data": target_item["data"]},
                                            {"platform": source, "data": source_item["data"]}
                                            ]
    else:        
        matching_items[source_item["sku"]] = [{"platform": target, "id": target_item.get("id", None), "price": target_item.get("price", 0), "qty": target_item.get("qty", 0)}]

def execute_updates(source = None, use_source = False, targets = None, options = None):
    """
    The function `execute_updates` processes update data
    for different platforms and calls corresponding
    update functions based on the platform.
    """

    platform_to_function = {
        "n11": n11api.update_products,
        "hepsiburada": hpapi.update_listing,
        "amazon": spapi_update_listing,
        "pttavm": pttavm_updatedata,
        "pazarama": pazarama_updateRequest,
        "trendyol": post_trendyol_data,
        "wordpress": update_wordpress_products,
    }

    logger.info("Starting updates...")

    post_data = process_update_data(source=source, use_source=use_source, targets=targets, options=options)
    one_month_back = None
    custom_date_input = None

    if post_data:

        count = 1

        if not options:

            for update in post_data:

                logger.info(
                    f"""{count}. Product with sku {update['sku']} from {update['platform']} has a new stock! || New stock: {update['qty']}"""
                )

                count += 1

        while True:

            logger.info(f"1. Update by date \n2. Update by sku\n3. Exit")
            user_input = Prompt.ask("Choose from the above options to continue?: ", choices=["1", "2", "3"])
            
            if user_input.lower() == "3":

                logger.info("Exiting the program.")

                break

            elif user_input.lower() in ["1","2"]:

                logger.info(f"1. Update by month from now \n2. Custom date\n3. Exit")
                date_input = Prompt.ask("Choose a date from the above options to continue?: ", choices=["1", "2", "3"])

                if date_input.lower() == "3":

                    logger.info("Exiting the program.")
                    break

                elif date_input.lower() == "1":

                    current_date = datetime.now()
                    one_month_back = current_date - relativedelta(months=1)

                elif date_input.lower() == "2":

                    custom_date_input = Prompt.ask("Please enter the required date with format Year-Month: ex. 2023-01")
                    custom_date_input = datetime.strptime(custom_date_input, "%Y-%m-%d")

                logger.info("Update in progress...")

                if options:
                    for platform, func in platform_to_function.items():
                        if isinstance(targets, list):
                            for target_platform in targets:
                                if platform == target_platform:

                                    func(products=post_data,
                                         options=options, source=source)
                                    
                        else:
                            if platform == targets:
                                    items_by_date = {}
                                    for post in post_data:
                                        
                                        source_item_lastUpdateDate = datetime.strptime(post_data[post][1]['lastUpdateDate'], "%Y-%m-%d")

                                        if one_month_back and one_month_back <= source_item_lastUpdateDate:
                                            items_by_date[post] = post_data[post]
                                        
                                        elif custom_date_input and custom_date_input <= source_item_lastUpdateDate:
                                            items_by_date[post] = post_data[post]
                                        
                                    if items_by_date:

                                        post_data = items_by_date

                                    func(products=post_data,
                                         options=options, source=source)

                else:

                    for post in post_data:
                        for platform, func in platform_to_function.items():
                            if platform == post["platform"]:

                                func(post)

                break

            else:

                logger.error(
                    "Invalid Prompt.ask. Please enter 'y' for yes or 'n' for no.")

def create_products(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS, LOCAL_DATA=False):

    platform_to_function = {
        "n11": n11api.add_products,
        "hepsiburada": hpapi.create_listing,
        "amazon": spapi_add_listing,
        "pttavm": pttavm_updatedata,
        "pazarama": pazarama_updateRequest,
        "trendyol": post_trendyol_data,
        "wordpress": create_wordpress_products,
    }

    data_lists, _ = get_data(
        every_product=True,
        local=LOCAL_DATA,
        source=SOURCE_PLATFORM,
        targets=[TARGET_PLATFORM],
        match=True,
    )

    filtered_data = filter_quantity_data(
        data=data_lists,
        every_product=True,
        no_match=True,
        source=None,
        target=TARGET_PLATFORM
    )

    if filtered_data:

        platform_to_function[TARGET_PLATFORM](data=filtered_data)

    logger.info("Done")

def process(data_dict: dict = None):

    # Clear screen command depending on the OS    
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Linux and macOS
        os.system('clear')

    if data_dict:

        logger.info("User input recieved, processing...")

        try:

            for k, v in data_dict.items():

                if k == 'update':

                    execute_updates(source=data_dict['update']['source'], 
                                    targets=data_dict['update']['target'], 
                                    use_source= True if data_dict['update']['options'] else False, 
                                    options=data_dict['update']['options'])
                    break

                create_products(SOURCE_PLATFORM=data_dict['create']['source'], 
                                TARGET_PLATFORM=data_dict['create']['target'], 
                                TARGET_OPTIONS=data_dict['create']['options'], 
                                LOCAL_DATA=data_dict['create']['local_data'])
                break

        except KeyboardInterrupt:

            logger.warning("The program has been interrupted.")
            logger.info("Shutting down...")
            exit()

            

if __name__ == "__main__":

    input_app = ProductManagerApp()
    results = input_app.run()
    process(results)