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
