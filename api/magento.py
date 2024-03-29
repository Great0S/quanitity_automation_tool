""" The code snippet imports 
  various modules such as `ThreadPoolExecutor`,
 `csv`, `partial`, `re`, `sys`, `time`, `json`, `os`, 
 `generate_nonce` from `oauthlib.common`,
 `Client` from `oauthlib.oauth1`, `requests`, `webdriver`
   from `selenium`, `Keys` from
 `selenium.webdriver.common.keys`, and `Options` from 
 `selenium.webdriver.chrome.options`."""

from concurrent.futures import ThreadPoolExecutor
import csv
from functools import partial
import re
import sys
import time
import json
import os
from oauthlib.common import generate_nonce
from oauthlib.oauth1 import Client
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


def get_oauth_token(consumer_key: str, consumer_secret: str, url: str, callback: str, method: str):
    """
    The function `get_oauth_token` retrieves an OAuth token 
    using the provided consumer key, consumer
    secret, URL, callback, and method.
    """
    try:
        client = create_headers(
            key=consumer_key,
            secret=consumer_secret,
            callback=callback,
            verifier='', token=None)

        header = Client.sign(
            client,
            uri=url+"/oauth/initiate",
            http_method=method)[1]

        response = requests.request(
            method,
            url+"/oauth/initiate",
            headers=header,
            data={}, timeout=3000)

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

    except (requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects,
            requests.exceptions.HTTPError,
            requests.exceptions.RequestException) as e:
        raise Exception("Failed to get access token due to: %s" % e) from e


def get_verifier_token(data_content: dict, url: str, username: str, password: str):
    """
    The function `get_verifier_token` uses Selenium WebDriver 
    to automate the process of logging in to a
    website and retrieving a verifier token from the final URL.

    :param data_content: The `data_content` parameter is a 
    dictionary that contains the OAuth token. It
    is used to construct the authorization URL
    :param url: The `url` parameter is the base URL of the 
    website or API that you are trying to
    authenticate with. It is used to construct the authorization 
    URL and navigate to it using Selenium
    WebDriver
    :param username: The `username` parameter is the username 
    or email address used for authentication
    on the website or application you are trying to access
    :param password: The `password` parameter is the password 
    for the user account that will be used to
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
        # cookies = driver.get_cookies()

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
        raise Exception(f"Failed to get verifier token: {e}") from e


def get_access_token(consumer_key, consumer_secret, callback, auth_data, token, url, method):
    """
    The function `get_access_token` retrieves an access token using OAuth authentication.
    """

    try:
        client = create_headers(key=consumer_key, secret=consumer_secret,
                                callback=callback, verifier=auth_data, token=token)
        header = Client.sign(
            client,
            uri=url+"/oauth/token",
            http_method=method)[1]

        response = requests.request(
            method,
            url+"/oauth/token",
            headers=header,
            data={},
            timeout=3000)

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

        raise Exception(f"Failed to get access token: {e}") from e


def create_headers(key, secret, callback, verifier, token):
    """
    The function `create_headers` generates client headers
    for OAuth authentication using provided key,
    secret, callback, verifier, and token information.
    """

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
    """
    The function `get_token` retrieves a verifier token and an 
    access token using OAuth authentication.
    """

    oauth_token = get_oauth_token(
        consumer_key, consumer_secret, base_url, callback, method)

    verifier_token = get_verifier_token(
        oauth_token, base_url, username, password)

    access_token = get_access_token(
        consumer_key, consumer_secret, callback, verifier_token, oauth_token, base_url, method)

    return {'verifier_token': verifier_token, 'access_token': access_token}


def fetch_products(base_url, callback, consumer_key, consumer_secret, username, password):
    """
    This Python function fetches products from a specified 
    base URL using OAuth authentication and
    pagination.

    :param base_url: The `base_url` parameter is the base 
    URL of the API endpoint from which you want to
    fetch products. It is the starting point for constructing t
    he full URL for making API requests
    :param callback: The `callback` parameter in the `fetch_products` 
    function is typically used in
    OAuth authentication flows. It represents the URL to which the 
    service provider will redirect the
    user after they have approved access to their data. This URL is 
    often used to complete the
    authentication process and obtain access tokens
    :param consumer_key: The `consumer_key` is a unique identifier 
    assigned to your application when you
    register it with the API provider. It is used to authenticate 
    your application when making requests
    to the API
    :param consumer_secret: Consumer secret is a confidential key 
    that is used in OAuth authentication
    to verify the identity of the consumer (your application) to the
      service provider (API). It should
    be kept secure and not shared publicly
    :param username: The `username` parameter in the `fetch_products` 
    function is typically the username
    or identifier of the user who is making the request to fetch products 
    from the specified `base_url`.
    This username is often used for authentication purposes to ensure that 
    the user has the necessary
    permissions to access the products data
    :param password: The `password` parameter in the `fetch_products` 
    function is used to provide the
    password for authentication when making requests to the API. It is 
    typically required along with the
    `username` parameter to authenticate the user and authorize access 
    to the resources on the server.
    Make sure to keep the password secure and
    :return: The function `fetch_products` returns a list of products 
    fetched from a specified base URL
    using the provided credentials and authentication tokens.
    """

    access_tokens = get_token(
        consumer_key, consumer_secret, base_url, callback, 'GET', username, password)

    client = create_headers(key=consumer_key,
                            secret=consumer_secret,
                            callback=callback,
                            verifier=access_tokens['verifier_token'],
                            token=access_tokens['access_token'])

    header = Client.sign(
        client, uri=f'{base_url}/api/rest/products?limit=100', http_method='GET')[1]

    content = requests.get(
        f'{base_url}/api/rest/products?limit=100', headers=header, data={}, timeout=3000)

    products = json.loads(content.text)

    page = 1
    product = []

    while products:

        for item in products:

            product.append(products[item])

        if len(products) < 100:
            break

        page += 1

        loop_client = create_headers(key=consumer_key,
                                     secret=consumer_secret,
                                     callback=callback,
                                     verifier=access_tokens['verifier_token'],
                                     token=access_tokens['access_token'])

        looping_header = Client.sign(loop_client,
                                     uri=f'{
                                         base_url}/api/rest/products?limit=100&page={page}',
                                     http_method='GET')[1]

        loop_request = requests.get(
            f'{base_url}/api/rest/products?limit=100&page={page}',
            headers=looping_header, data={}, timeout=3000)

        products = json.loads(loop_request.text)

    return product


def get_products_list(url):
    """
    The function `get_products_list` fetches a list of products 
    from a specified URL using provided
    credentials and base URL.

    :param url: The `url` parameter is the URL that will be used 
    to fetch products. It is passed to the
    `get_products_list` function to retrieve a list of products 
    based on the provided URL
    :return: The function `get_products_list(url)` returns a list 
    of products fetched from a specified
    URL after assigning variables and fetching the products using 
    the provided credentials and base URL.
    """

    consumer_key, consumer_secret, username, password, base_url, callback_address = assign_vars(
        url)

    product_list = fetch_products(consumer_key=consumer_key,
                                  consumer_secret=consumer_secret,
                                  base_url=base_url,
                                  callback=callback_address,
                                  username=username, password=password)

    return product_list


def assign_vars(url):
    """
    The function `assign_vars` extracts environment-specific 
    variables from the URL and environment
    variables for authentication purposes.

    :param url: The `assign_vars` function takes a URL as 
    input and extracts various environment
    variables based on that URL. It then constructs and returns 
    a set of variables including consumer
    key, consumer secret, username, password, base URL, and 
    callback address
    :return: The function `assign_vars` returns the following 
    variables in order: consumer_key,
    consumer_secret, username, password, base_url, and callback_address.
    """

    env = re.sub(r'\.com$', '', url).upper()

    consumer_key = os.getenv(f'{env}_KEY')
    consumer_secret = os.getenv(f'{env}_SECRET')
    username = os.getenv('USER')
    password = os.getenv('PASSWORD')

    base_url = f"https://www.{url}"
    callback_address = f"https://www.{url}/hakkimizda"

    return consumer_key, consumer_secret, username, password, base_url, callback_address


def process_updates(source_url: str,
                    target_url: str,
                    offline_data: list = None,
                    offline_check: bool = False):
    """
    The function `process_updates` takes in two URLs, extracts 
    data from the source URL and compares it
    with the target URL, and allows the user to update the found 
    items or continue processing non-found
    products.

    :param source_url: The `source_url` parameter is a string that 
    represents the URL of the source
    website from which data needs to be extracted
    :type source_url: str
    :param target_url: The `target_url` parameter is the URL of the 
    target website where the data will
    be updated
    :type target_url: str
    """

    # source_env = re.sub(r'\.com$', '', source_url).upper()
    # target_env = re.sub(r'\.com$', '', target_url).upper()

    found, not_found = extract_data(
        source_url, target_url, offline_data, offline_check)

    while len(found) != 0 or len(not_found) != 0:

        if found:

            print(f'Do you want to update the {len(found)} found items?')

            user_input = input('Enter Yes or No to continue...\n')

            if user_input in {'Yes', 'YES'}:

                successful = update_product(found)
                found = []

                if len(successful) == len(found):

                    print(f'{len(successful)} products were updated successfully.')

        elif len(found) == 0 and not_found:

            print('Do you want to continue processing non found products? ')

            user_input = input('1. Continue\n2. Exit\n')

            if user_input == '1':

                while True:

                    url_input = input(
                        'Please enter the website url you want to scrap: ')

                    # source_website = url_input
                    if re.search(r'www', url_input):

                        print(
                            "Please enter the website you want to scrap without www at the start: ")

                    elif url_input:

                        break

                    else:

                        print('Invalid value please try again!')

                # user_input_env = re.sub(r'\.com$', '', url_input).upper()

                non_found, found = extract_data(
                    source_url, target_url, not_found)

                not_found = non_found

            elif user_input == '2':

                print('The program will exit now! Have a good day.')

                sys.exit()

        elif len(found) == 0 and len(not_found) == 0:

            print('\n\nThe program will exit now!')

            sys.exit()


def update_product(found):
    """
    The function `update_product` updates products on a 
    website using multiple threads for efficiency.

    :param found: The `found` parameter in the `update_product` 
    function likely represents a list of
    items or products that need to be updated on a website 
    or system. The function seems to be updating
    these products by making API requests using the provided 
    parameters such as consumer key, consumer
    secret, username, password, base
    :return: The function `update_product` is returning a list 
    of successful updates after making PUT
    requests to update products on a website.
    """

    consumer_key, consumer_secret, username, password, base_url, callback_address = assign_vars(
        TARGET_WEBSITE)

    tokens = get_token(consumer_key, consumer_secret, base_url,
                       callback_address, 'PUT', username, password)

    print('\nUpdating please wait ...')

    partial_func = partial(update_request, tokens)

    with ThreadPoolExecutor(max_workers=27) as executor:

        successful = list(executor.map(partial_func, found))

    return successful


def update_request(tokens, item: dict):
    """
    The function `update_data` updates product data using a 
    PUT request to a specified URL, and returns
    a list of successfully updated product IDs.

    :param url: The `url` parameter is a string that represents 
    the URL of the API endpoint you want to
    update data on
    :type url: str
    :param env: The `env` parameter is a string that represents 
    the environment or server where the data
    will be updated. It could be a development, staging, or production environment
    :type env: str
    :param found: The `found` parameter is a list of dictionaries. Each dictionary 
    represents a product
    that needs to be updated. Each dictionary should have the following keys:
    :type found: list
    :return: a list of successful updates.
    """

    successful = []

    consumer_key, consumer_secret, _, _, base_url, callback_address = assign_vars(
        TARGET_WEBSITE)

    while True:

        client = create_headers(consumer_key, consumer_secret, callback_address,
                                tokens['verifier_token'], tokens['access_token'])

        header = Client.sign(client, uri=f"{base_url}/api/rest/products/{item['entity_id']}",
                             headers={"Content-Type": "application/json"},
                             http_method='PUT',
                             body=json.dumps(item))[1]

        update_response = requests.request("PUT",
                                           f"{base_url}/api/rest/products/{
                                               item['entity_id']}",
                                           headers=header,
                                           data=json.dumps(item), timeout=3000)

        if update_response.status_code == 200:

            successful = item['entity_id']
            break

        if update_response.status_code == 500:

            print(f"Timeout error for {item['entity_id']} | Retrying...")

        error = json.loads(update_response.text)[
            'messages']['error'][0]['message']

        if 'Resource unknown error.' == error:

            successful = item['entity_id']

            break

        print(f"""Product with sku {item['entity_id']} has error | Error: {
            update_response.text}""")

        break

    return successful


def extract_data(source_url: str, target_url: str, data_exist: list, offline: bool = False):
    """
    The function `extract_data` extracts and filters data 
    from a source URL and a target URL, handling
    cases where data already exists or needs to be retrieved.

    :param source_url: The `source_url` parameter is a string 
    that represents the URL from which data
    will be extracted. This could be a URL pointing to a data 
    source such as an API endpoint or a web
    page
    :type source_url: str
    :param target_url: The `target_url` parameter in the 
    `extract_data` function is the URL from which
    you want to extract data or update products list. This 
    URL is used to fetch the products list and
    extract relevant information such as entity ID, SKU, 
    and price for each item. If the `data_exist`
    :type target_url: str
    :param data_exist: The `data_exist` parameter is a 
    list that contains items to be checked for in the
    source URL. If this list is not empty, the function 
    will filter these items from the source URL. If
    it is empty, the function will retrieve a list of 
    products from the target URL and filter them from
    :type data_exist: list
    :return: The function `extract_data` returns two values: 
    `found_items` and `non_founds`. These
    values represent the items that were found in the data 
    source and the items that were not found,
    respectively.
    """

    if data_exist:

        if offline:

            updates_data = []

            for website_item in data_exist:

                updates_data.append({'id': website_item['id'],
                                     'sku': website_item['sku'],
                                     'degisken_fiyatlar': website_item['degisken_fiyatlar']
                                     })

            return updates_data, None

        found_items, non_founds = filter_data(source_url, data_exist)

    else:

        updates_target = get_products_list(target_url)

        updates_target_items = [{'id': item['entity_id'], 'sku': item['sku'],
                                 'price': item['price']}
                                for item in updates_target if 'price' in item]

        found_items, non_founds = filter_data(source_url, updates_target_items)

    if non_founds:

        not_found_file = f'{target_url}_non_found.csv'

        with open(not_found_file, 'w', newline='', encoding='utf-8') as csvfile:

            writer = csv.writer(csvfile)

            for item_id in non_founds:
                writer.writerow([item_id])

        print(f"""Length of found items: {
              len(found_items)} | Non-found: {len(non_founds)}""")

    else:

        print(f'Length of found items: {len(found_items)}')

    return found_items, non_founds


def filter_data(source_url, data_exist):
    """
    The function `filter_data` compares data from 
    two sources based on SKU and price, updating prices if
    below 100 and returning found and non-found items.

    :param source_url: The `source_url` parameter in 
    the `filter_data` function is the URL from which
    you are fetching the updated product list. This 
    URL is used to retrieve the product data that will
    be compared with the existing data
    :param data_exist: The `data_exist` parameter in 
    the `filter_data` function seems to be a list of
    dictionaries representing existing data from a 
    website. Each dictionary in the list contains keys
    like 'price', 'id', and 'sku' for a particular product
    :return: The function `filter_data` returns two 
    lists: `found` and `non_found`.
    """

    non_found = []
    found = []

    updates_source = get_products_list(source_url)
    updates_source_sku = [item['sku']for item in updates_source]

    for website_item in data_exist:
        first_updates_target_data = {'price': int(float(website_item['price'])),
                                     'id': website_item['id'],
                                     'sku': website_item['sku']}

        if first_updates_target_data['sku'] in updates_source_sku:

            updates_source_sku_index = updates_source_sku.index(
                first_updates_target_data['sku'])

            updates_source_price = int(
                float(updates_source[updates_source_sku_index]['price']))

            if updates_source_price < 100:

                updates_source_price = int(updates_source_price * 35.1)

            if first_updates_target_data['price'] == updates_source_price:

                continue

            # Found items from website2 (Updates source) with
            # matching sku from website1 (Updates target)
            found.append(
                {"entity_id": f"{first_updates_target_data['id']}",
                 "price": f"{updates_source_price}"})

        else:
            # Non found items from the first website (Updates target)
            # in the second website (Updates source)
            non_found.append(first_updates_target_data)

    return found, non_found


def read_csv(file):
    """
    The function `local_data` reads 
    data from a CSV file and returns a 
    list of items after converting
    them from JSON strings.    
    """

    item_list = []

    with open(f'{file}.csv', 'r', newline='', encoding='utf-8-sig') as csvfile:

        reader = csv.DictReader(csvfile)

        for item_id in reader:
            item_list.append(item_id)

    return item_list


print("How do you want to update?\n")
print("1. Online\n")
print("2. Offline\n")
option_value = input(
    'Please choose an option from above: ')

if option_value == '2':

    file_value = input(
        'Please enter the file name without space: ')

    TARGET_WEBSITE = input(
        'Please enter the target website: Ex. website.com ')

    local = read_csv(file_value)

    process_updates(source_url=None, target_url=TARGET_WEBSITE,
                    offline_data=local, offline_check=True)

    print('Done')

source_website = input(
    'Please enter the source website domain: Ex. website.com\n')
# source_platform = input('Please enter the source website platform: Ex. Magento\n')
TARGET_WEBSITE = input(
    '\nPlease enter the target website domain: Ex. website.com\n')
# target_platform = input('\nPlease enter the target website platform: Ex. Magento\n')
process_updates(source_url=source_website, target_url=TARGET_WEBSITE)
