import json
import time
import requests
import os
from simple_dotenv import GetEnv
from sp_api.api import Catalog, Reports, Orders
from sp_api.base import SellingApiException, Marketplaces
from sp_api.base.reportTypes import ReportType
from datetime import datetime, timedelta

from urllib import parse


client_id = str(GetEnv('SP_API_ID'))
client_secret = str(GetEnv('SP_API_SECRET'))
refresh_token = str(GetEnv('SP_API_REFRESH_TOKEN'))
MarketPlaceID = str(GetEnv("AMAZONTURKEYMARKETID"))
AmazonSA_ID = str(GetEnv('AMAZONSELLERACCOUNTID'))
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
def spapi_getOrders(rate_limit):

    token_response, access_token = get_access_token()

    params = {
    'MarketplaceIds': MarketPlaceID,
    'CreatedAfter': "2019-10-07T17:58:48.017Z"}
    rate = int(1 / rate_limit)    
    formatted_data = requestData(access_token, "/orders/v0/orders/", params)  
    first_seconds = current_seconds()
    seconds = 0

    
    orders = formatted_data['Orders']
    orders_dict = []
    
    while orders:
        if seconds >= rate:
            orderBasic_info(orders, orders_dict)
            params = {'MarketplaceIds': MarketPlaceID, "NextToken": parse.quote(formatted_data['NextToken'])}
            next_page_request = requestData(access_token, "/orders/v0/orders/", params)
            orders = next_page_request['Orders']
            seconds = 0
            first_seconds = current_seconds()
            
        else:
            time.sleep(rate)
            seconds_now = current_seconds()
            diff = seconds_now - first_seconds
            seconds = abs(diff) * 60
            count = 0
            
            continue
        
    return orders_dict

def current_seconds():
    time_now = datetime.now()
    second = time_now.strftime("%M.%S")
    return float(second)

def get_access_token():
    token_url = "https://api.amazon.com/auth/o2/token"
    payload = f'grant_type=refresh_token&client_id={client_id}&client_secret={client_secret}&refresh_token={refresh_token}'
    headers = {
  'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
}

    token_response = requests.request("POST", token_url, headers=headers, data=payload)
    response_content = json.loads(token_response.text)
    access_token = response_content['access_token']
    return token_response,access_token

def requestData(access_token, operation_uri, params: dict):

    Endpoint_url = f'https://sellingpartnerapi-eu.amazon.com{operation_uri}?'
    
    uri = '&'.join([f'{k}={params[k]}' for k, v in params.items()])

    # Get the current time
    current_time = datetime.utcnow()

    # Format the time in the desired format
    formatted_time = current_time.strftime('%Y%m%dT%H%M%SZ')
    report_header = {
    'Content-Type': 'application/json',
    'x-amz-access-token': f'{access_token}',
    'x-amz-date': formatted_time
}   

    orders_request = requests.get(f"{Endpoint_url}{uri}", headers=report_header, data=[])
    jsonify = json.loads(orders_request.text)['payload']

    return jsonify

def orderBasic_info(orders, orders_list):
    
    for item in orders:
        city = None 
        if "ShippingAddress" in item and item['FulfillmentChannel'] == "MFN" and isinstance(item['ShippingAddress'], dict):
            city = item['ShippingAddress']['City']
            county = item['ShippingAddress'].get('County', None)
        
        # Create a dictionary for each item's information and append it to data_list
        data = {
            "AmazonOrderId": item.get('AmazonOrderId', None),
            "OrderStatus": item.get('OrderStatus', None),
            "EarliestShipDate": item.get('EarliestShipDate', None),
            "LatestShipDate": item.get('LatestShipDate', None),
            "PurchaseDate": item.get('PurchaseDate', None),
            "City": city,
            "County": county
        }
        
        orders_list.append(data)
    
    return orders_list

token_response = spapi_getOrders(rate_limit=0.0167)

print(token_response.text)