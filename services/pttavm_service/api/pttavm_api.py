""" The lines `import csv`, `import os`, `import requests`, and `import xmltodict` are importing
 necessary Python libraries/modules for the script to use."""
import csv
import os
import re
import time
import requests
import xmltodict
import logging

class PTTAVMAPI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.username = os.environ.get('PTTAVMUSERNAME')
        self.password = os.environ.get('PTTAVMPASSWORD')
        self.TedarikciId = os.environ.get('PTTAVMTEDARIKCIID')

    def request_data(self, method: str = 'POST', uri: str = '', params: dict = None, data: list = ''):
        """
        The function `requestData` sends a SOAP request to a specific 
        URL with provided parameters and data,
        handling the response accordingly.
        """

        url = "https://ws.pttavm.com:93/service.svc"

        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/" xmlns:ept="http://schemas.datacontract.org/2004/07/ePttAVMService">
        <soapenv:Header>
            <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                <wsse:UsernameToken>
                    <wsse:Username>{self.username}</wsse:Username>
                    <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{self.password}</wsse:Password>
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

            error_response = self.format_data(response)['s:Fault']['faultstring']['#text']

            if not re.search('dakika', error_response):

                return error_response

            time.sleep(2)

    def format_data(self, response):
        """
        The `formatData` function parses an XML response 
        into a dictionary and returns the body content.

        """

        # Access the response elements
        raw_xml = response.text

        # Parse the XML response into a dictionary using xmltodict library.
        response_json = xmltodict.parse(raw_xml)

        # Access the response elements using the response_namespace and list_name variables.
        body_content = response_json['s:Envelope']['s:Body']

        return body_content

    def getpttavm_procuctskdata(self, everyproduct: bool = False, local: bool = False):
        """
        The function `getPTTAVM_procuctskData` retrieves product 
        data from an API and returns a list of
        products with specific details.
        """

        api_call = self.request_data(uri='StokKontrolListesi')
        products = []

        if api_call.status_code == 200:

            products_list = self.format_data(api_call)[
                'StokKontrolListesiResponse']['StokKontrolListesiResult']['a:StokKontrolDetay']

            for product in products_list:

                if not everyproduct:

                    products.append({'id': product['a:Barkod'],
                                     'sku': product['a:UrunKodu'],
                                     'qty': int(product['a:Miktar']),
                                     'price': float(product['a:KDVli'])})

                else:

                    products.append(product)

            self.logger.info(f"""PTTAVM fetched {len(products)} products""")

            return products

        return []

    def pttavm_updatedata(self, product_data: dict):
        """
        The function `pttavm_updateData` updates product data 
        on a platform called PTTAVM by sending a
        request with the provided product information.
        """

        sku = product_data['sku']
        item_id = product_data['id']
        qty = product_data['qty']
        price = product_data['price']
        # price_kdvsiz = product['price'] - product['price'] * 0.1

        update_payload = f"""
        <tem:StokFiyatGuncelle3>
            <tem:item>
                <ept:Aktif>true</ept:Aktif>
                <ept:Barkod>{item_id}</ept:Barkod>
                <ept:KDVOran>10</ept:KDVOran>
                <ept:KDVli>{price}</ept:KDVli>
                <ept:KDVsiz>0</ept:KDVsiz>
                <ept:Miktar>{qty}</ept:Miktar>
                <ept:ShopId>{self.TedarikciId}</ept:ShopId>
            </tem:item>
        </tem:StokFiyatGuncelle3>"""

        update_request = self.request_data(uri='StokFiyatGuncelle3', data=update_payload)

        if isinstance(update_request, requests.Response):

            responses_msg = self.format_data(update_request)[
                'StokFiyatGuncelle3Response']['StokFiyatGuncelle3Result']

            self.logger.info(f"""Product success: {
                responses_msg['a:Success']}, sku: {sku}, New stock: {qty}, New price: {price}""")

        else:

            self.logger.error(f"""Request failure for product {sku} | Response: {
                update_request}""")

    def save_to_csv(self, data, filename=""):
        """
        The function `save_to_csv` takes a list of dictionaries, 
        extracts keys from the dictionaries, and
        writes the data to a CSV file with the specified filename.

        :param data: The `data` parameter in the `save_to_csv` 
        function is expected to be a list of
        dictionaries. Each dictionary in the list represents a 
        row of data to be written to the CSV file
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
