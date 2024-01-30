from datetime import datetime
import json
import requests

# The code snippet is initializing some variables and setting up the headers for making API requests.
page = 0
url_addon = ""
products = []
headers = {
    'User-Agent': '120101 - SelfIntegration',
    'Authorization': 'Basic c1V0V1BWT3U4ZWdISldWcE5za0s6QVBhTU5rQjBuUVJQTzZSQ2tjeWc='
}


def request_data(url_addons, request_type, payload_content):
    """
    The function `request_data` sends a request to a specified URL with specified headers, request type,
    and payload content.

    :param url_addons: The `url_addons` parameter is a string that represents any additional path or
    query parameters that need to be added to the base URL. It is appended to the base URL to form the
    complete URL for the API request
    :param request_type: The `request_type` parameter is the type of HTTP request to be made. It can be
    one of the following: "GET", "POST", "PUT", "DELETE", etc
    :param payload_content: The payload_content parameter is the data that you want to send in the
    request. It can be in various formats such as JSON, XML, or form data. The content of the payload
    will depend on the specific API you are working with and the data it expects
    :return: the response object from the API request.
    """
    payload = payload_content
    url = f"https://api.trendyol.com/sapigw/suppliers/120101/products{url_addons}"

    return requests.request(request_type, url, headers=headers, data=payload)


def prepare_data(request_data):
    """
    The function prepares the data by decoding the response from a request.

    :param request_data: The parameter `request_data` is the data that is received from a request made
    to an API or a server. It could be in the form of a JSON string or any other format
    :return: the decoded data, which is a Python object obtained by parsing the response text as JSON.
    """
    response = request_data
    decoded_data = json.loads(response.text)
    return decoded_data


def get_data(startDate, endDate):
    """
    The function `get_data` retrieves data from multiple pages and appends it to a list of products.

    :param page: The `page` parameter is used to specify the page number of the data to retrieve. It is
    used in the URL to fetch data from different pages
    :param products: The `products` parameter is a list that will store the extracted data. Each item in
    the list will be a dictionary with two keys: "barcode" and "quantity". The "barcode" key will store
    the product's barcode, and the "quantity" key will store the quantity of the product
    """
    page = 0

    if startDate and endDate is not None:
        stDate = datetime.strptime(startDate, "%d/%m/%Y").date()
        enDate = datetime.strptime(endDate, "%d/%m/%Y").date()
        startDate = int(datetime.fromordinal(stDate.toordinal()).timestamp())
        endDate = int(datetime.fromordinal(enDate.toordinal()).timestamp())
        url_addon = f"?page={page}&size=100&startDate={startDate}&endDate={endDate}"
    else:
        url_addon = f"?page={page}&size=100"
    decoded_data = prepare_data(request_data(url_addon, "GET", {}))

    while page < int(decoded_data['totalPages']):
        for element in range(len(decoded_data['content'])):
            data = decoded_data['content'][element]
            item = data['productMainId']
            quantity = data['quantity']

            # Define the timestamp
            timestamp = data['createDateTime']

            # Convert the timestamp to milliseconds
            milliseconds = timestamp / 1000

            # Convert milliseconds to datetime object
            date_without_time = datetime.utcfromtimestamp(milliseconds).date()

            products.append({
                "barcode": f"{item}",
                "quantity": quantity,
                "date": date_without_time
            })

        page += 1
        url_addon = f"?page={page}&size=100"
        decoded_data = prepare_data(request_data(url_addon, "GET", {}))
    print(f"Data records extracted size is {len(products)}")
    return products


def post_data(products):
    """
    The function `post_data` sends a POST request to a specified URL with a payload containing a list of
    products.

    :param products: The "products" parameter is a list of items that you want to post to the server.
    Each item in the list should be a dictionary containing the necessary information for the server to
    process
    """
    url_addon = "/price-and-inventory"
    post_payload = json.dumps({
        "items": [products]
    })
    post_response = request_data(url_addon, "POST", post_payload)

    print(post_response.text)


# The `get_data(page, products)` function is responsible for retrieving data from multiple pages and
# appending it to a list of products.


# post_data(products, request_data, prepare_data)
print("Done!")
