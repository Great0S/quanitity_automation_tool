""" These lines of code are importing specific functions from different API modules. Each API module
 seems to be related to a specific platform or service, such as Amazon, Hepsiburada, Pazarama,
 PTTAVM, Trendyol, and N11. By importing these functions, the main script can utilize the
 functionalities provided by these APIs to retrieve stock data, update listings, and perform other
 operations related to each platform."""

from api.amazon_seller_api import spapi_getlistings, spapi_update_listing
from api.hepsiburada_api import hbapi_stock_data, hbapi_update_listing
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.pttavm_api import getPTTAVM_procuctskData, pttavm_updateData
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import get_n11_stock_data, post_n11_data


def get_data(every_product: bool = False):
    """
    The function `get_data()` retrieves stock data from N11
    and Trendyol, and returns various lists and
    data related to the retrieved data.
    :return: the following variables:
    - n11_data: data from N11 stock
    - trendyol_data: data from Trendyol stock
    - all_codes: a list of all unique product codes from both N11 and Trendyol data
    - n11_ids: a list of product IDs from N11 data
    - trendyol_ids: a list of product IDs from Trendyol
    """

    # Retrieve stock data from N11 and Trendyol APIs
    n11_data = get_n11_stock_data(every_product)

    trendyol_data = get_trendyol_stock_data(every_product)

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


def process_update_data():

    """
    The function `process_update_data` retrieves data, processes stock updates from different platforms,
    and returns the platform updates.
    :return: The function `process_update_data()` is returning the list `platform_updates`.
    """

    #  This allows us to access and use these variables
    data_lists, all_codes = get_data()

    # Initializing empty lists. These lists will be used
    # to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates, matching_values = get_platform_updates(
        data_lists, all_codes)

    print(f'\nLength of the two lists:- \nPlatform updates is {
          len(platform_updates)}\nMatching codes is {len(matching_values)}\n')

    return platform_updates


def get_platform_updates(data, all_codes):

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

            if data[f'{platform}_data']:

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

                lowest_val = min(products, key=lambda x: x['qty'])

                for product in products:

                    if product['qty'] > lowest_val['qty']:

                        value_diff = int(
                            product['qty']) - int(lowest_val['qty'])

                        matching_values.append(
                            {'sku': product['id'],
                             'qty1': product['qty'],
                             'qty2': lowest_val['qty'],
                             'value_difference': value_diff})

                        changed_values.append(
                            {'id': product['id'],
                             'sku': item_key,
                             'price': product.get('price', None),
                             'qty': str(lowest_val['qty']),
                             'platform': product['platform']})
            else:

                continue

    return changed_values, matching_values


def execute_updates():
    """
    The function `execute_updates` processes update data
    for different platforms and calls corresponding
    update functions based on the platform.
    """

    post_data = process_update_data()

    for post in post_data:

        if post['platform'] == 'Trendyol':

            post_trendyol_data(post)

        elif post['platform'] == 'N11':

            post_n11_data(post)

        elif post['platform'] == 'Amazon':

            spapi_update_listing(post)

        elif post['platform'] == 'HepsiBurada':

            hbapi_update_listing(post)

        elif post['platform'] == 'Pazarama':

            pazarama_updateRequest(post)

        elif post['platform'] == 'PTTAVM':

            pttavm_updateData(post)


execute_updates()

print('All updates has finished. The program will exit now!')
