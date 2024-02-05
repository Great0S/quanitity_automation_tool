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

    all_codes = list(set([item['id'] for item in N11_data] +
                         [item['productMainId'] for item in Trendyol_data]))
    n11_ids = [item['id'] for item in N11_data]
    trendyol_ids = [item['productMainId']
                    for item in Trendyol_data]

    return N11_data, Trendyol_data, all_codes, n11_ids, trendyol_ids


def process_data():

    #  This allows us to access and use these variables
    N11_data, Trendyol_data, all_codes, n11_ids, trendyol_ids = get_data()

    # Initializing empty lists. These lists will be used to store data during the processing of stock
    # data from N11 and Trendyol APIs.
    Trendyol_post_data = []
    N11_post_data = []
    changed_values = []
    matching_values = []

    for code in all_codes:
        if code in n11_ids:
            qty1 = [item['stok'] for item in N11_data if item['id'] == code][0]
        else:
            qty1 = None

        if code in trendyol_ids:
            qty2 = [item['quantity']
                    for item in Trendyol_data if item['productMainId'] == code][0]
            trend_barcode = [item['barcode']
                             for item in Trendyol_data if item['productMainId'] == code][0]
        else:
            qty2 = None

        if qty1 and qty2:
            if qty1 > qty2:
                value_diff = qty1 - qty2
            elif qty1 < qty2:
                value_diff = qty2 - qty1
            else:
                value_diff = None

            matching_values.append(
                {'code': code, 'qty1': qty1, 'qty2': qty2, 'value_difference': value_diff})

            if value_diff:
                qty = qty2
                for item in N11_data:
                    if item['productSellerCode'] == code:
                        try:
                            N11_post_data.append(
                                {'code': item['id'], 'qty': qty})
                        except ValueError:
                            continue
                    else:
                        continue
                changed_values.append(
                    {'code': code, 'qty': str(qty)})

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

    print(
        f'\nLength of the two lists:- \nChanged values count is {len(changed_values)}\nMatching codes is {len(matching_values)}')

    if N11_post_data:
        changed_values = N11_post_data
    elif Trendyol_post_data:
        changed_values = Trendyol_post_data
    else:
        return changed_values


post_n11_data(process_data())
