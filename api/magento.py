import json
import os
from dotenv import load_dotenv
from oauthlib.common import generate_nonce
from oauthlib.oauth1 import Client
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time

def get_oauth_token(header, url, method):
    try:
        response = requests.request(
            method, url+"/oauth/initiate", headers=header, data={})
        response.raise_for_status()
        response_data = response.text.split("&")
        data_ready = [
            response_item.replace("=", '":"') for response_item in response_data
        ]
        parsed_data = {}
        for item in data_ready:
            key, value = item.split('":"')
            parsed_data[key] = value
        parsed_data.pop('oauth_callback_confirmed')
        return parsed_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get access token: {e}")


def get_verifier_token(data_content, url, username, password):
    try:
        # Set up Chrome options for headless mode
        chrome_options = Options()
        # Run Chrome in headless mode (no GUI)
        chrome_options.add_argument("--headless")

        # Create a Chrome WebDriver instance
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to the authorization URL
        driver.get(url+"/panel/oauth_authorize?oauth_token=" +
                   data_content['oauth_token'])

        # Find and interact with the username and password input fields
        username_input = driver.find_element(by='id', value="username")
        password_input = driver.find_element(by='id', value="login")

        # Enter username and password
        username_input.send_keys(username)
        password_input.send_keys(password)

        # submit the form by pressing Enter
        password_input.send_keys(Keys.RETURN)

        # Wait for the page to load (you might need to adjust the sleep time)
        time.sleep(3)
        submit_btn = driver.find_element(
            by='id', value="oauth_authorize_confirm")
        submit_btn = submit_btn.click()

        # Get the current URL after authorization (contains the returned value)
        final_url = driver.current_url

        # Close the browser
        driver.quit()

        verifier = final_url.split(
            '&')[1].replace('oauth_verifier=', '')

        return verifier
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get verifier token: {e}")


def get_access_token(consumer_key, consumer_secret, callback, auth_data, token, url):
    try:
        header = create_headers(key=consumer_key, secret=consumer_secret, callback=callback, verifier=auth_data, token=token, url=url, url_addon='/oauth/token', request_method='GET')
        response = requests.request("GET", url+"/oauth/token", headers=header, data={})
        response.raise_for_status()
        response_data = response.text.split("&")
        data_ready = [response_item.replace("=", '":"') for response_item in response_data]
        parsed_data = {}
        for item in data_ready:
            key, value = item.split('":"')
            parsed_data[key] = value

        return parsed_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get access token: {e}")


def create_headers(key, secret, callback, verifier, token, url, url_addon, request_method):
    if token:
        oauth_token = token['oauth_token']
        oauth_token_secret = token['oauth_token_secret']
    else:
        oauth_token = ''
        oauth_token_secret = ''

    client = Client(
        key,
        client_secret=secret,
        callback_uri=callback,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        verifier=verifier,
        nonce=generate_nonce(),
        timestamp=str(int(time.time())),
    )
    body, header, bod = Client.sign(client, uri=url+url_addon, http_method=request_method)
    return header


def fetch_products(base_url, callback, consumer_key, consumer_secret, username, password):
    verifier_token, access_token = get_token(consumer_key, consumer_secret, base_url, callback, 'GET', username, password)
    header = create_headers(consumer_key, consumer_secret, callback, verifier_token, access_token, base_url, '/api/rest/products?limit=100', 'GET')
    products = json.loads(requests.get(f'{base_url}/api/rest/products?limit=100', headers=header, data={}).text)

    page = 1
    product = []

    while products:
        for item in products:
            product.append(products[item])
            
        if len(products) < 100:
            break

        page += 1
        looping_header = create_headers(consumer_key, consumer_secret, callback, verifier_token, access_token, base_url, f'/api/rest/products?limit=100&page={page}', 'GET')
        products = json.loads(requests.get(f'{base_url}/api/rest/products?limit=100&page={page}', headers=looping_header, data={}).text)

    return product


def get_token(consumer_key, consumer_secret, base_url, callback, method, username, password):
    header = create_headers(key=consumer_key, secret=consumer_secret, callback=callback, verifier='', token=None, url=base_url, url_addon="/oauth/initiate", request_method=method)
    oauth_token = get_oauth_token(header, base_url, method)
    verifier_token = get_verifier_token(oauth_token, base_url, username, password)
    access_token = get_access_token(consumer_key, consumer_secret, callback, verifier_token, oauth_token, base_url)
    return verifier_token, access_token

def duvardan_duvara_products():
    load_dotenv()
    consumer_key = os.getenv('DUVARDANDUVARA_KEY')
    consumer_secret = os.getenv('DUVARDANDUVARA_SECRET')
    username = os.getenv('USER')
    password = os.getenv('PASSWORD')
    base_url = "https://www.duvardanduvara.com"
    callback_address = "https://www.duvardanduvara.com/response.php"
    product_list = fetch_products(consumer_key=consumer_key, consumer_secret=consumer_secret, base_url=base_url, callback=callback_address, username=username, password=password)

    return product_list

dnd_products = duvardan_duvara_products()

print(len(dnd_products))
