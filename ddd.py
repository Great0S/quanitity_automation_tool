# import logging.config
# from zeep import Client, exceptions, xsd

# # Enable verbose logging
# logging.config.dictConfig({
#     'version': 1,
#     'formatters': {
#         'verbose': {
#             'format': '%(name)s: %(message)s'
#         }
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#             'formatter': 'verbose',
#         },
#     },
#     'loggers': {
#         'zeep': {
#             'level': 'DEBUG',
#             'handlers': ['console'],
#         },
#     }
# })

# wsdl = 'https://api.n11.com/ws/CategoryService.wsdl'
# client = Client(wsdl)

# auth = {
#     'appKey': 'eadbc7a0-60ee-4870-8d5c-8c1821eb1f40',
#     'appSecret': 'LRyus24CajHNV6IH'
# }
# category_id = 1002841

# try:
#     response = client.service.GetSubCategories(auth=auth, categoryId=category_id, lastModifiedDate=xsd.SkipValue)

#     # Print the response
#     print(response)

#     if response.result.status == 'success':
#         print(f"Category ID: {response.category.id}")
#         print(f"Category Name: {response.category.name}")
#         if hasattr(response, 'subCategoryList') and response.subCategoryList:
#             for subcategory in response.subCategoryList.subCategory:
#                 print(f"Subcategory ID: {subcategory.id}")
#                 print(f"Subcategory Name: {subcategory.name}")
#     else:
#         print(f"Error: {response.result.errorMessage} (Code: {response.result.errorCode})")
# except exceptions.Fault as fault:
#     print(f"SOAP Fault: {fault}")


from zeep import Client
from lxml import etree

# Initialize the client
client = Client('https://api.n11.com/ws/CategoryService.wsdl')

# Create the request message
message = client.create_message(
    client.service,
    'GetSubCategories',
    auth={
        'appKey': 'eadbc7a0-60ee-4870-8d5c-8c1821eb1f40',
        'appSecret': 'LRyus24CajHNV6IH'
    },
    categoryId=1002841
)

# Convert the message to an XML element
xml_message = etree.ElementTree(message)

# Find and remove the lastModifiedDate element if it exists
for elem in xml_message.xpath('//lastModifiedDate'):
    elem.getparent().remove(elem)

# Send the modified request
response = client.transport.post_xml(
    'https://api.n11.com/ws/CategoryService/',
    etree.tostring(xml_message)
)

print(response.content)
