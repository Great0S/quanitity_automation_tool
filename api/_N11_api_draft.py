import csv
from datetime import datetime
from functools import reduce
import operator
import time
import requests
import xmltodict
from bs4 import BeautifulSoup


url = "https://api.n11.com/ws/ProductService/"
current_page = 0
payload_temp = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sch="http://www.n11.com/ws/schemas">
    <soapenv:Header/>
    <soapenv:Body>
        <sch:GetProductListRequest>
            <auth>
                <appKey>b5f2329d-d92f-4bb9-8d1b-3badedf77762</appKey>
                <appSecret>BmDozr9ORpNlhjNp</appSecret>
            </auth>
            <pagingData>
                <currentPage>{current_page}</currentPage>
                <pageSize>100</pageSize>
            </pagingData>
        </sch:GetProductListRequest>
    </soapenv:Body>
</soapenv:Envelope>"""
headers = {"Content-Type": "text/xml; charset=utf-8"}

ordersLST = []
product_data = []
# response = requests.request("POST", url, headers=headers, data=payload_temp)
# response_data = BeautifulSoup(
#     response.text, "xml").contents[0].contents[1].contents[0]
# total_pages = int(response_data.contents[1].contents[3].text)


def data_request(payload_data):
    time.sleep(5)

    # if startDate and endDate is not None:
    #     payload = payload_data.replace(
    #         f"<startDate></startDate>",
    #         f"<startDate>{str(startDate)}</startDate>"
    #     )
    #     payload = payload.replace(
    #         f"<endDate></endDate>",
    #         f"<endDate>{str(endDate)}</endDate>"
    #     )
    # else:
    #     payload = payload_data
    req_response = requests.request(
        "POST", url, headers=headers, data=payload_data)
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


def item_data_extract(ordersLST, json_data, iterator, item):
    if len(json_data[iterator]["orderItemList"]["orderItem"]) >= 20:
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

    price = float(json_data[iterator]["totalAmount"])

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


def extract_qty(product_data, json_data):

    date_format = "%d/%m/%Y"

    for n in range(len(json_data)):
        item = json_data[n]["orderItemList"]["orderItem"]

        if len(item) < 20:
            for item_data in range(len(item)):
                # Convert the date string to a datetime object
                date_obj = datetime.strptime(
                    item[item_data]['approvedDate'], date_format).date()

                product_data.append({'productId': item[item_data]['productSellerCode'], 'qty': int(
                    item[item_data]['quantity']), 'date': date_obj})
        else:
            date_obj = datetime.strptime(
                item['approvedDate'], date_format).date()
            product_data.append({'productId': item['productSellerCode'], 'qty': int(
                item['quantity']), 'date': date_obj})


def get_details():
    current_page = 0
    response = data_request(payload_temp)
    response_data = BeautifulSoup(
        response.text, "xml").contents[0].contents[1].contents[0]
    total_pages = int(response_data.contents[2].contents[2].text)

    while current_page < total_pages:
        status = response_data.contents[0].text
        if status == "success":
            xml_data = xmltodict.parse(str(response_data.contents[2]))
            json_data = xml_data["orderList"]["order"]

        # Define the format of the date string
            extract_qty(product_data, json_data)

        # item_data_extract(ordersLST, json_data, n, item)
            current_page += 1
            payload = payload_temp.replace(
                f"<currentPage>0</currentPage>",
                f"<currentPage>{str(current_page)}</currentPage>",
            )
            response = data_request(payload)
            if response == "retry":
                continue
            elif response is not None:
                response_data = (
                    BeautifulSoup(
                        response.text, "xml").contents[0].contents[1].contents[0]
                )
            return product_data

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

    print("\n\n\nData has been save to N11_satis_raporu_tum.csv successfully!")
