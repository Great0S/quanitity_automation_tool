import requests
import lxml.etree as ET

url = "https://api.n11.com/ws/ProductService/"
current_page = 0

# Authenticate with your appKey and appSecret
headers = {"Content-Type": "text/xml; charset=utf-8"}
payload = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:GetProductListRequest>
            <auth>
                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>
                <appSecret>BmDozr9ORpNlhjNp</appSecret>
            </auth>
            <pagingData>
                <currentPage>0</currentPage>
                <pageSize>100</pageSize>
            </pagingData>
        </sch:GetProductListRequest>
    </soapenv:Body>
</soapenv:Envelope>
"""


# Call the DetailedOrderList operation
api_call = requests.post(url, headers=headers, data=payload)

# Access the response elements
def assign_vars(response):
    raw_xml = response.text
    tree = ET.fromstring(raw_xml)
    namespaces = {'ns3': 'http://www.n11.com/ws/schemas'}
    products_raw_response = tree.find(
        './/ns3:GetProductListResponse', namespaces)
    products_list = products_raw_response.find('products').findall('product')
    products_pages = products_raw_response.find(
        'pagingData').find('pageCount').text
    return products_list, products_pages


if api_call.status_code == 200:
    products_list, products_pages = assign_vars(api_call)

    # Process all pages found
    while current_page < int(products_pages):

        if products_list is not None:

            # Process the product data
            for product in products_list:

                # Access order details using order.id, order.createDate, etc.
                product_id = product.find('productSellerCode').text
                product_qty = product.find('stockItems').find(
                    'stockItem').find('quantity').text
                raw_elements_strings = {'kod': product.find('id').text,'id': product_id, 'stok': product_qty}
                # raw_elements = ET.fromstringlist(raw_elements_strings)
                print(raw_elements_strings)
        else:
            print("No products found in the response.")

        current_page += 1
        payload_dump = payload.replace(
            f"<currentPage>0</currentPage>",
            f"<currentPage>{str(current_page)}</currentPage>",
        )
        api_call_loop = requests.post(url, headers=headers, data=payload_dump)
        products_list, products_pages = assign_vars(api_call_loop)
else:
    print("Error:", api_call.text)

print("SOAP Request Successful. Response:", api_call.reason)
