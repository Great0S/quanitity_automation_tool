import os
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken

api_key = os.getenv("N11_KEY")
api_secret = os.getenv("N11_SECRET")
auth = {"appKey": api_key, "appSecret": api_secret}
wsdl_url = 'https://api.n11.com/ws/ProductService.wsdl'
settings = Settings(
            strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True
        )
client = Client(wsdl=wsdl_url, settings=settings, wsse=UsernameToken(api_key, api_secret))

operation = client.wsdl.services['SaveProduct'].ports['PortName'].operations['OperationName']

# Access and print the input parameters
for name, element in operation.input.body.type.elements:
    print(f"Parameter Name: {name}")
    print(f"Parameter Type: {element.type}")
    print(f"Parameter minOccurs: {element.min_occurs}")
    print(f"Parameter maxOccurs: {element.max_occurs}")
    print()