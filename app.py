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
from typing import Dict, List, Any, Optional, Tuple

from api.amazon_seller_api import AmazonListingManager, spapi_getlistings
from api.hepsiburada_api import Hb_API
from api.pazarama_api import PazaramaAPIClient
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
    handlers=[RichHandler(rich_tracebacks=True)])

logger = logging.getLogger(__name__)
hpApi = Hb_API()
n11Api = N11API()
amznApi = AmazonListingManager()
pazaramaApi = PazaramaAPIClient()


def filter_data(every_product, local, targets):
    """
    The function `filter_data` filters and retrieves
    stock data for different platforms based on
    specified targets.
    """

    data_content = {}
    codes = []
    platform_to_function = {
        "n11": n11Api.get_products,
        "hepsiburada": hpApi.get_listings,
        "amazon": spapi_getlistings,
        "pttavm": getpttavm_procuctskdata,
        "pazarama": pazaramaApi.get_products,
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

def filter_items(
    self,
    data: Dict[str, Any],
    source: str = "",
    use_source: bool = False,
    target: str = "",
    include_all: bool = False,
    find_mismatches: bool = False,
) -> List[Dict[str, Any]]:
    """
    Filters and compares item data across platforms, returning items with quantity changes or mismatches.

    Args:
        data (Dict[str, Any]): Input data with items from various platforms.
        source (str): Source platform for comparison.
        use_source (bool): Whether to prioritize source platform data.
        target (str): Specific target platform to compare against.
        include_all (bool): Include all items, even if unchanged.
        find_mismatches (bool): Return items that don't match across platforms.

    Returns:
        List[Dict[str, Any]]: List of items with quantity changes or mismatches.
    """

    # self.platforms.pop(source)

    # if find_mismatches:
    #     return find_non_matching_items(data, source, target)

    # matching_items = {}

    # for platform in self.platforms:
    #     platform_data = data.get(f"{platform}_data")
    #     if not platform_data:
    #         continue

    #     if use_source:
    #         compare_with_source(data[f"{source}_data"], platform_data, platform, matching_items, include_all)
    #     else:
    #         for item in platform_data:
    #             add_items_without_source(matching_items=matching_items, target_item=item, platform=platform, include_all=include_all)

    # return generate_changed_items(matching_items, use_source, include_all)

    if find_mismatches:

        use_source = True
        non_matching_items = find_non_matching_items(data, source, target)

    else:

        if source:
            del self.platforms[self.platforms.index(source)]

        for platform in self.platforms:
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

                                add_matching_item(
                                    matching_items, params, include_all)
                                break

                else:

                    for platform_item in data[f"{platform}_data"]:

                        add_items_without_source(
                            include_all, matching_items, platform, platform_item)

    if non_matching_items:

        matching_items = non_matching_items

    if matching_items:

        if not include_all:

            changed_values = generate_changed_items(matching_items, use_source)

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

def find_non_matching_items(data: Dict[str, Any], source: str, target: str) -> List[Dict[str, Any]]:
    """Finds items that don't match between source and target platforms."""
    non_matching_items = []
    target_data = {item["sku"]: item for item in data.get(f"{target}_data", [])}

    for source_item in data.get(f"{source}_data", []):
        if source_item["sku"] not in target_data:
            non_matching_items.append({"platform": target, "data": source_item["data"]})

    return non_matching_items

def generate_changed_items(matching_items: Dict[str, List[Dict[str, Any]]], use_source: bool) -> List[Dict[str, Any]]:
    """Generates a list of items with quantity changes or includes all items if specified."""
    changed_items = []

    for sku, items in matching_items.items():
        if len(items) > 1:
            reference_item = items[0] if use_source else min(items, key=lambda x: x["qty"])
            for item in items:
                if reference_item["qty"] != item["qty"]:
                    changed_items.append({
                        "id": item.get("id"),
                        "sku": sku,
                        "price": reference_item.get("price", 0),
                        "qty": str(reference_item["qty"]),
                        "platform": item["platform"]
                    })

    return changed_items

def add_items_without_source(include_all: bool, matching_items: Dict[str, List[Dict[str, Any]]], platform: str, target_item):
    """Helper function to add items without considering the source."""

    qty = (
        int(target_item.get("data", {}).get("quantity", 0))
        if "data" in target_item
        else target_item.get("qty", 0)
    )
    item_id = target_item.get("data", {}).get("id", target_item.get("id"))
    price = target_item.get("price", 0)

    if target_item["sku"] in matching_items:
        if include_all:
            matching_items[target_item["sku"]].append(
                {"platform": platform, "data": target_item["data"]}
            )
        else:
            matching_items[target_item["sku"]].append(
                {"platform": platform, "id": item_id, "price": price, "qty": qty}
            )
    else:
        if include_all:
            matching_items[target_item["sku"]] = [
                {"platform": platform, "data": target_item["data"]}
            ]
        else:
            matching_items[target_item["sku"]] = [
                {"platform": platform, "id": item_id, "price": price, "qty": qty}
            ]

def compare_with_source(source_data: List[Dict[str, Any]], platform_data: List[Dict[str, Any]], 
                        platform: str, matching_items: Dict[str, List[Dict[str, Any]]], include_all: bool):
    """Compares items between source and a target platform, updating matching_items."""
    for source_item in source_data:
        for target_item in platform_data:
            if source_item["sku"] == target_item["sku"]:
                add_matching_item(matching_items, source_item, target_item, platform, include_all)
                break

def add_matching_item(matching_items: Dict[str, List[Dict[str, Any]]], source_item: Dict[str, Any], 
                      target_item: Dict[str, Any], platform: str, include_all: bool):
    """Helper function to add matching items to the matching_items dictionary."""

    """Adds a source and target item pair to matching_items."""
    sku = source_item["sku"]
    if include_all:
        matching_items[sku] = [
            {"platform": source_item["platform"], "data": source_item["data"]},
            {"platform": platform, "data": target_item["data"]}            
        ]
    else:
        matching_items[sku] = [
            {
                "platform": platform,
                "id": target_item.get("id", None),
                "price": target_item.get("price", 0),
                "qty": target_item.get("qty", 0),
            }
        ]
    
class App:

    N11 = "n11"
    HEPSIBURADA = "hepsiburada"
    AMAZON = "amazon"
    PTTAVM = "pttavm"
    PAZARAMA = "pazarama"
    TRENDYOL = "trendyol"
    WORDPRESS = "wordpress"

    def __init__(self) -> None:

        self.platform_data_cache = {}     
        self.platforms = [
            self.N11,
            self.HEPSIBURADA,
            self.AMAZON,
            self.PTTAVM,
            self.PAZARAMA,
            self.TRENDYOL,
            self.WORDPRESS,
        ]   
        self.platform_to_update_function = {
            'n11': n11Api.update_products,
            'hepsiburada': hpApi.update_listing,
            'amazon': amznApi.update_listing,
            'pttavm': pttavm_updatedata,
            'pazarama': pazaramaApi.update_product,
            'trendyol': post_trendyol_data,
            'wordpress': update_wordpress_products,
        }

    def load_initial_data(self, load_all: bool, platforms: list[str] = None) -> dict:
        """
        Load initial data in the background and cache it.

        Args:
            load_all (bool): Whether to load all products or partial data.
            platforms (list[str], optional): List of platform names to load data from. 
                                             Loads all platforms if None.

        Returns:
            dict: Loaded data from the specified platforms or all platforms if none are specified.
        """

        # Mapping of platform names to corresponding data retrieval functions
        platform_functions = {
            "trendyol": lambda: get_trendyol_stock_data(load_all),
            "n11": lambda: n11Api.get_products(load_all),
            "hepsiburada": lambda: hpApi.get_listings(load_all),
            "pazarama": lambda: pazaramaApi.get_products(load_all),
            "wordpress": lambda: get_wordpress_products(load_all),
            "pttavm": lambda: getpttavm_procuctskdata(load_all),
            "amazon": lambda: spapi_getlistings(load_all),
        }

        data = {}

        # Load data for the specified platforms or all platforms if none specified
        selected_platforms = platforms or platform_functions.keys()

        for platform in selected_platforms:
            try:
                data[platform] = platform_functions[platform]()
            except KeyError:
                print(f"Platform '{platform}' not found.")
            except Exception as e:
                print(f"Error loading data for platform '{platform}': {e}")

        # Cache loaded data if all platforms are being loaded
        if platforms is None:
            self.platform_data_cache.update(data)

        return data
   
    def retrieve_stock_data(self,
                            include_all_products: bool = False,
                            use_local_data: bool = False,
                            source_platform: str = None,
                            target_platforms: list = None,
                            match_data: bool = False):
        """
        The `retrieve_stock_data()` function retrieves stock data
        from various platforms and returns specific data and
        lists related to the retrieved information.

        Parameters:
        - include_all_products (bool): Whether to retrieve all products or just specific ones.
        - use_local_data (bool): Whether to retrieve local data or not.
        - source_platform (str): The source platform from which to retrieve data.
        - target_platforms (list): List of target platforms to retrieve data from.
        - match_data (bool): Whether to match the data between source and targets.

        Returns:
        - dict: Data from target platforms, possibly including source platform data.
        - list: Combined list of all unique product codes from source and targets.
        """

        if target_platforms:

            targets = target_platforms if isinstance(target_platforms, list) else [target_platforms]

            try:
                # Retrieve data from source and target platforms
                source_data = self.retrieve_data(include_all_products, use_local_data, [source_platform])

                target_data = self.retrieve_data(include_all_products, use_local_data, targets) if target_platforms else ({}, [])

                # Include source platform data in target platforms if applicable
                target_data[source_platform] = source_data[source_platform]

                return target_data

            except Exception as e:
                logger.error(f"An error occurred while retrieving stock data: {e}")
                return {}

        self.load_initial_data(include_all_products)
        return self.platform_data_cache
    
    def get_date_range(date_option: str) -> Tuple[datetime, datetime]:
        """
        Retrieves the start and end dates based on the user's input or predefined options.

        Parameters:
        - date_option (str): Option to determine date range selection. 
                             "1" for the past month, "2" for user-defined dates.

        Returns:
        - Tuple[datetime, datetime]: A tuple containing start_date and end_date.
        """
        if date_option == "1":
            end_date = datetime.now()
            start_date = end_date - relativedelta(months=1)
        elif date_option == "2":
            try:
                start_date_input = Prompt.ask("Enter the start date (YYYY-MM-DD): ")
                end_date_input = Prompt.ask("Enter the end date (YYYY-MM-DD): ")
                start_date = datetime.strptime(start_date_input, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_input, "%Y-%m-%d")
                if start_date > end_date:
                    raise ValueError("Start date cannot be after end date.")
            except ValueError as e:
                print(f"Invalid date format or range: {e}")
                return None, None
        else:
            print("Invalid option selected.")
            return None, None

        return start_date, end_date

    def retrieve_data(self, include_all_products: bool, use_local_data: bool, platforms: list) -> Tuple[dict, list]:
        """
        Retrieves and filters stock data from specified platforms.
    
        Parameters:
        - include_all_products (bool): Flag to determine if all products should be included.
        - use_local_data (bool): Flag to determine if local data should be used.
        - platforms (list): List of platform names from which to retrieve data.
    
        Returns:
        - dict: A dictionary containing data from the specified platforms.
        - list: A list of SKUs extracted from the retrieved data.
        """
        # Initialize the result variables
        filtered_data = {}
    
        # Load initial data based on the include_all_products flag
        self.load_initial_data(include_all_products)
        
        # Access cached data
        cached_data = self.platform_data_cache
    
        # Retrieve and process data for each specified platform
        for platform in platforms:
            platform_key = platform.lower()
            platform_data = cached_data.get(platform_key)
            
            if platform_data:
                filtered_data[platform_key] = platform_data
    
        return filtered_data

    def filter_data_by_date_range(
        data: Dict[str, dict],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, dict]:
        """
        Filters the given data based on a specified date range.
    
        Parameters:
        - data (Dict[str, dict]): Dictionary where keys are identifiers (e.g., SKUs) and values are dictionaries containing post data.
        - start_date (Optional[datetime]): The earliest date to include in the filter. If None, no start date filter is applied.
        - end_date (Optional[datetime]): The latest date to include in the filter. If None, no end date filter is applied.
    
        Returns:
        - Dict[str, dict]: A dictionary containing only the entries within the specified date range.
        """
        
        if not start_date and not end_date:
            return data
    
        filtered_data = {}
        for identifier, entry in data.items():
            last_update_date_str = entry.get("lastUpdateDate")
            
            if last_update_date_str:
                try:
                    last_update_date = datetime.strptime(last_update_date_str, "%Y-%m-%d")
                except ValueError:
                    continue  # Skip entries with invalid date formats
                
                if start_date and last_update_date < start_date:
                    continue
                if end_date and last_update_date > end_date:
                    continue
                
                filtered_data[identifier] = entry
    
        return filtered_data

    def filter_items(
        self,
        data: Dict[str, Any],
        source: str = "",
        use_source: bool = False,
        target: str = "",
        include_all: bool = False,
        find_mismatches: bool = False,
        ) -> List[Dict[str, Any]]:
        """
        Filters and compares item data across platforms, returning items with quantity changes or mismatches.

        Args:
            data (Dict[str, Any]): Input data with items from various platforms.
            source (str): Source platform for comparison.
            use_source (bool): Whether to prioritize source platform data.
            target (str): Specific target platform to compare against.
            include_all (bool): Include all items, even if unchanged.
            find_mismatches (bool): Return items that don't match across platforms.

        Returns:
            List[Dict[str, Any]]: List of items with quantity changes or mismatches.
        """
        if source:
            del self.platforms[self.platforms.index(source)]

        if find_mismatches:
            return find_non_matching_items(data, source, target)

        matching_items = {}

        for platform in self.platforms:
            platform_data = data.get(platform)
            if not platform_data:
                continue

            if use_source:
                compare_with_source(data[source], platform_data, platform, matching_items, include_all)
            else:
                for item in platform_data:
                    add_items_without_source(matching_items=matching_items, target_item=item, platform=platform, include_all=include_all)

        return generate_changed_items(matching_items, use_source)
    
    def process_products_by_sku(
                            self,
                            sku_updates: List[Dict[str, str]],
                            update_type: Optional[str] = None
                        ) -> Dict[str, List[Dict[str, str]]]:
        """
         Updates product data based on provided SKU and update options.

         Parameters:
         - sku_updates (List[Dict[str, str]]): List of dictionaries where each dictionary maps SKU to the new value for update.
         - update_type (Optional[str]): Type of update to perform. Options are 'quantity' to update stock quantity, 'price' to update price, or None for no update.

         Returns:
         - Dict[str, List[Dict[str, str]]]: A dictionary where keys are platform names and values are lists of updated product data dictionaries.
         """

        self.load_initial_data(False)
        data_content = self.platform_data_cache
        product_data = []

        for platform, products in data_content.items():
            for sku_update in sku_updates:  
                
                # Check if the product SKU needs to be updated             
                for product in products:
                    product_sku = product.get("sku")

                    for sku, new_value in sku_update.items():
                        if product_sku == sku:

                            if update_type == 'qty':
                                product["qty"] = int(new_value)
                                product["platform"] = platform
                                product_data.append(product)
                            elif update_type == 'price':
                                product["price"] = float(new_value)
                                product["platform"] = platform
                                product_data.append(product)
                            elif update_type == 'info':
                                product["platform"] = platform
                                product_data.append(product)
                            break
                    
                    

        return product_data

    def process_update_data(self, source=None, use_source=False, targets=None, options=None):
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
            data_lists = self.retrieve_stock_data(include_all_products=all_data, source_platform=source, target_platforms=targets)

            # Return early if no data is retrieved
            if not data_lists:
                logger.info("No data retrieved. Exiting.")
                return {}

            # Process the retrieved data to filter relevant platform updates
            platform_updates = self.filter_items(
                data=data_lists,
                source=source,
                use_source=use_source,
                target=targets,
                include_all=all_data,
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

    def execute_platform_updates(self, platform, func, post_data, options, source):

        try:
            if isinstance(post_data, list):
                for post in post_data:
                    if platform == post['platform']:

                        func(post)
            else:
                if platform == post_data['platform']:
                    func(post_data)

            # logger.info(f"Successfully updated {len(post_data)} products on {platform.name}.")
        except Exception as e:
            logger.error(f"Failed to update products on {platform}. Error: {e}")

    def execute_updates(self, source=None, use_source=False, targets=None, options=None, user_input=None):
        """
        The function `execute_updates` processes update data
        for different platforms and calls corresponding
        update functions based on the platform.
        """

        
        date_input = None
        start_date = None
        end_date = None
        filtered_post_data = None

        logger.info("Starting updates...")

        if user_input:

            post_data = self.process_products_by_sku(user_input, update_type=options)
        
        else:

            post_data = self.process_update_data(source=source, use_source=use_source, targets=targets, options=options)

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

                start_date, end_date = self.get_date_range(date_input)
                filtered_post_data = self.filter_post_data_by_date(post_data, start_date, end_date)

            else:
                logger.error("Invalid choice. Please select a valid option.")

            logger.info("Update in progress...")

            if filtered_post_data:

                post_data = filtered_post_data

            

            # Process updates
            for platform, func in self.platform_to_update_function.items():

                if isinstance(targets, list):
                    if platform in targets:
                        self.execute_platform_updates(platform, func, post_data, options, source)
                elif platform == targets:
                    self.execute_platform_updates(platform, func, post_data, options, source)
                elif not source and not targets:
                    self.execute_platform_updates(platform, func, post_data, options, source)

            logger.info("Updates completed.")

            break
            
    def create_products(self, SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS, LOCAL_DATA=False):

        platform_to_function = {
        "n11": n11Api.add_products,
        "hepsiburada": hpApi.create_listing,
        "amazon": amznApi.add_listings,
        "pttavm": pttavm_updatedata,
        "pazarama": pazaramaApi.create_products,
        "trendyol": post_trendyol_data,
        "wordpress": create_wordpress_products,
    }

        data_lists, _ = self.retrieve_stock_data(
        include_all_products=True,
        use_local_data=LOCAL_DATA,
        source_platform=SOURCE_PLATFORM,
        target_platforms=[TARGET_PLATFORM],
        match_data=True,
    )

        filtered_data = self.filter_items(
        data=data_lists,
        include_all=True,
        find_mismatches=True,
        source=SOURCE_PLATFORM,
        target=TARGET_PLATFORM,
    )

        if filtered_data:

            platform_to_function[TARGET_PLATFORM](data=filtered_data)

        logger.info("Done")

    def process(self, data_dict: dict = None):

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

                        App.execute_updates(self,
                            source=data_dict["update"]["source"],
                            targets=data_dict["update"]["target"],
                            use_source=True if data_dict["update"]["options"] else False,
                            options=data_dict["update"]["options"],
                            user_input=data_dict["update"]["user_input"],
                        )
                        break

                    App.create_products(self,
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

    app_instance = App()
    input_app = ProductManagerApp()
    results = input_app.run()
    app_instance.process(results)
