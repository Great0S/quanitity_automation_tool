import os
import requests


auth_hash = os.environ.get('HEPSIBURADAAUTHHASH')

url = "https://mpop.hepsiburada.com/product/api/products/import?version=1"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {auth_hash}'
}

files = {"file": ("integrator.json", open(
        "integrator.json", "rb"), "application/json")}
    
headers['Accept'] = 'application/json'
headers.pop('Content-Type')

response = requests.post(url, files=files, headers=headers)