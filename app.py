from api.trendyol_api import get_data
from api._N11_api_draft import get_details

Options = {
    "OPTION_1": 1,
    "OPTION_2": 2,
    "startDate": None,
    "endDate": None}

print("Do you want to filter by specific date?\nChoose by entering the option number from below:\n1. Yes\n2. No")

user_input = int(input())

if user_input == Options['OPTION_1']:
    print('Please enter start date ? Ex: 22/03/2024')
    Options['startDate'] = input()
    print('Please enter end date ? Ex: 22/04/2024')
    Options['endDate'] = input()
    print("Loading data ...")
    N11_data = get_details()
    Trendyol_data = get_data(Options['startDate'], Options['endDate'])

elif user_input == Options['OPTION_2']:
    N11_data = get_details()
    Trendyol_data = get_data(Options['startDate'], Options['endDate'])
else:
    print("Invalid input. Please try again.")

print(f'N11 Data: {N11_data}\n Trendyol Data: {Trendyol_data}')