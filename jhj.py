import csv
import json


lis = []

with open('kapionupaspasi.com_non_found.csv', 'r', newline='', encoding='utf-8') as csvfile:

    reader = csv.reader(csvfile)

    for item_id in reader:
        lis.append(json.loads(item_id[0].replace("'", "\"")))
