import json
import requests
import os
from dotenv import load_dotenv
from sp_api.api import Catalog, Reports, Orders
from sp_api.base import SellingApiException, Marketplaces
from sp_api.base.reportTypes import ReportType
from datetime import datetime, timedelta

load_dotenv()


client_id = os.getenv('SP_API_ID')
client_secret = os.getenv('SP_API_SECRET')
refresh_token = os.getenv('SP_API_REFRESH_TOKEN')
MarketPlaceID = os.getenv('AMAZONSELLERACCOUNTID')
credentials={
        'refresh_token': refresh_token,
        'lwa_app_id': client_id,
        'lwa_client_secret': client_secret
    }
# jj = f'{MarketPlaceID}'
# try:
#   # orders = Orders(credentials=credentials,marketplace=Marketplaces.TR).get_orders(CreatedAfter=(datetime.utcnow() - timedelta(days=20)).isoformat())
#   client = Reports(credentials=credentials,marketplace=Marketplaces.TR).create_report(reportType=ReportType.GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL, marketplaceIds=['A2Z045PNNSBEVP'])
#   
# except SellingApiException as ex:
#   print(f'{ex}')
token_url = "https://api.amazon.com/auth/o2/token"
payload = f'grant_type=refresh_token&client_id={client_id}&client_secret={client_secret}&refresh_token={refresh_token}'
headers = {
  'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
}

token_response = requests.request("POST", token_url, headers=headers, data=payload)
response_content = json.loads(token_response.text)
access_token = response_content['access_token']
access_token_type = response_content['token_type']

ordersEndpoint_url = 'https://sellingpartnerapi-eu.amazon.com/orders/v0/orders/?MarketplaceIds=A33AVAJ2PDY3EV&CreatedAfter=2019-10-07T17:58:48.017Z'
# report_payload = {
#     'marketplaceIds': [
#         f'{MarketPlaceID}',
#         ],
#         'keywords': 'hali',
#         'includedData': 'summaries',
#         'pageSize': 10
# }
orders_payload = f'marketplaceIds=[{MarketPlaceID}]&CreatedAfter=2019-10-07T17:58:48.017Z'
# Get the current time
current_time = datetime.utcnow()

# Format the time in the desired format
formatted_time = current_time.strftime('%Y%m%dT%H%M%SZ')
report_header = {
    'Content-Type': 'application/json',
    'x-amz-access-token': f'{access_token}',
    'x-amz-date': formatted_time
}
params = {
    'keywords': 'hali',  # Example keyword
    'marketplaceIds': Marketplaces.TR,  # Replace with your actual marketplace ID
    'includedData': 'summaries',  # Include summaries data
    'pageSize': 10  # Number of results per page
}

report_request = requests.get(ordersEndpoint_url, headers=report_header, data=[])

print(token_response.text)