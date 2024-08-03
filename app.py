""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

import asyncio
import logging
import re
from rich.logging import RichHandler
from rich.prompt import Prompt
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Footer, Label, RadioSet, RadioButton, Input, Log
from api.amazon_seller_api import (
    spapi_add_listing,
    spapi_getlistings,
    spapi_update_listing,
)
from api.hepsiburada_api import HpApi
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getpttavm_procuctskdata, pttavm_updatedata
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import create_n11_data, get_n11_stock_data, post_n11_data
from api.wordpress_api import (
    create_wordpress_products,
    get_wordpress_products,
    update_wordpress_products,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)])
logger = logging.getLogger(__name__)

hpapi = HpApi()


class ProductManagerApp(App[None]):

    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:

        self.source = ''
        self.target = ''
        self.target_options = ''
        self.hide_containers([
            "create_container",
            "copy_container",
            "update_container",
            "specific_update_op_container",
            "specific_partial_op_choice_container",
            "storage_container",
            "specific_partial_op_source_platform_container",
            "specific_partial_op_target_platform_container"
        ])

    def compose(self) -> ComposeResult:

        with VerticalScroll():

            with Horizontal(id="operation_container"):

                yield Label("What operation would you like to perform?")
                with RadioSet(id="operation_choice"):
                    yield RadioButton("Create new product", id="create")
                    yield RadioButton("Update existing product", id="update")

            with Horizontal(id="create_container"):

                yield Label("How would you like to create a new product?")
                with RadioSet(id="create_choice"):
                    yield RadioButton("Copy from another platform", id="auto_copy")
                    yield RadioButton("Enter details manually", id="manual_copy")

            with Horizontal(id="copy_container"):

                yield Label("Please select the source platform to copy from: Ex. Trendyol")
                with RadioSet(id="source_platform"):
                    for button in self.platform_radio_set():
                        yield button

                yield Label("Please enter the target platform to copy to: Ex. PTTAVM")
                with RadioSet(id="target_platform"):
                    for button in self.platform_radio_set():
                        yield button

            with Horizontal(id="storage_container"):

                yield Label("Which storage do you want to use?")
                with RadioSet(id="storage_choice"):
                    yield RadioButton("Online storage", id="online_storage")
                    yield RadioButton("Offline storage", id="offline_storage")

            with Horizontal(id="update_container"):

                yield Label("Do you want to update specific platforms?")
                with RadioSet(id="update_choice"):
                    yield RadioButton("Yes", id="yes_specific_update")
                    yield RadioButton("No", id="no_specific_update")

            with Horizontal(id="specific_update_op_container"):

                yield Label("Available operations:")
                with RadioSet(id="specific_update_op_choice"):
                    yield RadioButton("Full update", id="specific_full_update")
                    yield RadioButton("Partial update", id="specific_partial_update")

            with Horizontal(id="specific_partial_op_source_platform_container"):

                yield Label("Please select the source platform to copy from: Ex. Trendyol")
                with RadioSet(id="specific_partial_op_source_platform"):
                    for button in self.platform_radio_set():
                        yield button

            with Horizontal(id="specific_partial_op_target_platform_container"):

                yield Label("Please select the target platform: Ex. Amazon")
                with RadioSet(id="specific_partial_op_target_platform"):
                    for button in self.platform_radio_set():
                        yield button

            with Horizontal(id="specific_partial_op_choice_container"):

                yield Label("Available partial operations:")
                with RadioSet(id="specific_partial_op_choice"):
                    yield RadioButton("Quantity", id="quantity")
                    yield RadioButton("Price", id="price")
                    yield RadioButton("Information (Images, Properties, descriptions)", id="info")

        yield Log()

    def platform_radio_set(self) -> list:
        return [
            RadioButton("Trendyol", id='trendyol'),
            RadioButton("Amazon", id='amazon'),
            RadioButton("HepsiBurada", id='hepsiburada'),
            RadioButton("N11", id='n11'),
            RadioButton("Pazarama", id='pazarama'),
            RadioButton("PTTAVM", id='pttavm'),
            RadioButton("Wordpress", id='wordpress')
        ]

    def hide_containers(self, container_ids: list) -> None:
        for container_id in container_ids:
            self.query_one(f"#{container_id}").display = False

    def show_container(self, container_id: str) -> None:
        self.query_one(f"#{container_id}").display = True

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:

        if event.radio_set.id == "operation_choice":
            self.hide_containers(["operation_container"])
            if event.pressed.id == "create":
                self.show_container("create_container")
            if event.pressed.id == "update":
                self.show_container("update_container")

        if event.radio_set.id == "create_choice":
            self.hide_containers(["create_container"])
            if event.pressed.id == "auto_copy":
                self.show_container("copy_container")
            if event.pressed.id == "manual_copy":
                self.query_one(Log).write_line(
                    "Enter details manually selected.")

        if event.radio_set.id == "source_platform":

            self.source = event.pressed.id

        if event.radio_set.id == "target_platform":

            self.target = event.pressed.id
            self.hide_containers(["copy_container"])
            self.show_container("storage_container")

        if event.radio_set.id == "storage_choice":

            if event.pressed.id == "online_storage":

                asyncio.create_task(create_products(
                    self.source, self.target, "copy", False))
                app.exit()

            asyncio.create_task(create_products(
                self.source, self.target, "", True))
            app.exit()

        if event.radio_set.id == "update_choice":

            self.hide_containers(["update_container"])
            if event.pressed.id == "yes_specific_update":

                self.show_container("specific_update_op_container")

            if event.pressed.id == "no_specific_update":

                self.query_one(Log).write_line(
                    "No specific platform update selected.")
                asyncio.create_task(execute_updates())
                app.exit()

        if event.radio_set.id == "specific_update_op_choice":

            if event.pressed.id == "specific_full_update":

                self.query_one(Log).write_line("Full update selected.")
                asyncio.create_task(execute_updates(
                    self.source, self.target, "full"))
                app.exit()

            if event.pressed.id == "specific_partial_update":

                self.hide_containers(["specific_update_op_container"])
                self.show_container(
                    "specific_partial_op_source_platform_container")

        if event.radio_set.id == "specific_partial_op_source_platform":

            self.source = event.pressed.id
            self.hide_containers(
                ["specific_partial_op_source_platform_container"])
            self.show_container(
                "specific_partial_op_target_platform_container")

        if event.radio_set.id == "specific_partial_op_target_platform":

            self.target = event.pressed.id
            self.hide_containers(
                ["specific_partial_op_target_platform_container"])
            self.show_container("specific_partial_op_choice_container")

        if event.radio_set.id == "specific_partial_op_choice":
            if event.pressed.id == "quantity":

                self.query_one(Log).write_line(
                    "Partial update for quantity selected.")
                asyncio.create_task(execute_updates(
                    self.source, self.target, "qty"))
                app.exit()

            if event.pressed.id == "price":

                self.query_one(Log).write_line(
                    "Partial update for price selected.")
                asyncio.create_task(execute_updates(
                    self.source, self.target, "price"))
                app.exit()

            if event.pressed.id == "info":

                self.query_one(Log).write_line(
                    "Partial update for information selected.")
                asyncio.create_task(execute_updates(
                    self.source, self.target, "info"))
                app.exit()


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
        "n11_data": get_n11_stock_data(every_product),
        "amazon_data": spapi_getlistings(every_product),
        "hepsiburada_data": hpapi.get_listings(every_product),
        "pazarama_data": getPazarama_productsList(every_product),
        "wordpress_data": get_wordpress_products(every_product),
        "pttavm_data": getpttavm_procuctskdata(every_product),
    }

    if every_product:

        pass

    elif match:

        all_codes = {source: source_codes, targets: target_codes}

    else:

        all_codes = list(
            set(
                [item["sku"] for item in data_content["n11_data"]]
                + [item["sku"] for item in data_content["trendyol_data"]]
                + [item["sku"] for item in data_content["amazon_data"]]
                + [item["sku"] for item in data_content["hepsiburada_data"]]
                + [item["sku"] for item in data_content["pazarama_data"]]
                + [item["sku"] for item in data_content["wordpress_data"]]
                + [item["sku"] for item in data_content["pttavm_data"]]
            )
        )

    return data_content, all_codes


def filter_data(every_product, local, targets):
    """
    The function `filter_data` filters and retrieves
    stock data for different platforms based on
    specified targets.
    """

    data_content = {}
    codes = []
    platform_to_function = {
        "n11": get_n11_stock_data,
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


def process_update_data(source=None, targets=None, options=None):
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
    platform_updates = filter_data_list(
        data=data_lists, source=source, target=targets, every_product=all_data
    )

    logger.info(f"""Product updates count is {len(platform_updates)}""")

    return platform_updates


def filter_data_list(data, source, target, every_product: bool = False, no_match=False):
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

    matching_ids = {}
    non_matching_ids = {}
    # Initialize a set to store all SKUs from the source platform

    if no_match:

        source = True

    for platform in platforms:

        if platform != source:

            if f"{platform}_data" in data:

                for source_item in data[f"{platform}_data"]:

                    if source:

                        if no_match:

                            target_skus = list(
                                item["sku"] for item in data[f"{target}_data"]
                            )
                            platform = target

                        for target_item in data[f"{platform}_data"]:

                            if target_item["sku"] == source_item["sku"]:
                                if no_match:

                                    break

                                elif target_item["sku"] in matching_ids:

                                    if every_product:

                                        matching_ids[target_item["sku"]].append(
                                            {
                                                "platform": platform,
                                                "data": source_item["data"],
                                            }
                                        )
                                    else:

                                        matching_ids[target_item["sku"]].append(
                                            {
                                                "platform": platform,
                                                "id": source_item["id"],
                                                "price": source_item.get("price", 0),
                                                "qty": source_item["qty"],
                                            }
                                        )

                                else:

                                    if every_product:

                                        matching_ids[target_item["sku"]] = [
                                            {
                                                "platform": platform,
                                                "data": source_item["data"],
                                            }
                                        ]

                                    else:

                                        matching_ids[target_item["sku"]] = [
                                            {
                                                "platform": platform,
                                                "id": source_item["id"],
                                                "price": source_item.get("price", 0),
                                                "qty": source_item["qty"],
                                            }
                                        ]

                                break

                            elif no_match and source_item["sku"] not in target_skus:
                                if source_item["sku"] not in non_matching_ids:

                                    non_matching_ids[source_item["sku"]] = [
                                        {
                                            "platform": platform,
                                            "data": source_item["data"],
                                        }
                                    ]

                    else:

                        if source_item["sku"] in matching_ids:

                            if every_product:

                                matching_ids[source_item["sku"]].append(
                                    {"platform": platform,
                                        "data": source_item["data"]}
                                )
                            else:

                                matching_ids[source_item["sku"]].append(
                                    {
                                        "platform": platform,
                                        "id": source_item["id"],
                                        "price": source_item.get("price", 0),
                                        "qty": source_item["qty"],
                                    }
                                )

                        else:

                            if every_product:

                                matching_ids[source_item["sku"]] = [
                                    {"platform": platform,
                                        "data": source_item["data"]}
                                ]
                            else:

                                matching_ids[source_item["sku"]] = [
                                    {
                                        "platform": platform,
                                        "id": source_item["id"],
                                        "price": source_item.get("price", 0),
                                        "qty": source_item["qty"],
                                    }
                                ]

    if non_matching_ids:

        matching_ids = non_matching_ids

    if matching_ids:

        if not every_product:

            for item_key, item_val in matching_ids.items():

                products = item_val

                if len(products) > 1:

                    if source:

                        source_val = item_val[0]

                    else:

                        filtered_products = [
                            product
                            for product in products
                            if product["qty"] is not None
                        ]
                        source_val = min(filtered_products,
                                         key=lambda x: x["qty"])

                        if source_val["qty"] == 0:

                            pass

                    for product in products:

                        if product == source_val:

                            continue

                        if item_key == "EVA1":

                            pass

                        if source_val["qty"] == product["qty"]:

                            if source_val["price"] == product["price"]:

                                continue

                            continue

                        changed_values.append(
                            {
                                "id": product["id"],
                                "sku": item_key,
                                "price": source_val.get("price", 0),
                                "qty": str(source_val["qty"]),
                                "platform": product["platform"],
                            }
                        )
                else:

                    continue

        else:

            for item_key, item_val in matching_ids.items():

                products = item_val

                if len(products) > 1:

                    changed_values.append(products[0]["data"])

                else:

                    changed_values = matching_ids

                    break

    return changed_values


async def execute_updates(source=None, targets=None, options=None):
    """
    The function `execute_updates` processes update data
    for different platforms and calls corresponding
    update functions based on the platform.
    """

    platform_to_function = {
        "n11": post_n11_data,
        "hepsiburada": hpapi.update_listing,
        "amazon": spapi_update_listing,
        "pttavm": pttavm_updatedata,
        "pazarama": pazarama_updateRequest,
        "trendyol": post_trendyol_data,
        "wordpress": update_wordpress_products,
    }

    post_data = process_update_data(source, targets, options)

    if post_data:

        count = 1

        if not options:

            for update in post_data:

                logger.info(
                    f"""{count}. Product with sku {update['sku']} from {
                        update['platform']} has a new stock! || New stock: {update['qty']}"""
                )

                count += 1

        while True:

            user_input = Prompt.ask(
                "Do you want to continue? (y/n): ", choices=["y", "n"])

            if user_input.lower() == "n":

                logger.info("Exiting the program.")

                break

            elif user_input.lower() == "y":

                logger.info("Update in progress...")

                if options:

                    for platform, func in platform_to_function.items():

                        for target_platform in targets:

                            if platform == target_platform:

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


async def create_products(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS, LOCAL_DATA=False):

    platform_to_function = {
        "n11": create_n11_data,
        "hepsiburada": hpapi.add_listing,
        "amazon": spapi_add_listing,
        "pttavm": pttavm_updatedata,
        "pazarama": pazarama_updateRequest,
        "trendyol": post_trendyol_data,
        "wordpress": create_wordpress_products,
    }

    data_lists, all_codes = get_data(
        every_product=True,
        local=LOCAL_DATA,
        source=SOURCE_PLATFORM,
        targets=[TARGET_PLATFORM],
        match=True,
    )

    filtered_data = filter_data_list(
        data=data_lists,
        all_codes=all_codes,
        every_product=True,
        no_match=True,
        source=None,
    )

    if filtered_data:

        platform_to_function[TARGET_PLATFORM](filtered_data)

    logger.info("Done")


if __name__ == "__main__":
    app = ProductManagerApp()
    app.run()
