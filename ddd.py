import requests

url = "https://isortagimgiris.pazarama.com/connect/token"

payload = 'grant_type=client_credentials&scope=merchantgatewayapi.fullaccess'
headers = {
  'Content-Type': 'application/x-www-form-urlencoded',
  'Authorization': 'Basic OTQ5NWRlYjQzYmQ4NDQ4OTg0NTRhMzI5NTIzYzNhN2E6NWJmM2I5MmRjNGQyNGM3ZmE2NDY3MWEzMjhlZWVjYTE='
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
