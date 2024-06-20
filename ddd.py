

import requests
from api.amazon_seller_api import request_data


product_definitions = request_data(
    operation_uri=f"/definitions/2020-09-01/productTypes",
    params={
        "marketplaceIds": "A33AVAJ2PDY3EV",
        "itemName": "Halı",
        "locale": "tr_TR",
        "searchLocale": "tr_TR",
    },
    payload=[],
    method='GET')


product_attrs = request_data(
    operation_uri=f"/definitions/2020-09-01/productTypes/RUG",
    params={
        "marketplaceIds": "A33AVAJ2PDY3EV",
        "requirements": "LISTING",
        "locale": "en_US",
    },
    payload=[],
    method='GET')

print(sfd)
