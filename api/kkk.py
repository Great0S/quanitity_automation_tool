import json
import requests

from amazon_seller_api import get_access_token

url = 
access_token = get_access_token()
params = {
    "marketplaceIds": "A33AVAJ2PDY3EV",
    "issueLocale": "en_US",
    "includedData": "attributes,fulfillmentAvailability",
    
}

headers = {
    "User-Agent": "BlazingAPI/0.1 (Lang=Python/3.11.7; platform=Windows/10)",
    "x-amz-access-token": access_token
}

response = requests.get(url, params=params, headers=headers)
refined = json.loads(response.text)

if response.status_code == 200:
    # Request was successful
    data = response.json()
    # Process the response data as needed
    print(data)
else:
    print(f"Request failed with status code {response.status_code}")
additional_info = {
    '408-6659271-4223524': {'AdditionalData': 'Some additional data for this order'},
    # Add more additional info mappings as needed
}

orders_list = [
    {'AmazonOrderId': '408-6659271-4223524', 'OrderStatus': 'Shipped', 'EarliestShipDate': '2022-03-07T00:30:00Z', 'LatestShipDate': '2022-03-07T00:30:00Z', 'PurchaseDate': '2022-03-06T11:42:02Z', 'City': None, 'County': 'Levazım Mh.'},
    # Add more order dictionaries
]

# Iterate through each order dictionary
for order in orders_list:
    # Get the AmazonOrderId for the current order
    order_id = order['AmazonOrderId']
    
    # Check if additional information exists for this order ID
    if order_id in additional_info:
        # Merge the additional information with the current order dictionary
        order.update(additional_info[order_id])

# Now each order dictionary in orders_list should have additional information if available
