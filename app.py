""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

import re
from rich import print as printr
from api.amazon_seller_api import spapi_getlistings, spapi_update_listing
from api.hepsiburada_api import hbapi_stock_data, hbapi_update_listing
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getPTTAVM_procuctskData, pttavm_updateData
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import get_n11_stock_data, post_n11_data



def get_data(every_product: bool = False, source: str = None, targets: list = None):
    """
    The `get_data()` function retrieves stock data from various platforms and returns specific data and
    lists related to the retrieved information.

    :param every_product: The `every_product` parameter in the `get_data()` function is a boolean
    parameter that specifies whether to retrieve data for every product or not. If set to `True`, data
    for every product will be retrieved. If set to `False`, data for specific products will be retrieved
    based on the other, defaults to False
    :type every_product: bool (optional)
    :param source: The `source` parameter in the `get_data()` function is used to specify the source
    platform from which you want to retrieve data. It can be a string indicating the source platform
    such as "N11" or "Trendyol". If you provide a value for the `source` parameter
    :type source: str
    :param targets: The `targets` parameter in the `get_data()` function is a list that specifies the
    platforms from which you want to retrieve data. You can pass a list of platform names as targets to
    filter the data accordingly
    :type targets: list
    :return: The function `get_data()` returns either `target_platforms` and `all_codes` if `targets`
    are provided, or `data_content` and `all_codes` if `every_product` is False.
    """

    # Retrieve stock data from APIs
    if targets:

        source_platform, source_codes = filter_data(every_product, [source])
        target_platforms, target_codes = filter_data(every_product, targets)
        all_codes = list(set(target_codes +
                             source_codes))
        target_platforms[f"{source}_data"] = source_platform[f"{source}_data"]

        return target_platforms, all_codes

    trendyol_data = get_trendyol_stock_data(every_product)

    n11_data = get_n11_stock_data(every_product)

    amazon_data = spapi_getlistings(every_product)

    hepsiburada_data = hbapi_stock_data(every_product)

    pazarama_data = getPazarama_productsList(every_product)

    pttavm_data = getPTTAVM_procuctskData(every_product)

    data_content = {"trendyol_data": trendyol_data,
                    "n11_data": n11_data,
                    "amazon_data": amazon_data,
                    "hepsiburada_data": hepsiburada_data,
                    "pazarama_data": pazarama_data,
                    "pttavm_data": pttavm_data}

    if every_product:

        pass

    else:

        all_codes = list(set([item['sku'] for item in n11_data] +
                             [item['sku'] for item in trendyol_data] +
                             [item['sku'] for item in amazon_data] +
                             [item['sku'] for item in hepsiburada_data] +
                             [item['sku'] for item in pazarama_data] +
                             [item['sku'] for item in pttavm_data]))

    return data_content, all_codes


def filter_data(every_product, targets):
    """
    The function `filter_data` filters and retrieves stock data for different platforms based on
    specified targets.

    :param every_product: It seems like the description of the `every_product` parameter is missing.
    Could you please provide more details or an example of what the `every_product` parameter contains
    or represents? This will help in understanding the context better and providing a more accurate
    response
    :param targets: It seems like the `targets` parameter is a list of platform names such as 'n11',
    'hepsiburada', 'amazon', 'pttavm', 'pazarama', 'trendyol'. These platform names are used to filter
    and retrieve specific data related to
    :return: The function `filter_data` is returning the `target_platform` variable, which is being
    updated based on the conditions inside the for loop for each target platform specified in the
    `targets` list. The function is filtering and retrieving stock data for different platforms such as
    n11, hepsiburada, amazon, pttavm, pazarama, and trendyol, and the final `target
    """

    data_content = {}
    codes = []

    for name in targets:
        if re.search('n11', name):
            data_content[f"{name}_data"] = get_n11_stock_data(every_product)

        elif re.search('hepsiburada', name):
            data_content[f"{name}_data"] = hbapi_stock_data(every_product)

        elif re.search('amazon', name):
            data_content[f"{name}_data"] = spapi_getlistings(every_product)

        elif re.search('pttavm', name):
            data_content[f"{name}_data"] = getPTTAVM_procuctskData(
                every_product)

        elif re.search('pazarama', name):
            data_content[f"{name}_data"] = getPazarama_productsList(
                every_product)

        elif re.search('trendyol', name):
            data_content[f"{name}_data"] = get_trendyol_stock_data(
                every_product)

    for _, item in data_content.items():
        for item_data in item:
            codes.append(item_data['sku'])

    return data_content, codes


def process_update_data(source=None, targets=None):
    """
    The function `process_update_data` retrieves data, processes 
    stock updates from different platforms, and returns the 
    platform updates.
    :return: The function `process_update_data()` is returning the 
    list `platform_updates`.
    """

    #  This allows us to access and use these variables
    data_lists, all_codes = get_data(source=source, targets=targets)

    # Initializing empty lists. These lists will be used
    # to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates, matching_values = get_platform_updates(
        data_lists, all_codes, source)

    printr(f"""\nLength of the two lists:- \nPlatform updates is {
          len(platform_updates)}\nMatching codes is {len(matching_values)}\n""")

    return platform_updates


def get_platform_updates(data, all_codes, source):
    """
    The function `get_platform_updates` compares quantity values
    for items across different platforms and returns a list of
    changed values and matching values.

    :param data: The function `get_platform_updates` takes two
    parameters: `data` and `all_codes`. The `data` parameter
    seems to be a dictionary containing platform data for different
    platforms like Trendyol, N11, Amazon, HepsiBurada, Pazarama, and PTTAVM
    :param all_codes: All_codes is a list of SKU codes that you want to check
    for updates on different platforms. The function `get_platform_updates`
    takes this list along with some data containing platform information
    and compares the quantities of products with the same SKU on different
    platforms. It then identifies any discrepancies in quantities and returns a
    :return: The function `get_platform_updates` returns two lists: `changed_values` and
    `matching_values`.
    """

    changed_values = []

    platforms = ['trendyol',
                 'n11',
                 'amazon',
                 'hepsiburada',
                 'pazarama',
                 'pttavm']

    matching_values = []

    matching_ids = {}

    item_id = 0

    for code in all_codes:

        for platform in platforms:

            if f'{platform}_data' in data:

                for item in data[f'{platform}_data']:

                    if item['sku'] == code:

                        quantity = item['qty']

                        item_id = item['id']

                        if code in matching_ids:

                            matching_ids[code].append(
                                {'platform': platform,
                                 'id': item_id,
                                 'price': item.get('price', None),
                                 'qty': quantity})

                        else:

                            matching_ids[code] = [
                                {'platform': platform,
                                 'id': item_id,
                                 'price': item.get('price', None),
                                 'qty': quantity}]

                        break

    if matching_ids:

        for item_key, item_val in matching_ids.items():

            products = item_val

            if len(products) > 1:

                if source:

                    source_val = item_val[0]

                else:

                    source_val = min(products, key=lambda x: x['qty'])

                for product in products:

                    if source_val['qty'] == product['qty'] and source_val['price'] == product['price']:

                        continue

                    matching_values.append(
                        {'sku': product['id'],
                         'qty1': product['qty'],
                         'qty2': source_val['qty']})

                    changed_values.append(
                        {'id': product['id'],
                         'sku': item_key,
                         'price': source_val.get('price', None),
                         'qty': str(source_val['qty']),
                         'platform': product['platform']})
            else:

                continue

    return changed_values, matching_values


def execute_updates(source=None, targets=None):
    """
    The function `execute_updates` processes update data
    for different platforms and calls corresponding
    update functions based on the platform.
    """

    post_data = process_update_data(source, targets)

    if post_data:

        for post in post_data:

            if post['platform'] != source:

                if post['platform'] == 'trendyol':

                    post_trendyol_data(post)

                elif post['platform'] == 'n11':

                    post_n11_data(post)

                elif post['platform'] == 'amazon':

                    spapi_update_listing(post)

                elif post['platform'] == 'hepsiburada':

                    hbapi_update_listing(post)

                elif post['platform'] == 'pazarama':

                    pazarama_updateRequest(post)

                elif post['platform'] == 'pttavm':

                    pttavm_updateData(post)


printr('Do you want to update specific platforms ?\n')
printr('1. Yes\n2. No\n')
options = input('Choose an option from above: ')

if options == '1':

    SOURCE_PLATFORM = input(
        'Please enter the source website platform: Ex. Trendyol\n')
    TARGET_PLATFORM = input(
        '\nPlease enter the target website platform: Ex. Magento\n').split(' ')
else:

    SOURCE_PLATFORM = None
    TARGET_PLATFORM = None

execute_updates(SOURCE_PLATFORM, TARGET_PLATFORM)

print('All updates has finished. The program will exit now!')
