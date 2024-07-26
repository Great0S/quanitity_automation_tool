

# import requests
# from api.amazon_seller_api import request_data


# product_definitions = request_data(
#     operation_uri=f"/definitions/2020-09-01/productTypes",
#     params={
#         "marketplaceIds": "A33AVAJ2PDY3EV",
#         "itemName": "Halı",
#         "locale": "tr_TR",
#         "searchLocale": "tr_TR",
#     },
#     payload=[],
#     method='GET')


# product_attrs = request_data(
#     operation_uri=f"/definitions/2020-09-01/productTypes/RUG",
#     params={
#         "marketplaceIds": "A33AVAJ2PDY3EV",
#         "requirements": "LISTING",
#         "locale": "en_US",
#     },
#     payload=[],
#     method='GET')

# print(sfd)

# from glob import glob
# import os
# import re

# file_saved = 'amazon-all-inventory'

# dir_path = os.getcwd()

# matching_files = glob(os.path.join(dir_path, f'*{file_saved}*'))

# for file in matching_files:

#     if re.search(r'\.csv', file):

#         file_saved = file


# print(dir_path)

dad = [{'url': 'https://cdn.dsmcdn.com/ty1432/product/media/images/prod/QC/20240720/10/8d3b8e67-723e-3920-9857-ae99c0924a33/1_org_zoom.jpg'}, {'url': 'https://cdn.dsmcdn.com/ty1433/product/media/images/prod/QC/20240720/10/0ed7ccc5-91d8-374e-bde1-cbd7e4f4e418/1_org_zoom.jpg'}, {'url': 'https://cdn.dsmcdn.com/ty1433/product/media/images/prod/QC/20240720/10/5b53a8e2-dc16-3242-95d5-c6a222e75bbe/1_org_zoom.jpg'},
       {'url': 'https://cdn.dsmcdn.com/ty1432/product/media/images/prod/QC/20240720/10/9c122bac-8936-38ae-850f-6834fc80f065/1_org_zoom.jpg'}, {'url': 'https://cdn.dsmcdn.com/ty1432/product/media/images/prod/QC/20240603/11/43e1556d-ede5-3007-9e2b-9712028886b9/1_org_zoom.jpg'}, {'url': 'https://cdn.dsmcdn.com/ty1432/product/media/images/prod/QC/20240710/18/96d72b1f-794b-3aba-a310-d0365d0d409f/1_org_zoom.jpg'}, {'url': 'https://cdn.dsmcdn.com/ty1433/product/media/images/prod/QC/20240530/13/078c924a-4ca9-304f-9718-e4d98c804eeb/1_org_zoom.jpg'}]

for i in enumerate(dad):

    if i[0] == 0:

       pass

    print(i[0])


    