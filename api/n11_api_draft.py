from base64 import b64encode
import requests
from zeep import Client, Settings, Transport
from lxml import etree
import lxml.etree as ET

# parser = ET.XMLParser()  # Instantiate the parser


# url = "https://api.n11.com/ws/OrderService.wsdl"
# wsdl_url = url

# # Create a Zeep client with a custom transport to handle cookies
# transport = Transport(session=requests.Session())
# client = Client(wsdl_url, transport=transport)

# # Build the request payload
# request_payload = {
#     'auth': {
#         'appKey': 'b5f2329d-d92f-4bb9-8d1b-3badedf77762',
#         'appSecret': 'BmDozr9ORpNlhjNp',
#     },
#     'searchData': {
#         'productId': '',
#         'status': 'Completed',
#         'buyerName': '',
#         'orderNumber': '',
#         'productSellerCode': '',
#         'recipient': '',
#         'sameDayDelivery': '',
#         'period': {
#             'startDate': '',
#             'endDate': '',
#         },
#         'sortForUpdateDate': True,
#     },
#     'pagingData': {
#         'currentPage': 0,
#         'pageSize': 100,
#         'totalCount': '',
#         'pageCount': '',
#     },
# }

# # Make the SOAP request
# try:
#     response = client.service.GetOrderList(**request_payload)
#     print("SOAP Request Successful. Response:", response)
# except Exception as e:
#     print("SOAP Request Failed. Exception:", e)



# wsdl_url = "https://api.n11.com/ws/OrderService.wsdl"

# client = Client(wsdl_url)

# # Set up authentication headers
# headers = {
#     'Content-Type': 'text/xml; charset=utf-8',  # Ensure correct content type
#     'Authorization': f"Basic {b64encode(b'b5f2329d-d92f-4bb9-8d1b-3badedf77762:BmDozr9ORpNlhjNp').decode('utf-8')}"  # Base64-encoded credentials
# }

# # Create a custom transport for authentication
# transport = Transport(session=requests.Session())
# transport.session.headers.update(headers)

# # Bind the client to the transport
# client.transport = transport

# # Create the request data
# auth = client.get_type('ns0:Authentication')(appKey='b5f2329d-d92f-4bb9-8d1b-3badedf77762', appSecret='BmDozr9ORpNlhjNp')

# search_data = client.get_type('ns0:DetailedOrderListRequest')(
#     productId="",
#     status="Completed",
#     buyerName = '',
#     orderNumber = '',
#     productSellerCode = '',
#     recipient = '',
#     sameDayDelivery = '',
#     period=client.get_type('ns0:OrderSearchPeriod')(startDate='', endDate=''),  # Use client.get_type for nested types,
#     sortForUpdateDate = True,
#     pagingData=client.get_type('ns0:PagingData')(
#         currentPage=0,
#         pageSize=100
#     )
# )

# # Call the service
# response = client.service.DetailedOrderList(auth=auth, searchData=search_data)

# # Access the order list (assuming it's in the response)
# order_list = response.orderList

# # Process the order data as needed
# for order in order_list.order:
#     # Access order details using order.id, order.createDate, etc.
#     print(order.id, order.createDate)  # Example usage

# settings = Settings(strict=False, xml_huge_tree=True)
# client = Client(url, settings=settings)

# # auth = {'appKey': 'b5f2329d-d92f-4bb9-8d1b-3badedf77762',
# #         'appSecret': 'BmDozr9ORpNlhjNp'}
# # searchData = {'productId': '', 'status': 'Completed',
# #               'buyerName': '',
# #               'orderNumber': '',
# #               'productSellerCode': '',
# #               'recipient': '',
# #               'sameDayDelivery': '',
# #               'period': {'startDate': '',
# #                          'endDate': ''},
# #               'sortForUpdateDate': True}
# # pagingData = {'currentPage': 0,
# #               'pageSize': 100,
# #               'totalCount': '',
# #               'pageCount': ''}

# headers = {"Content-Type": "text/xml; charset=utf-8"}

# # Authenticate with your appKey and appSecret
# auth = client.get_type('ns0:Authentication')(appKey='b5f2329d-d92f-4bb9-8d1b-3badedf77762', appSecret='BmDozr9ORpNlhjNp')

# # Construct search and paging data
# search_data = client.get_type('ns0:OrderDataListRequest')(
#     productId='',  # Adjust as needed
#     status='Completed',  # Adjust as needed
#     buyerName = '',
#     orderNumber = '',
#     productSellerCode = '',
#     recipient = '',
#     sameDayDelivery = '',
#     period=client.get_type('ns0:OrderSearchPeriod')(startDate='', endDate=''),  # Use client.get_type for nested types,
#     sortForUpdateDate = True
# )
# paging_data = client.get_type('ns0:PagingData')(currentPage=1, pageSize=100)

# # Call the DetailedOrderList operation
# # response = client.service.DetailedOrderList(auth=auth, searchData=search_data, pagingData=paging_data)

# # # Access the response elements
# # if response.result.status == 'success':
# #     if response.orderList is not None:
# #         order_list = response.orderList.order
# #     else:
# #         print("No orders found in the response.")
# #     # paging_info = response.pagingData
# #     # Process the order list and paging information
# # else:
# #     print("Error:", response.result.errorMessage)

# try:
#     responseb = client.bind()
#     print(responseb.DetailedOrderList(auth=auth,
#                                             searchData=search_data,
#                                             pagingData=paging_data))
#     response = client.service.OrderList(auth=auth,
#                                             searchData=search_data,
#                                             pagingData=paging_data)
#     tree = etree.fromstring(response, parser)
#     order_list = response['orderList']

    
#     print("DOne")

# except Exception as Ex:
#     print(f"Request error {Ex}")

import requests

url = "https://api.n11.com/ws/orderService/"

payload = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:sch=\"http://www.n11.com/ws/schemas\">\\n    \n    <soapenv:Header/>\\n\n    <soapenv:Body>\\n        \n        <sch:DetailedOrderListRequest>\\n            \n            <auth>\\n                \n                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>\\n\n                <appSecret>BmDozr9ORpNlhjNp</appSecret>\\n\n            </auth>\\n\n            <searchData>\\n                \n                <productId></productId>\\n\n                <status>Completed</status>\\n\n                <buyerName></buyerName>\\n\n                <orderNumber></orderNumber>\\n\n                <productSellerCode></productSellerCode>\\n\n                <recipient></recipient>\\n\n                <sameDayDelivery></sameDayDelivery>\\n\n                <period>\\n                    \n                    <startDate></startDate>\\n\n                    <endDate></endDate>\\n\n                </period>\\n\n                <sortForUpdateDate>true</sortForUpdateDate>\\n\n            </searchData>\\n\n            <pagingData>\\n                \n                <currentPage>0</currentPage>\\n\n                <pageSize>100</pageSize>\\n\n                <totalCount></totalCount>\\n\n                <pageCount></pageCount>\\n\n            </pagingData>\\n\n        </sch:DetailedOrderListRequest>\\n\n    </soapenv:Body>\\n\n</soapenv:Envelope>"
headers = {
  'Content-Type': 'text/xml, text/html;',
  'Cookie': 'e2f9affc532f36c6aec1c8bd433e2a59=1b5b2500db0aa596b2d05492f2e43fb4'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)

print("SOAP Request Successful. Response:", response)
