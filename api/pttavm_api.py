import json
import os
import requests
import xmltodict


username = os.environ.get('PTTAVMUSERNAME')
password = os.environ.get('PTTAVMPASSWORD')
TedarikciId = os.environ.get('PTTAVMTEDARIKCIID')

def requestData(method: str ='POST', uri: str ='', params: dict ={}, data: list = ''):

    url = "https://ws.pttavm.com:93/service.svc"

    payload = f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
    <soapenv:Header>
        <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <wsse:UsernameToken>
                <wsse:Username>{username}</wsse:Username>
                <wsse:Password>{password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
    {data}
    </soapenv:Body>
</soapenv:Envelope>"""

    headers = {
  'Content-Type': 'text/xml; charset=utf-8',
  'SOAPAction': f'http://tempuri.org/IService/{uri}'
}

    response = requests.request(method, url, headers=headers, params=params, data=payload)

    if response.status_code == 200:

        # response_data = json.loads(response.text)

        return response

    else:

        print(f'PTTAVM request has failed || Reason: {response.text}')

        return None

def formatData(response):

    # Access the response elements
    raw_xml = response.text

    # Parse the XML response into a dictionary using xmltodict library.
    response_json = xmltodict.parse(raw_xml)

    # Access the response elements using the response_namespace and list_name variables.
    body_content = response_json['s:Envelope']['s:Body']
    
    return body_content
    
def getPTTAVM_procuctskData(everyProduct: bool = False):

    api_call = requestData(uri='StokKontrolListesi')
    products = []

    if api_call.status_code == 200:

        products_list = formatData(api_call)['StokKontrolListesiResponse']['StokKontrolListesiResult']['a:StokKontrolDetay']

        if not everyProduct:

            for product in products_list:

                products.append({'id': product['a:Barkod'],
                                 'sku': product['a:UrunKodu'],
                                 'qty': product['a:Miktar']})
                
            print('PTTAVM products data request is successful. Response: ', api_call.reason)
            
            return products
        
        else:

            return products_list

def pttavm_updateData(product):

    sku = product['sku']
    item_id = product['id']
    qty = product['qty']

    update_payload = f"""<tem:StokFiyatGuncelle3>
            <tem:ShopId>{TedarikciId}</tem:ShopId>
            <tem:Barkod>{item_id}</tem:Barkod>
            <tem:Miktar>{qty}</tem:Miktar>
        </tem:StokFiyatGuncelle3>"""
    
    update_request = requestData(uri='StokFiyatGuncelle3', data=update_payload)

    if update_request.status_code == 200:

        print(f'N11 product with sku: {sku}, New value: {qty}')

    else:

        print(f"Request failure for N11 product {sku} | Response: {update_request}")

pttavm_updateData({'sku': 'AYAKKRK', 'id': 'AYAKKRK', 'qty': 11})