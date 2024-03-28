""" The lines `import csv`, `import os`, `import requests`, and `import xmltodict` are importing
 necessary Python libraries/modules for the script to use."""
import csv
import os
import re
import time
import requests
import xmltodict
from rich import print as printr


username = os.environ.get('PTTAVMUSERNAME')
password = os.environ.get('PTTAVMPASSWORD')
TedarikciId = os.environ.get('PTTAVMTEDARIKCIID')


def requestdata(method: str = 'POST', uri: str = '', params: dict = None, data: list = ''):
    """
    The function `requestData` sends a SOAP request to a specific 
    URL with provided parameters and data,
    handling the response accordingly.

    :param method: The `method` parameter in the `requestData` 
    function specifies the HTTP method to be
    used for the request. By default, it is set to 'POST', but 
    you can provide a different HTTP method
    like 'GET', 'PUT', 'DELETE', etc, defaults to POST
    :type method: str (optional)
    :param uri: The `uri` parameter in the `requestData` function 
    represents the specific endpoint or
    operation that you want to call on the SOAP web service hosted at
    "https://ws.pttavm.com:93/service.svc". It is used to construct 
    the SOAPAction header in the HTTP
    request to specify the
    :type uri: str
    :param params: The `params` parameter in the `requestData` 
    function is used to pass any query
    parameters that need to be included in the request URL. These 
    parameters are typically used for
    filtering or pagination purposes when making HTTP requests
    :type params: dict
    :param data: The `data` parameter in the `requestData` function 
    is used to pass the SOAP body
    content for the SOAP request. It is a string that contains the 
    XML data to be sent in the SOAP
    envelope's body section. This data typically includes the specific 
    operation or action that the SOAP
    request is intended to
    :type data: list
    :return: The function `requestData` returns the response object 
    from the HTTP request made to the
    specified URL. If the response status code is 200, it returns the 
    response object. If there is an
    error or the status code is not 200, it prints an error message 
    and returns None.
    """

    url = "https://ws.pttavm.com:93/service.svc"

    payload = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/" xmlns:ept="http://schemas.datacontract.org/2004/07/ePttAVMService">
    <soapenv:Header>
        <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <wsse:UsernameToken>
                <wsse:Username>{username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
   <soapenv:Body>
    {data}
    </soapenv:Body>
</soapenv:Envelope>
"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'http://tempuri.org/IService/{uri}'
    }

    while True:

        response = requests.request(
            method, url, headers=headers, params=params, data=payload, timeout=3000)

        if response.status_code == 200:

            return response

        error_response = formatdata(response)['s:Fault']['faultstring']['#text']\

        if not re.search('dakika', error_response):

            return error_response

        time.sleep(2)


def formatdata(response):
    """
    The `formatData` function parses an XML response 
    into a dictionary and returns the body content.

    :param response: It looks like the code snippet 
    you provided is a function named `formatData` that
    takes a `response` parameter. The function is designed 
    to parse an XML response into a dictionary
    using the `xmltodict` library and then access specific 
    elements within the response
    :return: The function `formatData(response)` returns 
    the body content of the XML response parsed
    into a dictionary using the xmltodict library.
    """

    # Access the response elements
    raw_xml = response.text

    # Parse the XML response into a dictionary using xmltodict library.
    response_json = xmltodict.parse(raw_xml)

    # Access the response elements using the response_namespace and list_name variables.
    body_content = response_json['s:Envelope']['s:Body']

    return body_content


def getpttavm_procuctskdata(everyproduct: bool = False):
    """
    The function `getPTTAVM_procuctskData` retrieves product 
    data from an API and returns a list of
    products with specific details.

    :param everyProduct: The `everyProduct` parameter in the 
    `getPTTAVM_procuctskData` function is a
    boolean parameter with a default value of `False`. This 
    parameter is used to determine whether to
    return data for every product or just a summary of products, 
    defaults to False
    :type everyProduct: bool (optional)
    :return: If the `everyProduct` parameter is `False`, the 
    function will return a list of dictionaries
    containing product information (id, sku, qty, price) extracted 
    from the API response. If the
    `everyProduct` parameter is `True`, the function will return 
    the entire list of products as received
    from the API without any further processing.
    """

    api_call = requestdata(uri='StokKontrolListesi')
    products = []

    if api_call.status_code == 200:

        products_list = formatdata(api_call)[
            'StokKontrolListesiResponse']['StokKontrolListesiResult']['a:StokKontrolDetay']

        if not everyproduct:

            for product in products_list:

                products.append({'id': product['a:Barkod'],
                                 'sku': product['a:UrunKodu'],
                                 'qty': int(product['a:Miktar']),
                                 'price': float(product['a:KDVsiz'])})

            printr('PTTAVM products data request is successful. Response: ',
                   api_call.reason)

            return products

        return products_list

    return None


def pttavm_updatedata(product):
    """
    The function `pttavm_updateData` updates product data 
    on a platform called PTTAVM by sending a
    request with the provided product information.

    :param product: The `pttavm_updateData` function seems 
    to be updating product data for a PTTAVM
    system. The function takes a `product` dictionary as a 
    parameter, which should contain the following
    keys:
    """

    sku = product['sku']
    item_id = product['id']
    qty = product['qty']
    price = product['price']
    price_kdvsiz = product['price'] - product['price'] * (10/100)

    update_payload = f"""
    <tem:StokFiyatGuncelle3>
        <tem:item>
            <ept:Aktif>true</ept:Aktif>
            <ept:Barkod>{item_id}</ept:Barkod>
            <ept:KDVOran>10</ept:KDVOran>
            <ept:KDVli>{price}</ept:KDVli>
            <ept:KDVsiz>{price_kdvsiz}</ept:KDVsiz>
            <ept:Miktar>{qty}</ept:Miktar>
            <ept:ShopId>{TedarikciId}</ept:ShopId>
        </tem:item>
    </tem:StokFiyatGuncelle3>"""

    update_request = requestdata(uri='StokFiyatGuncelle3', data=update_payload)

    if isinstance(update_request, requests.Response):

        responses_msg = formatdata(update_request)[
            'StokFiyatGuncelle3Response']['StokFiyatGuncelle3Result']

        printr(f"""PTTAVM product success: {
            responses_msg['a:Success']}, sku: {sku}, New stock: {qty}, New price: {price}""")

    else:

        printr(f"""Request failure for PTTAVM product {sku} | Response: {
            update_request}""")


def save_to_csv(data, filename=""):
    """
    The function `save_to_csv` takes a list of dictionaries, 
    extracts keys from the dictionaries, and
    writes the data to a CSV file with the specified filename.

    :param data: The `data` parameter in the `save_to_csv` 
    function is expected to be a list of
    dictionaries. Each dictionary in the list represents a 
    row of data to be written to the CSV file.
    The keys of these dictionaries will be used as the column 
    headers in the CSV file
    :param filename: The `filename` parameter in the `save_to_csv` 
    function is a string that specifies
    the name of the CSV file where the data will be saved. If no 
    filename is provided, the default value
    is an empty string
    """

    if data:

        keys = set()

        for item in data:

            keys.update(item.keys())

        with open(f"{filename}_data_list.csv", "w", newline='', encoding="utf-8") as csvfile:

            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))

            file_writer.writeheader()

            for d in data:

                file_writer.writerow(d)
