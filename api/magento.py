from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from functools import partial
import re
import sys
from dotenv import load_dotenv
from oauthlib.common import generate_nonce
from oauthlib.oauth1 import Client
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import json
import os


def get_oauth_token(consumer_key: str, consumer_secret: str, url: str, callback: str, method: str):
    """
    The function `get_oauth_token` retrieves an OAuth token using the provided consumer key, consumer
    secret, URL, callback, and method.
    
    :param consumer_key: The consumer key is a unique identifier for the application or client making
    the OAuth request. It is obtained when registering the application with the OAuth provider
    :type consumer_key: str
    :param consumer_secret: The `consumer_secret` parameter is a string that represents the secret key
    for the OAuth consumer. It is used to authenticate the consumer when making requests to the OAuth
    server
    :type consumer_secret: str
    :param url: The `url` parameter is the base URL of the OAuth provider's API. It is used to construct
    the full URL for the OAuth initiation endpoint
    :type url: str
    :param callback: The `callback` parameter is the URL where the OAuth provider will redirect the user
    after they have authorized the application. This URL should be provided by your application and
    should handle the authorization callback
    :type callback: str
    :param method: The `method` parameter is the HTTP method to be used for the request. It can be one
    of the following: "GET", "POST", "PUT", "DELETE", etc
    :type method: str
    :return: a dictionary containing the parsed data from the response.
    """
    try:
        client = create_headers(
            key=consumer_key, secret=consumer_secret, callback=callback, verifier='', token=None)
        header = Client.sign(
            client, uri=url+"/oauth/initiate", http_method=method)[1]
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


def get_verifier_token(data_content: dict, url: str, username: str, password: str):
    """
    The function `get_verifier_token` uses Selenium WebDriver to automate the process of logging in to a
    website and retrieving a verifier token from the final URL.
    
    :param data_content: The `data_content` parameter is a dictionary that contains the OAuth token. It
    is used to construct the authorization URL
    :param url: The `url` parameter is the base URL of the website or API that you are trying to
    authenticate with. It is used to construct the authorization URL and navigate to it using Selenium
    WebDriver
    :param username: The `username` parameter is the username or email address used for authentication
    on the website or application you are trying to access
    :param password: The `password` parameter is the password for the user account that will be used to
    log in to the authorization page
    :return: the verifier token.
    """

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

        # Using Selenium WebDriver to get the cookies from the current session.
        cookies = driver.get_cookies()

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


def get_access_token(consumer_key, consumer_secret, callback, auth_data, token, url, method):
    try:
        client = create_headers(key=consumer_key, secret=consumer_secret,
                                callback=callback, verifier=auth_data, token=token)
        header = Client.sign(
            client, uri=url+"/oauth/token", http_method=method)[1]
        response = requests.request(
            method, url+"/oauth/token", headers=header, data={})
        response.raise_for_status()
        response_data = response.text.split("&")
        data_ready = [response_item.replace(
            "=", '":"') for response_item in response_data]
        parsed_data = {}
        for item in data_ready:
            key, value = item.split('":"')
            parsed_data[key] = value

        return parsed_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get access token: {e}")


def create_headers(key, secret, callback, verifier, token):
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

    return client


def get_token(consumer_key, consumer_secret, base_url, callback, method, username, password):

    oauth_token = get_oauth_token(
        consumer_key, consumer_secret, base_url, callback, method)
    verifier_token = get_verifier_token(
        oauth_token, base_url, username, password)
    access_token = get_access_token(
        consumer_key, consumer_secret, callback, verifier_token, oauth_token, base_url, method)

    return {'verifier_token': verifier_token, 'access_token': access_token}


def fetch_products(base_url, callback, consumer_key, consumer_secret, username, password):
    access_tokens = get_token(
        consumer_key, consumer_secret, base_url, callback, 'GET', username, password)
    client = create_headers(key=consumer_key, secret=consumer_secret,
                            callback=callback, verifier=access_tokens['verifier_token'], token=access_tokens['access_token'])
    header = Client.sign(client, uri=f'{base_url}/api/rest/products?limit=100', http_method='GET')[1]
    content = requests.get(f'{base_url}/api/rest/products?limit=100', headers=header, data={})
    products = json.loads(content.text)

    page = 1
    product = []

    while products:
        for item in products:
            product.append(products[item])

        if len(products) < 100:
            break

        page += 1
        loop_client = create_headers(key=consumer_key, secret=consumer_secret,callback=callback, verifier=access_tokens['verifier_token'], token=access_tokens['access_token'])
        looping_header = Client.sign(loop_client, uri=f'{base_url}/api/rest/products?limit=100&page={page}', http_method='GET')[1]
        products = json.loads(requests.get(f'{base_url}/api/rest/products?limit=100&page={page}', headers=looping_header, data={}).text)

    return product


def get_products_list(url):
    consumer_key, consumer_secret, username, password, base_url, callback_address = assign_vars(url)
    product_list = fetch_products(consumer_key=consumer_key, consumer_secret=consumer_secret,
                                  base_url=base_url, callback=callback_address, username=username, password=password)

    return product_list


def assign_vars(url):
    load_dotenv()
    env = re.sub(r'\.com$', '', url).upper()
    consumer_key = os.getenv(f'{env}_KEY')
    consumer_secret = os.getenv(f'{env}_SECRET')
    username = os.getenv('USER')
    password = os.getenv('PASSWORD')
    base_url = f"https://www.{url}"
    callback_address = f"https://www.{url}/hakkimizda"

    return consumer_key, consumer_secret, username, password, base_url, callback_address


def process_updates(source_url: str, target_url: str):
    """
    The function `process_updates` takes in two URLs, extracts data from the source URL and compares it
    with the target URL, and allows the user to update the found items or continue processing non-found
    products.
    
    :param source_url: The `source_url` parameter is a string that represents the URL of the source
    website from which data needs to be extracted
    :type source_url: str
    :param target_url: The `target_url` parameter is the URL of the target website where the data will
    be updated
    :type target_url: str
    """

    source_env = re.sub(r'\.com$', '', source_url).upper()
    target_env = re.sub(r'\.com$', '', target_url).upper()
    not_found, found = extract_data(
        source_url, target_url, source_env, target_env, [])

    while len(found) != 0 or len(not_found) != 0:
        if found:
            print(f'Do you want to update the {len(found)} found items?')
            user_input = input('Enter Yes or No to continue...\n')
            if user_input == 'Yes' or 'YES':
                successful = update_product(found)
                found = []
                if len(successful) == len(found):
                    print(f'{len(successful)} products were updated successfully.')
        elif len(found) == 0 and not_found:
            print(f'Do you want to continue processing non found products? ')
            user_input = input('1. Continue\n2. Exit\n')

            if user_input == '1':
                while True:
                    url_input = input(
                        'Please enter the website url you want to scrap: ')
                    source_website = url_input
                    if re.search(r'www', url_input):
                        print(
                            "Please enter the website you want to scrap without www at the start: ")
                    elif url_input:
                        break
                    else:
                        print('Invalid value please try again!')

                user_input_env = re.sub(r'\.com$', '', url_input).upper()
                non_found, found = extract_data(
                    source_url, target_url, user_input_env, target_env, not_found)
                not_found = non_found

            elif user_input == '2':
                print('The program will exit now! Have a good day.')
                sys.exit()
        elif len(found) == 0 and len(not_found) == 0:
            print('\n\nThe program will exit now!')
            sys.exit()

def update_product(found):
    consumer_key, consumer_secret, username, password, base_url, callback_address = assign_vars(target_website)
    tokens = get_token(consumer_key, consumer_secret, base_url, callback_address, 'PUT', username, password)
    print('\nUpdating please wait ...')
    partial_func = partial(update_request, tokens)
    with ThreadPoolExecutor(max_workers=27) as executor:
        successful = list(executor.map(partial_func, found))
    return successful


def update_request(tokens, item: dict ):
    """
    The function `update_data` updates product data using a PUT request to a specified URL, and returns
    a list of successfully updated product IDs.
    
    :param url: The `url` parameter is a string that represents the URL of the API endpoint you want to
    update data on
    :type url: str
    :param env: The `env` parameter is a string that represents the environment or server where the data
    will be updated. It could be a development, staging, or production environment
    :type env: str
    :param found: The `found` parameter is a list of dictionaries. Each dictionary represents a product
    that needs to be updated. Each dictionary should have the following keys:
    :type found: list
    :return: a list of successful updates.
    """

    successful = []

    consumer_key, consumer_secret, username, password, base_url, callback_address = assign_vars(target_website)
    
    while True:
        client = create_headers(consumer_key, consumer_secret, callback_address, tokens['verifier_token'], tokens['access_token'])
        header = Client.sign(client, uri=f"{base_url}/api/rest/products/{item['entity_id']}", headers={"Content-Type": "application/json"}, http_method='PUT', body=json.dumps(item))[1]
        update_response = requests.request("PUT", f"{base_url}/api/rest/products/{item['entity_id']}", headers=header, data=json.dumps(item))
        if update_response.status_code == 200:
            successful = item['entity_id']
            break
        elif update_response.status_code == 500:
            print(f"Timeout error for {item['entity_id']} | Retrying...")
        else:
            error = json.loads(update_response.text)['messages']['error'][0]['message']
            if 'Resource unknown error.' == error:
                successful = item['entity_id']
                break
            else:
                print(f'Product with sku {item['entity_id']} has error | Error: {
                  update_response.text}')
                break
    return successful


def extract_data(source_url: str, target_url: str, source_env: str, target_env: str, data_exist: list):
    """
    The function `extract_data` compares data from two websites and returns a list of items that are
    found and not found in the second website.

    :param data_url: The `data_url` parameter is a string that represents the URL of the data source. It
    is used to fetch the data from the specified URL
    :type data_url: str
    :param data_env: The `data_env` parameter is a string that represents the environment or source of
    the data. It could be a URL or any other identifier that specifies where the data is coming from
    :type data_env: str
    :param data_exist: The parameter `data_exist` is a list that contains existing data from a website.
    It is used to compare the existing data with the data obtained from another website
    :type data_exist: list
    :return: The function `extract_data` returns two lists: `non_found` and `found`.
    """

    non_found = []
    found = []

    if data_exist:
        updates_source = get_products_list(source_url)
        updates_source_sku = [item['sku']for item in updates_source]
        for website_item in data_exist:

            updates_target_item_id = website_item['entity_id']
            updates_target_price = int(float(website_item['price']))
            updates_target_sku = website_item['sku']

            if updates_target_sku in updates_source_sku:
                updates_source_sku_index = updates_source_sku.index(
                    updates_target_sku)
                updates_source_price = int(
                    float(updates_source[updates_source_sku_index]['price']))
                if updates_source_price < 100:
                    updates_source_price = int(updates_source_price * 32.8)

                if updates_target_price == updates_source_price:
                    continue
                else:
                    found.append(
                        {"entity_id": f"{updates_target_item_id}", "price": f"{updates_source_price}"})
            else:
                non_found.append({"sku": updates_target_sku, "entity_id": f"{updates_target_item_id}", "price": f"{updates_target_price}"})
    else:
        updates_target = get_products_list(target_url)
        updates_target_items = [{'id': item['entity_id'], 'sku': item['sku'],
                                 'price': item['price']} for item in updates_target if 'price' in item]
        updates_source = get_products_list(source_url)
        updates_source_sku = [item['sku']for item in updates_source]
        for website_item in updates_target_items:

            updates_target_price = int(float(website_item['price']))
            updates_target_item_id = website_item['id']
            updates_target_sku = website_item['sku']

            if website_item['sku'] in updates_source_sku:

                updates_source_sku_index = updates_source_sku.index(
                    website_item['sku'])
                updates_source_price = int(
                    float(updates_source[updates_source_sku_index]['price']))
                if updates_source_price < 100:
                    updates_source_price = int(updates_source_price * 32.8)

                if updates_target_price == updates_source_price:
                    continue
                else:
                    # Found items from website2 (Updates source) with matching sku from website1 (Updates target)
                    found.append(
                        {"entity_id": f"{updates_target_item_id}", "price": f"{updates_source_price}"})
            else:
                # Non found items from the first website (Updates target) in the second website (Updates source)
                non_found.append({"sku": updates_target_sku, "entity_id": f"{updates_target_item_id}", "price": f"{updates_target_price}"})

    if non_found:
        not_found_file = f'{target_url}_non_found.csv'
        with open(not_found_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for id in non_found:
                writer.writerow([id])
        print(f'Length of found items: {
              len(found)} | Non-found: {len(non_found)}')
    else:
        print(f'Length of found items: {len(found)}')

    return non_found, found

source_website = input('Please enter the source website domain: Ex. website.com\n')
# source_platform = input('Please enter the source website platform: Ex. Magento\n')
target_website = input('\nPlease enter the target website domain: Ex. website.com\n')
# target_platform = input('\nPlease enter the target website platform: Ex. Magento\n')
process_updates(source_url=source_website, target_url=target_website)
