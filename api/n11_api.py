from zeep import Client, Settings
from lxml import etree
import lxml.etree as ET

parser = ET.XMLParser()  # Instantiate the parser


url = "https://api.n11.com/ws/OrderService.wsdl"
settings = Settings(strict=False, xml_huge_tree=True)
client = Client(url, settings=settings)

# auth = {'appKey': 'b5f2329d-d92f-4bb9-8d1b-3badedf77762',
#         'appSecret': 'BmDozr9ORpNlhjNp'}
# searchData = {'productId': '', 'status': 'Completed',
#               'buyerName': '',
#               'orderNumber': '',
#               'productSellerCode': '',
#               'recipient': '',
#               'sameDayDelivery': '',
#               'period': {'startDate': '',
#                          'endDate': ''},
#               'sortForUpdateDate': True}
# pagingData = {'currentPage': 0,
#               'pageSize': 100,
#               'totalCount': '',
#               'pageCount': ''}

headers = {"Content-Type": "text/xml; charset=utf-8"}

# Authenticate with your appKey and appSecret
auth = client.get_type('ns0:Authentication')(appKey='b5f2329d-d92f-4bb9-8d1b-3badedf77762', appSecret='BmDozr9ORpNlhjNp')

# Construct search and paging data
search_data = client.get_type('ns0:OrderDataListRequest')(
    productId='',  # Adjust as needed
    status='Completed',  # Adjust as needed
    buyerName = '',
    orderNumber = '',
    productSellerCode = '',
    recipient = '',
    sameDayDelivery = '',
    period=client.get_type('ns0:OrderSearchPeriod')(startDate='', endDate=''),  # Use client.get_type for nested types,
    sortForUpdateDate = True
)
paging_data = client.get_type('ns0:PagingData')(currentPage=1, pageSize=100)

# Call the DetailedOrderList operation
# response = client.service.DetailedOrderList(auth=auth, searchData=search_data, pagingData=paging_data)

# # Access the response elements
# if response.result.status == 'success':
#     if response.orderList is not None:
#         order_list = response.orderList.order
#     else:
#         print("No orders found in the response.")
#     # paging_info = response.pagingData
#     # Process the order list and paging information
# else:
#     print("Error:", response.result.errorMessage)

try:
    response = client.bind()
    response = client.service.OrderList(auth=auth,
                                            searchData=search_data,
                                            pagingData=paging_data)
    tree = etree.fromstring(response, parser)
    order_list = response['orderList']

    
    print("DOne")

except Exception as Ex:
    print(f"Request error {Ex}")
print("SOAP Request Successful. Response:", response)
