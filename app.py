""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

import re
from rich import print as printr
from api.amazon_seller_api import spapi_getlistings, spapi_update_listing
from api.hepsiburada_api import hbapi_stock_data, hbapi_update_listing, hpapi_add_listing
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getpttavm_procuctskdata, pttavm_updatedata
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import get_n11_stock_data, post_n11_data
from api.wordpress_api import get_wordpress_products, update_wordpress_products


def get_data(every_product: bool = False, source: str = None, targets: list = None):
    """
    The `get_data()` function retrieves stock data 
    from various platforms and returns specific data and
    lists related to the retrieved information.
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

    wordpress_data = get_wordpress_products(every_product)

    pttavm_data = getpttavm_procuctskdata(every_product)

    data_content = {"trendyol_data": trendyol_data,
                    "n11_data": n11_data,
                    "amazon_data": amazon_data,
                    "hepsiburada_data": hepsiburada_data,
                    "pazarama_data": pazarama_data,
                    "wordpress_data": wordpress_data,
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
    The function `filter_data` filters and retrieves 
    stock data for different platforms based on
    specified targets.
    """

    data_content = {}
    codes = []
    platform_to_function = {
        'n11': get_n11_stock_data,
        'hepsiburada': hbapi_stock_data,
        'amazon': spapi_getlistings,
        'pttavm': getpttavm_procuctskdata,
        'pazarama': getPazarama_productsList,
        'wordpress': get_wordpress_products,
        'trendyol': get_trendyol_stock_data
    }

    for name in targets:

        for platform, function in platform_to_function.items():

            if re.search(platform, name):
                data_content[f"{name}_data"] = function(every_product)

    for _, item in data_content.items():

        for item_data in item:

            codes.append(item_data['sku'])

    return data_content, codes


def process_update_data(source=None, targets=None, options=None):
    """
    The function `process_update_data` retrieves data, processes 
    stock updates from different platforms, and returns the 
    platform updates.
    :return: The function `process_update_data()` is returning the 
    list `platform_updates`.
    """

    all = False

    if options:

        if options == 'full':

            data_lists, all_codes = get_data(
                every_product=True, source=source, targets=targets)

            all = True

    else:

        data_lists, all_codes = get_data(source=source, targets=targets)

    # Initializing empty lists. These lists will be used
    # to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates = filter_data_list(
        data_lists, all_codes, source, every_product=all)

    printr(f"""\nLength of the two lists:- \nPlatform updates is {
        len(platform_updates)}\n""")

    return platform_updates


def filter_data_list(data, all_codes, source, every_product: bool = False, match: bool = True):
    """
    The function `filter_data_list` compares quantity values
    for items across different platforms and returns a list of
    changed values and matching values.
    """

    changed_values = []

    platforms = ['trendyol',
                 'n11',
                 'amazon',
                 'hepsiburada',
                 'pazarama',
                 'wordpress',
                 'pttavm']

    matching_ids = {}
    non_matching_ids = {}

    item_id = 0

    for code in all_codes:

        for platform in platforms:

            if f'{platform}_data' in data:

                for item in data[f'{platform}_data']:

                    if item['sku'] == code:

                        if code in matching_ids:

                            if every_product:

                                matching_ids[code].append({'platform': platform,
                                                           'data': item['data']})
                            else:

                                matching_ids[code].append(
                                    {'platform': platform,
                                     'id': item['id'],
                                     'price': item.get('price', 0),
                                     'qty': item['qty']})

                        else:

                            if every_product:

                                matching_ids[code] = [{'platform': platform,
                                                      'data': item['data']}]

                            else:

                                matching_ids[code] = [
                                    {'platform': platform,
                                     'id': item['id'],
                                     'price': item.get('price', 0),
                                     'qty': item['qty']}]

                        break

    if matching_ids:

        if not every_product:

            for item_key, item_val in matching_ids.items():

                products = item_val

                if len(products) > 1:

                    if source:

                        source_val = item_val[0]

                    else:

                        source_val = min(products, key=lambda x: x['qty'])

                    for product in products:

                        if product == source_val:

                            continue

                        if source_val['qty'] == product['qty']:

                            if source_val['price'] == product['price']:

                                continue

                            continue

                        # product_price = product['price'] + product['price'] * 0.1

                        # if product_price - source_val['price'] <= 1:

                        #     continue

                        changed_values.append(
                            {'id': product['id'],
                             'sku': item_key,
                             'price': source_val.get('price', 0),
                             'qty': str(source_val['qty']),
                             'platform': product['platform']})
                else:

                    continue

        else:

            if matching_ids:

                for item_key, item_val in matching_ids.items():

                    products = item_val

                    if len(products) > 1:

                        if products[0]['platform'] == TARGET_PLATFORM:

                            continue

                        changed_values.append(products[0]['data'])
            
            else:

                changed_values = matching_ids

    return changed_values


def execute_updates(source=None, targets=None, options=None):
    """
    The function `execute_updates` processes update data
    for different platforms and calls corresponding
    update functions based on the platform.
    """

    platform_to_function = {
        'n11': post_n11_data,
        'hepsiburada': hbapi_update_listing,
        'amazon': spapi_update_listing,
        'pttavm': pttavm_updatedata,
        'pazarama': pazarama_updateRequest,
        'trendyol': post_trendyol_data,
        'wordpress': update_wordpress_products
    }

    post_data = process_update_data(source, targets, options)

    if post_data:

        count = 1

        for update in post_data:

            printr(f"""{count}. Product with sku {update['sku']} from {
                   update['platform']} has a new stock! || New stock: {update['qty']}""")

            count += 1

        while True:

            user_input = input("\nDo you want to continue? (y/n): ")

            if user_input.lower() == 'n':

                printr("\nExiting the program.")

                break

            elif user_input.lower() == 'y':

                printr("\nUpdate in progress...\n")

                for post in post_data:

                    for platform, func in platform_to_function.items():

                        if platform == post['platform']:

                            func(post)

                break

            else:
                printr("Invalid input. Please enter 'y' for yes or 'n' for no.")


def create_products(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS):

    data_lists, all_codes = get_data(every_product=True,
        source=SOURCE_PLATFORM, targets=[TARGET_PLATFORM])

    filtered_data = filter_data_list(data=data_lists, all_codes=all_codes, every_product=True, match=False, source=None)

    if filtered_data:

        hpapi_add_listing(filtered_data)

    print('Done')


printr('What operation would you like to perform?\n')
printr('1. Create new product\n2. Update existing product\n')
operation = input('Choose an operation from above: ')

if operation == '1':

    printr('How would you like to create a new product?\n')
    printr('1. Copy from another platform\n2. Enter details manually\n')
    create_option = input('Choose an option from above: ')

    if create_option == '1':

        SOURCE_PLATFORM = input(
            'Please enter the source platform to copy from: Ex. Trendyol\n')
        TARGET_PLATFORM = input(
            '\nPlease enter the target platform to copy to: Ex. PTTAVM\n')
        TARGET_OPTIONS = 'copy'

    elif create_option == '2':
        TARGET_OPTIONS = 'manual'

elif operation == '2':
    printr('Do you want to update specific platforms ?\n')
    printr('1. Yes\n2. No\n')
    options = input('Choose an option from above: ')

    if options == '1':
        SOURCE_PLATFORM = input(
            'Please enter the source website platform: Ex. Trendyol\n')
        TARGET_PLATFORM = input(
            '\nPlease enter the target website platform: Ex. Magento\n').split(' ')

        printr('Available operations:\n1. Full update\n2. Partial update\n')
        select_op = input("\nWhich operation will you be doing today ? ")

        if select_op == '1':
            TARGET_OPTIONS = 'full'
        elif select_op == '2':
            printr('Available partial operations: \n1. Quantity\n2. Price\n3. Information (Images, Properties, descriptons)\n')
            select_partial_op = input(
                "\nWhich partial operation will you choose ? ")

            if select_partial_op == '1':
                TARGET_OPTIONS = 'qty'
            elif select_partial_op == '2':
                TARGET_OPTIONS = 'price'
            elif select_partial_op == '3':
                TARGET_OPTIONS = 'info'
    else:
        SOURCE_PLATFORM = None
        TARGET_PLATFORM = None
        TARGET_OPTIONS = None

execute_updates(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS)

# create_products(SOURCE_PLATFORM, TARGET_PLATFORM, TARGET_OPTIONS)

print('\nAll updates has finished. The program will exit now!')
