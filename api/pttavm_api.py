""" The lines `import csv`, `import os`, `import requests`, and `import xmltodict` are importing
 necessary Python libraries/modules for the script to use."""
import csv
import os
import requests
import xmltodict


username = os.environ.get('PTTAVMUSERNAME')
password = os.environ.get('PTTAVMPASSWORD')
TedarikciId = os.environ.get('PTTAVMTEDARIKCIID')


def requestData(method: str = 'POST', uri: str = '', params: dict = None, data: list = ''):

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

    response = requests.request(
        method, url, headers=headers, params=params, data=payload, timeout=3000)

    if response.status_code == 200:

        # response_data = json.loads(response.text)

        return response

    else:

        print(f'PTTAVM request has failed || Reason: {response.text}')

        return None


def formatData(response):
    """
    The `formatData` function parses an XML response into a dictionary and returns the body content.

    :param response: It looks like the code snippet you provided is a function named `formatData` that
    takes a `response` parameter. The function is designed to parse an XML response into a dictionary
    using the `xmltodict` library and then access specific elements within the response
    :return: The function `formatData(response)` returns the body content of the XML response parsed
    into a dictionary using the xmltodict library.
    """

    # Access the response elements
    raw_xml = response.text

    # Parse the XML response into a dictionary using xmltodict library.
    response_json = xmltodict.parse(raw_xml)

    # Access the response elements using the response_namespace and list_name variables.
    body_content = response_json['s:Envelope']['s:Body']

    return body_content


def getPTTAVM_procuctskData(everyProduct: bool = False):
    """
    The function `getPTTAVM_procuctskData` retrieves product data from an API and returns a list of
    products with specific details.

    :param everyProduct: The `everyProduct` parameter in the `getPTTAVM_procuctskData` function is a
    boolean parameter with a default value of `False`. This parameter is used to determine whether to
    return data for every product or just a summary of products, defaults to False
    :type everyProduct: bool (optional)
    :return: If the `everyProduct` parameter is `False`, the function will return a list of dictionaries
    containing product information (id, sku, qty, price) extracted from the API response. If the
    `everyProduct` parameter is `True`, the function will return the entire list of products as received
    from the API without any further processing.
    """

    api_call = requestData(uri='StokKontrolListesi')
    products = []

    if api_call.status_code == 200:

        products_list = formatData(api_call)[
            'StokKontrolListesiResponse']['StokKontrolListesiResult']['a:StokKontrolDetay']

        if not everyProduct:

            for product in products_list:

                products.append({'id': product['a:Barkod'],
                                 'sku': product['a:UrunKodu'],
                                 'qty': int(product['a:Miktar']),
                                 'price': float(product['a:KDVsiz'])})

            print('PTTAVM products data request is successful. Response: ',
                  api_call.reason)

            return products

        else:

            return products_list


def pttavm_updateData(product):

    sku = product['sku']
    item_id = product['id']
    qty = product['qty']
    price = product['price']

    update_payload = f"""
    <tem:StokFiyatGuncelle3>
        <tem:item>
            <ept:Aktif>true</ept:Aktif>
            <ept:Barkod>{item_id}</ept:Barkod>
            <ept:KDVOran>10</ept:KDVOran>
            <ept:KDVli>{price}</ept:KDVli>
            <ept:KDVsiz>0</ept:KDVsiz>
            <ept:Miktar>{qty}</ept:Miktar>
            <ept:ShopId>{TedarikciId}</ept:ShopId>
        </tem:item>
    </tem:StokFiyatGuncelle3>"""

    update_request = requestData(uri='StokFiyatGuncelle3', data=update_payload)

    response_feedback = formatData(update_request)

    if update_request.status_code == 200:

        print(f'PTTAVM product with sku: {sku}, New value: {qty}')

    else:

        print(f"Request failure for PTTAVM product {sku} | Response: {
              response_feedback['StokFiyatGuncelle3Response']['StokFiyatGuncelle3Result']}")


def save_to_csv(data, filename=""):

    if data:

        keys = set()

        for item in data:

            keys.update(item.keys())

        with open(f"{filename}_data_list.csv", "w", newline='', encoding="utf-8") as csvfile:

            file_writer = csv.DictWriter(csvfile, fieldnames=sorted(keys))

            file_writer.writeheader()

            for d in data:

                file_writer.writerow(d)
