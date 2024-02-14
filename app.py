from api.trendyol_api import get_trendyol_stock_data
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


def get_data():
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
    N11_data = get_n11_stock_data()
    Trendyol_data = get_trendyol_stock_data()
    data_content = {"Trendyol_data": Trendyol_data, "N11_data": N11_data}

    all_codes = list(set([item['code'] for item in N11_data] +
                         [item['code'] for item in Trendyol_data]))
    n11_ids = [item['code'] for item in N11_data]
    trendyol_ids = [item['code']
                    for item in Trendyol_data]

    return data_content, all_codes, n11_ids, trendyol_ids


def process_data():

    #  This allows us to access and use these variables
    data_lists, all_codes, n11_ids, trendyol_ids = get_data()

    # Initializing empty lists. These lists will be used to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    platform_updates, matching_values = get_platform_updates(data_lists, all_codes, n11_ids, trendyol_ids)

    print(
        f'\nLength of the two lists:- \nPlatform updates is {len(platform_updates)}\nMatching codes is {len(matching_values)}\n')
    


    # if len(N11_post_data) > 0:
    #     changed_values = N11_post_data
    # elif len(Trendyol_post_data) > 0:
    #     changed_values = Trendyol_post_data
    # else:
    return platform_updates

def get_platform_updates(data, all_codes, n11_ids, trendyol_ids):
    changed_values = []
    matching_values = []
    qty1 = None
    qty2 = None

    for code in all_codes:
        if code in n11_ids and code in trendyol_ids:
            for item in data['N11_data']:
                if item['code'] == code:
                    qty1 = item['stok']
                    break
                else:
                    qty1 = None
            for item in data['Trendyol_data']:
                if item['code'] == code:
                    qty2 = item['stok']
                    trend_barcode = item['id']
                    break
                else:
                    qty2 = None

        if qty1 and qty2 is not None:      
            qty = None      
            if qty1 > qty2:
                value_diff = qty1 - qty2
                qty = qty2
                target = 'N11'
            elif qty1 < qty2:
                value_diff = qty2 - qty1
                qty = qty1
                target = 'Trendyol'                
            else:
                value_diff = None

            matching_values.append(
                {'code': code, 'qty1': qty1, 'qty2': qty2, 'value_difference': value_diff})

            if value_diff:
                # data_list = data[f'{target}_data']
                # for item in data_list:
                #     if item['code'] == code:
                #         try:
                #             new_post_data.append(
                #                 {'code': item['code'], 'qty': qty})
                #         except ValueError:
                #             continue
                #     else:
                #         continue
                changed_values.append(
                    {'code': code, 'qty': str(qty), 'platform': target})

                # for item in Trendyol_data:
                #     if item['productMainId'] == code:
                #         try:
                #             Trendyol_post_data.append(
                #             {'barcode': item['barcode'], 'quantity': qty})
                #         except ValueError:
                #             continue
                #     else:
                #         continue
            else:
                continue
    return changed_values,matching_values

post_data = process_data()

post_n11_data(post_data)
