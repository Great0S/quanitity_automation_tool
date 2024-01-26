import csv
from functools import reduce
import operator
import time
import requests
import xmltodict
from bs4 import BeautifulSoup


url = "https://api.n11.com/ws/orderService/"
# start_date = "01/01/2018"
# end_date = "01/01/2024"
current_page = 0
payload_temp = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:DetailedOrderListRequest>
            <auth>
                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>
                <appSecret>BmDozr9ORpNlhjNp</appSecret>
            </auth>
            <searchData>
                <productId></productId>
                <status></status>
                <buyerName></buyerName>
                <orderNumber></orderNumber>
                <productSellerCode></productSellerCode>
                <recipient></recipient>
                <sameDayDelivery></sameDayDelivery>
                <period>
                    <startDate></startDate>
                    <endDate></endDate>
                </period>
                <sortForUpdateDate>true</sortForUpdateDate>
            </searchData>
            <pagingData>
                <currentPage>{current_page}</currentPage>
                <pageSize>100</pageSize>
                <totalCount></totalCount>
                <pageCount></pageCount>
            </pagingData>
        </sch:DetailedOrderListRequest>
    </soapenv:Body>
</soapenv:Envelope>"""
headers = {"Content-Type": "text/xml; charset=utf-8"}

ordersLST = []
response = requests.request("POST", url, headers=headers, data=payload_temp)
response_data = BeautifulSoup(
    response.text, "xml").contents[0].contents[1].contents[0]
total_pages = int(response_data.contents[1].contents[3].text)


def data_request(url, headers, payload):
    time.sleep(5)
    req_response = requests.request("POST", url, headers=headers, data=payload)
    if req_response.status_code == 200:
        return req_response
    elif (
        req_response.text
        == "failureSELLER_API.notAvailableForUpdateForFiveSecondsdetailedOrders belli süre aralıklarıyla güncellenebilirSELLER_API"
    ):
        total_pages += 1
        time.sleep(5)
        return "retry"
    else:
        return None


while current_page < total_pages:
    status = response_data.contents[0].text
    if status == "success":
        xml_data = xmltodict.parse(str(response_data.contents[2]))
        json_data = xml_data["orderList"]["order"]

        for n in range(len(json_data)):
            item = json_data[n]["orderItemList"]["orderItem"]
            if len(json_data[n]["orderItemList"]["orderItem"]) >= 20:
                item_name = item["productName"]
                item_date = item["updatedDate"]
                total_product = qty = int(item["quantity"])
                unit_price = item["sellerInvoiceAmount"]
                product_code = item["productSellerCode"]
            else:
                item_name = []
                qty = []
                item_date = item[0]["updatedDate"]
                unit_price = []
                product_code = []

                for t in range(len(item)):
                    item_name.append(item[t]["productName"])
                    qty.append(float(item[t]["quantity"]))
                    unit_price.append(item[t]["sellerInvoiceAmount"])
                    product_code.append(item[t]["productSellerCode"])
                total_product = reduce(operator.add, qty)

            price = float(json_data[n]["totalAmount"])

            print(
                f"{item_date} - {item_name} + {unit_price} x {total_product} = {price}"
            )
            if isinstance(item_name, list):
                for l in range(len(item_name)):
                    ordersLST.append(
                        {
                            "product": item_name[l],
                            "code": product_code[l],
                            "qty": qty[l],
                            "price": unit_price[l],
                            "date": item_date,
                        }
                    )
            else:
                ordersLST.append(
                    {
                        "product": item_name,
                        "code": product_code,
                        "qty": total_product,
                        "price": price,
                        "date": item_date,
                    }
                )
        current_page += 1
        payload = payload_temp.replace(
            f"<currentPage>0</currentPage>",
            f"<currentPage>{str(current_page)}</currentPage>",
        )
        response = data_request(url, headers, payload)
        if response == "retry":
            continue
        elif response is not None:
            response_data = (
                BeautifulSoup(
                    response.text, "xml").contents[0].contents[1].contents[0]
            )


# Method to save scraped data to a csv file
def save_data(ordersLST):
    columns = ["product", "code", "qty", "price", "date"]
    with open(
        "N11_satis_raporu_tum.csv", mode="w", newline="", encoding="utf-8"
    ) as file:
        data_convert = csv.DictWriter(file, fieldnames=columns)

        # Write headers
        data_convert.writeheader()

        # Write rows
        data_convert.writerows(ordersLST)


save_data(ordersLST)

print("\n\n\nData has been save to N11_satis_raporu_tum.csv successfully!")
