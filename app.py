from api.amazon_seller_api import spapi_getListings, spapi_updateListing
from api.hepsiburada_api import hbapi_stock_data, hbapi_updateListing
from api.pazarama_api import getPazarama_productsList, pazarama_updateRequest
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.n11_api import get_n11_stock_data, post_n11_data

# Options = {
#     "OPTION_1": 1,
#     "OPTION_2": 2,
#     "startDate": None,
#     "endDate": None}

# print("Do you want to filter by specific date?\nChoose by entering the option number from below:\n1. Yes\n2. No")

# user_input = int(input())

# if user_input == Options['OPTION_1']:
#     print('Please enter start date ? Ex: 22/03/2024')
#     Options['startDate'] = input()
#     print('Please enter end date ? Ex: 22/04/2024')
#     Options['endDate'] = input()
#     print("Loading data ...")
#     N11_data = get_details()
#     Trendyol_data = get_data(Options['startDate'], Options['endDate'])

# elif user_input == Options['OPTION_2']:
#     N11_data = get_details()
#     Trendyol_data = get_data(Options['startDate'], Options['endDate'])
# else:
#     print("Invalid input. Please try again.")


def get_data(everyProduct: bool = False):
    
    """
    The function `get_data()` retrieves stock data from N11 and Trendyol, and returns various lists and
    data related to the retrieved data.
    :return: the following variables:
    - N11_data: data from N11 stock
    - Trendyol_data: data from Trendyol stock
    - all_codes: a list of all unique product codes from both N11 and Trendyol data
    - n11_ids: a list of product IDs from N11 data
    - trendyol_ids: a list of product IDs from Trendyol
    """

    # Retrieve stock data from N11 and Trendyol APIs
    N11_data = get_n11_stock_data(everyProduct)

    Trendyol_data = get_trendyol_stock_data(everyProduct)

    Amazon_data = spapi_getListings(everyProduct)

    HepsiBurada_data = hbapi_stock_data(everyProduct)

    Pazarama_data = getPazarama_productsList(everyProduct)

    data_content = {"Trendyol_data": Trendyol_data,
                    "N11_data": N11_data, 
                    "Amazon_data": Amazon_data, 
                    "HepsiBurada_data": HepsiBurada_data, 
                    "Pazarama_data": Pazarama_data}

    if everyProduct:

        pass

    else:

        all_codes = list(set([item['sku'] for item in N11_data] +
                             [item['sku'] for item in Trendyol_data] + 
                             [item['sku'] for item in Amazon_data] + 
                             [item['sku'] for item in HepsiBurada_data] + 
                             [item['sku'] for item in Pazarama_data]))

    return data_content, all_codes


def process_update_data():

    #  This allows us to access and use these variables
    data_lists, all_codes = get_data()

    # Initializing empty lists. These lists will be used to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates, matching_values = get_platform_updates(
        data_lists, all_codes)

    print(f'\nLength of the two lists:- 
          \nPlatform updates is {len(platform_updates)}\nMatching codes is {len(matching_values)}\n')

    return platform_updates


def get_platform_updates(data, all_codes):

    changed_values = []

    platforms = ['Trendyol', 
                 'N11', 
                 'Amazon', 
                 'HepsiBurada', 
                 'Pazarama']

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
                                 'qty': quantity})

                        else:

                            matching_ids[code] = [
                                {'platform': platform, 
                                 'id': item_id,  
                                 'qty': quantity}]

                        break

    if matching_ids:

        for item_key in matching_ids:

            products = matching_ids[item_key]

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
                             'qty': str(lowest_val['qty']), 
                             'platform': product['platform']})
            else:

                continue

    return changed_values, matching_values


def execute_updates():

    post_data = process_update_data()

    for post in post_data:

        if post['platform'] == 'Trendyol':

            post_trendyol_data(post)

        elif post['platform'] == 'N11':

            post_n11_data(post)

        elif post['platform'] == 'Amazon':

            spapi_updateListing(post)

        elif post['platform'] == 'HepsiBurada':

            hbapi_updateListing(post)

        elif post['platform'] == 'Pazarama':

            pazarama_updateRequest(post)


execute_updates()

print('All updates has finished. The program will exit now!')
