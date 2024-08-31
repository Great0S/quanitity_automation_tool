""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

from enum import Enum
import logging
import re
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from tui import ProductManagerApp
from rich.logging import RichHandler
from rich.prompt import Prompt
from typing import Dict, List, Any

from api.amazon_seller_api import (
    AmazonListingManager,
    spapi_add_listing,
    spapi_getlistings,
    spapi_update_listing,
)
from api.hepsiburada_api import Hb_API
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getpttavm_procuctskdata, pttavm_updatedata
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import N11API
from api.wordpress_api import (
    create_wordpress_products,
    get_wordpress_products,
    update_wordpress_products,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
hpapi = Hb_API()
n11api = N11API()
amznApi = AmazonListingManager()

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

        source_platform, source_codes = filter_data(
            every_product, local, [source])
        
        target_platforms, target_codes = filter_data(
            every_product, local, target)
        
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
        "amazon_data": spapi_getlistings(every_product),
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


def process_update_data(source=None, use_source=False, targets=None, options=None):
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
    platform_updates = filter_items_data(
        data=data_lists,
        source=source,
        use_source=use_source,
        target=targets,
        every_product=all_data,
    )
    # Filter platform_updates by createdTime and updatedTime from source
    if use_source:

        for item in platform_updates:

            source_data = platform_updates[item][0]["data"]
            product_createdTime = datetime.fromtimestamp(
                source_data["createDateTime"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            product_updatedTime = datetime.fromtimestamp(
                source_data["lastUpdateDate"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            platform_updates[item][1]["createDateTime"] = product_createdTime
            platform_updates[item][1]["lastUpdateDate"] = product_updatedTime

    logger.info(f"""Product updates count is {len(platform_updates)}""")

    return platform_updates


def filter_items_data(
    data="",
    source="",
    use_source=False,
    target="",
    every_product: bool = False,
    no_match=False,
):
    """
    The function `filter_items_data` compares quantity values
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
        non_matching_items = get_non_matching_items(data, source, target)

    else:

        if source:
            del platforms[platforms.index(source)]

        for platform in platforms:
            if f"{platform}_data" in data:
                if use_source:

                    for platform_item in data[f"{platform}_data"]:
                        for source_item in data[f"{source}_data"]:

                            if source_item["sku"] == platform_item["sku"]:

                                params = {
                                    "source_platform": source,
                                    "target_platform": platform,
                                    "source_item": source_item,
                                    "target_item": platform_item,
                                }

                                add_to_matching_items(
                                    matching_items, params, every_product)
                                break

                else:

                    for platform_item in data[f"{platform}_data"]:

                        add_items_without_source(
                            every_product, matching_items, platform, platform_item)

    if non_matching_items:

        matching_items = non_matching_items

    if matching_items:

        if not every_product:

            changed_values = generate_changed_values(matching_items, use_source)

        else:

            if use_source:

                changed_values = get_product_variants(matching_items)

            else:

                for item_key, item_val in matching_items.items():

                    products = item_val

                    if len(products) > 1:

                        changed_values.extend([product["data"]
                                              for product in products])

                    else:

                        changed_values = matching_items
                        break

    return changed_values

def get_product_variants(matching_items: Dict[Any, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups items by their productMainId and returns a dictionary with productMainId as keys.

    Args:
        matching_items (Dict[Any, List[Dict[str, Any]]]): A dictionary where keys are item identifiers
            and values are lists containing item data.

    Returns:
        Dict[str, List[Dict[str, Any]]]: A dictionary where each key is a productMainId and the value
            is a list of dictionaries containing platform and data information for that productMainId.
    """
    group_codes = {}

    for item in matching_items:
        item_data = matching_items[item][0]
        group_code = item_data['data']['productMainId']

        if item_data['data']['quantity'] == 0:
            continue
       
        if group_code in group_codes:
            group_codes[group_code].append({"platform": item_data['platform'], "data": item_data['data']})
        else:
            group_codes[group_code] = [{"platform": item_data['platform'], "data": item_data['data']}]
    
    return group_codes

def get_non_matching_items(data, source, target):
    """Helper function to get non matching items."""

    non_matching_items = {}

    if f"{target}_data" in data:

        target_skus = list(item["sku"] for item in data[f"{target}_data"])
        for source_item in data[f"{source}_data"]:

            source_item_sku = source_item["sku"]
            if (source_item_sku not in target_skus and source_item_sku not in non_matching_items):

                non_matching_items[source_item_sku] = [
                    {"platform": target, "data": source_item["data"]}]

        return non_matching_items

    else:

        return non_matching_items

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
                    if source_val["qty"] == 0:

                        pass

                    changed_values.append(
                        {
                            "id": product["id"],
                            "sku": sku,
                            "price": source_val.get("price", 0),
                            "qty": str(source_val["qty"]),
                            "platform": product["platform"],
                        }
                    )

    return changed_values

def add_items_without_source(every_product, matching_items, platform, target_item):
    """Helper function to add items without considering the source."""

    qty = (
        int(target_item.get("data", {}).get("quantity", 0))
        if "data" in target_item
        else target_item.get("qty", 0)
    )
    item_id = target_item.get("data", {}).get("id", target_item.get("id"))
    price = target_item.get("price", 0)

    if target_item["sku"] in matching_items:
        if every_product:
            matching_items[target_item["sku"]].append(
                {"platform": platform, "data": target_item["data"]}
            )
        else:
            matching_items[target_item["sku"]].append(
                {"platform": platform, "id": item_id, "price": price, "qty": qty}
            )
    else:
        if every_product:
            matching_items[target_item["sku"]] = [
                {"platform": platform, "data": target_item["data"]}
            ]
        else:
            matching_items[target_item["sku"]] = [
                {"platform": platform, "id": item_id, "price": price, "qty": qty}
            ]

def add_to_matching_items(matching_items, params, every_product):
    """Helper function to add matching items to the matching_items dictionary."""

    source_item = params["source_item"]
    target_item = params["target_item"]
    target = params["target_platform"]
    source = params["source_platform"]

    if every_product:
        matching_items[source_item["sku"]] = [
            {"platform": source, "data": source_item["data"]},
            {"platform": target, "data": target_item["data"]}            
        ]
    else:
        matching_items[source_item["sku"]] = [
            {
                "platform": target,
                "id": target_item.get("id", None),
                "price": target_item.get("price", 0),
                "qty": target_item.get("qty", 0),
            }
        ]
    
class App(Enum):

    N11 = "n11"
    HEPSIBURADA = "hepsiburada"
    AMAZON = "amazon"
    PTTAVM = "pttavm"
    PAZARAMA = "pazarama"
    TRENDYOL = "trendyol"
    WORDPRESS = "wordpress"

    def get_data(
    every_product: bool = False,
    local: bool = False,
    source: str = None,
    targets: list = None,
    match: bool = False):
        """
        The `get_data()` function retrieves stock data
        from various platforms and returns specific data and
        lists related to the retrieved information.

        Parameters:
        - every_product (bool): Whether to retrieve all products or not.
        - local (bool): Whether to retrieve local data or not.
        - source (str): The source platform to retrieve data from.
        - targets (list): List of target platforms to retrieve data from.
        - match (bool): Whether to match the data between source and targets.

        Returns:
        - dict: Data from target platforms, possibly including source platform data.
        - list: Combined list of all unique codes from source and targets.
        """

        if targets:

            target = targets if isinstance(targets, list) else [targets]

            try:
                # Retrieve data from source and target platforms
                source_platform, source_codes = App.filter_data(every_product, local, [source])
    
                target_platforms, target_codes = App.filter_data(every_product, local, target) if targets else ({}, [])
    
                # Combine codes from source and targets, ensuring uniqueness
                all_codes = list(set(source_codes + target_codes))
    
                # Include source platform data in target platforms if applicable
                if source_platform and f"{source}_data" in source_platform:
                    target_platforms[f"{source}_data"] = source_platform[f"{source}_data"]
    
                return target_platforms, all_codes
    
            except Exception as e:
                logger.error(f"An error occurred while retrieving data: {e}")
                return {}, []
            
        data_content = {
            "trendyol_data": get_trendyol_stock_data(every_product),
            "n11_data": n11api.get_products(every_product),
            "hepsiburada_data": hpapi.get_listings(every_product),
            "pazarama_data": getPazarama_productsList(every_product),
            "wordpress_data": get_wordpress_products(every_product),
            "pttavm_data": getpttavm_procuctskdata(every_product),
            "amazon_data": spapi_getlistings(every_product),
            }

        return data_content, []
    
    def get_date_range(date_input):

        if date_input == "1":
            end_date = datetime.now()
            start_date = end_date - relativedelta(months=1)
        elif date_input == "2":
            start_date = datetime.strptime(Prompt.ask("Enter the start date (YYYY-MM-DD): "), "%Y-%m-%d")
            end_date = datetime.strptime(Prompt.ask("Enter the end date (YYYY-MM-DD): "), "%Y-%m-%d")
        else:
            start_date, end_date = None, None

        return start_date, end_date

    def filter_data(every_product, local, targets):
        """
        The function `filter_data` filters and retrieves
        stock data for different platforms based on
        specified targets.

        Parameters:
        - every_product (bool): Whether to retrieve all products or not.
        - local (bool): Flag to determine if local data should be used.
        - targets (list): List of target platforms to retrieve data from.

        Returns:
        - dict: Retrieved data from target platforms.
        - list: List of SKUs (codes) from the retrieved data.
        """

        data_content = {}
        codes = []

        # Mapping of platform names to their respective data retrieval functions
        platform_to_function = {
            "n11": n11api.get_products,
            "hepsiburada": hpapi.get_listings,
            "amazon": spapi_getlistings,
            "pttavm": getpttavm_procuctskdata,
            "pazarama": getPazarama_productsList,
            "wordpress": get_wordpress_products,
            "trendyol": get_trendyol_stock_data,
        }

        # Loop through each target and retrieve data
        for target in targets:
            function = platform_to_function.get(target)
            if function:
                data = function(every_product)
                data_content[f"{target}_data"] = data

                # Extract codes (SKUs) from the data
                codes.extend(item["sku"] for item in data)

        return data_content, codes

    def filter_post_data_by_date(post_data, start_date, end_date):

        if not start_date and not end_date:
            return post_data

        return {
            sku: data for sku, data in post_data.items()
            if start_date <= datetime.strptime(data[1]["lastUpdateDate"], "%Y-%m-%d") <= end_date
        }

    def process_update_data(source=None, use_source=False, targets=None, options=None):
        """
        The function `process_update_data` retrieves data, processes
        stock updates from different platforms, and returns the
        platform updates.
        """

        # Validate options
        if options not in [None, "full", "info"]:
            logger.error(f"Invalid options value: {options}")
            return {}

        # Determine if all data should be retrieved based on options
        all_data = options in ["full", "info"]

        try:
            # Retrieve data based on the options provided
            data_lists, _ = App.get_data(
                every_product=all_data, source=source, targets=targets
            )

            # Return early if no data is retrieved
            if not data_lists:
                logger.info("No data retrieved. Exiting.")
                return {}

            # Process the retrieved data to filter relevant platform updates
            platform_updates = filter_items_data(
                data=data_lists,
                source=source,
                use_source=use_source,
                target=targets,
                every_product=all_data,
            )

            # If source data should be used, convert timestamps to readable dates
            if use_source:
                for item_id, (source_data, update_data) in platform_updates.items():
                    try:
                        product_createdTime = datetime.fromtimestamp(
                            source_data['data']['createDateTime'] / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        product_updatedTime = datetime.fromtimestamp(
                            source_data['data']["lastUpdateDate"] / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d")

                        update_data["createDateTime"] = product_createdTime
                        update_data["lastUpdateDate"] = product_updatedTime
                    except (KeyError, ValueError) as e:
                        logger.error(
                            f"Error processing timestamps for item {item_id}: {e}"
                        )
                        continue

            logger.info(f"Product updates count is {len(platform_updates)}")

            return platform_updates

        except Exception as e:
            logger.error(f"An error occurred while processing update data: {e}")
            return {}

    def execute_platform_updates(platform, func, post_data, options, source):

        try:
            if isinstance(post_data, list):
                for post in post_data:
                    if platform.value == post['platform']:

                        func(post)
            else:
                if platform.value == post_data['platform']:
                    func(post_data)

            # logger.info(f"Successfully updated {len(post_data)} products on {platform.name}.")
        except Exception as e:
            logger.error(f"Failed to update products on {platform.name}. Error: {e}")

    def execute_updates(source=None, use_source=False, targets=None, options=None):
        """
        The function `execute_updates` processes update data
        for different platforms and calls corresponding
        update functions based on the platform.
        """

        platform_to_function = {
            App.N11: n11api.update_products,
            App.HEPSIBURADA: hpapi.update_listing,
            App.AMAZON: spapi_update_listing,
            App.PTTAVM: pttavm_updatedata,
            App.PAZARAMA: pazarama_updateRequest,
            App.TRENDYOL: post_trendyol_data,
            App.WORDPRESS: update_wordpress_products,
        }
        date_input = None

        logger.info("Starting updates...")

        post_data = App.process_update_data(source=source, use_source=use_source, targets=targets, options=options)
        if not post_data:

            logger.info("No data to process. Exiting.")
            return

        # Display updates if no specific options are provided
        if not options:
            for count, update in enumerate(post_data, start=1):
                logger.info(
                    f"{count}. Product with SKU {update['sku']} from {update['platform']} has a new stock! "
                    f"New stock: {update['qty']}"
                )

        while True:
            user_input = Prompt.ask("1. Update by date \n2. Update by SKU\n3. Continue without date\n4. Exit\nChoose an option:", choices=["1", "2", "3", "4"])
            
            if user_input == "3":
                pass

            elif user_input == "4":
                logger.info("Exiting the program.")
                break

            elif user_input in ["1", "2"]:
                date_input = Prompt.ask("1. Update by last month \n2. Custom date\n3. Exit\nChoose an option:", choices=["1", "2", "3"])
                if date_input == "3":
                    logger.info("Exiting the program.")
                    break  
            else:
                logger.error("Invalid choice. Please select a valid option.")

            start_date, end_date = App.get_date_range(date_input)

            logger.info("Update in progress...")

            # Filter by date if required
            filtered_post_data = App.filter_post_data_by_date(post_data, start_date, end_date)

            # Process updates
            for platform_enum, func in platform_to_function.items():

                if isinstance(targets, list):
                    if platform_enum.value in targets:
                        App.execute_platform_updates(platform_enum, func, filtered_post_data, options, source)
                elif platform_enum.value == targets:
                    App.execute_platform_updates(platform_enum, func, filtered_post_data, options, source)
                elif not source and not targets:
                    App.execute_platform_updates(platform_enum, func, filtered_post_data, options, source)

            logger.info("Updates completed.")

            break
            


def create_products(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS, LOCAL_DATA=False):

    platform_to_function = {
        "n11": n11api.add_products,
        "hepsiburada": hpapi.create_listing,
        "amazon": amznApi.add_listings,
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

    filtered_data = filter_items_data(
        data=data_lists,
        every_product=True,
        no_match=True,
        source=SOURCE_PLATFORM,
        target=TARGET_PLATFORM,
    )

    if filtered_data:

        platform_to_function[TARGET_PLATFORM](data=filtered_data)

    logger.info("Done")


def process(data_dict: dict = None):

    # Clear screen command depending on the OS
    if os.name == "nt":  # For Windows
        os.system("cls")
    else:  # For Linux and macOS
        os.system("clear")

    if data_dict:

        logger.info("User input recieved, processing...")

        try:

            for k, v in data_dict.items():

                if k == "update":

                    App.execute_updates(
                        source=data_dict["update"]["source"],
                        targets=data_dict["update"]["target"],
                        use_source=True if data_dict["update"]["options"] else False,
                        options=data_dict["update"]["options"],
                    )
                    break

                create_products(
                    SOURCE_PLATFORM=data_dict["create"]["source"],
                    TARGET_PLATFORM=data_dict["create"]["target"],
                    TARGET_OPTIONS=data_dict["create"]["options"],
                    LOCAL_DATA=data_dict["create"]["local_data"],
                )
                break

        except KeyboardInterrupt:

            logger.warning("The program has been interrupted.")
            logger.info("Shutting down...")
            exit()


if __name__ == "__main__":

    input_app = ProductManagerApp()
    results = input_app.run()
    process(results)
