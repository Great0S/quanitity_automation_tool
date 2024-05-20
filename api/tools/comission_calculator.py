
import csv
import json
import chardet


def csv_to_json(csvFilePath):
    # Create a dictionary
    data = {}

    with open(csvFilePath, 'rb') as file:
        rawdata = file.read()
        result = chardet.detect(rawdata)
        encoding = result['encoding']

    # Replace 'your_csv_file.csv' with the actual path to your file
    with open(csvFilePath, 'r', encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)  # Convert reader object to a list of dictionaries

    # Now you have a list of dictionaries with headers as keys
    json_object = json.dumps(data, indent=2)

    return data


# Specify the CSV file path
csvFilePath = r'comissons.csv'


# Call the function to convert CSV to JSON
file_data = csv_to_json(csvFilePath)

items = {}

for product in file_data:

    name = product['ÜRÜN İSMİ']
    sku = product['SATICI STOK KODU']
    price = product['GÜNCEL TSF']
    comissions = ['0', product['1.KOMİSYON'], product['2.KOMİSYON'],
                  product['3.KOMİSYON'], product['4.KOMİSYON']]
    price_limits = {
        '1': [price, product['1.Fiyat Alt Limit']],
        '2': [product['2.Fiyat Üst Limiti'], product['2.Fiyat Alt Limit']],
        '3': [product['3.Fiyat Üst Limiti'], product['3.Fiyat Alt Limit']],
        '4': [product['4.Fiyat Üst Limiti'], 1],
    }

    calculated_comissions = {}

    for _, price_limit in price_limits.items():

        original_price_plus_comission = (float(price_limits['1'][0]) * float(comissions[1])) / 100
        orginial_price_minus_comissioned_price = float(price) - original_price_plus_comission

        price_plus_other_comission = (float(price_limit[0]) * float(comissions[int(_)])) / 100
        new_price_minus_new_comissioned_price = float(price_limit[0]) - price_plus_other_comission

        calculated_comissions[_] = {f'{price_limit[0]}TL': price_plus_other_comission,
                                    'orginial_price_minus_comissioned_price': orginial_price_minus_comissioned_price,
                                    'other_price_upper_limit': price_limit[0],
                                    'new_price_minus_new_comissioned_price': new_price_minus_new_comissioned_price,
                                    'comparison of other price with original price': orginial_price_minus_comissioned_price - new_price_minus_new_comissioned_price
                                    }

    items[sku] = {'name': name,
                  'price': price,
                  'comissions': calculated_comissions
                  }
    
     # Open the JSON file and write the data into it
    with open('calculated_comissions.json', 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(items, indent=4))

print(json.dumps(items, indent=4))

print('Done')
