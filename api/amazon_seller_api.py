import json
import requests
import os
from dotenv import load_dotenv


load_dotenv()

client_id = os.getenv('SP_API_ID')
client_secret = os.getenv('SP_API_SECRET')
refresh_token = os.getenv('SP_API_REFRESH_TOKEN')

url = "https://api.amazon.com/auth/o2/token"

payload = f'grant_type=refresh_token&client_id={client_id}&client_secret={client_secret}&refresh_token={refresh_token}'
headers = {
  'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
}

response = requests.request("POST", url, headers=headers, data=payload)
response_content = json.loads(response.text)
access_token = response_content['access_token']
access_token_type = response_content['token_type']

print(response.text)