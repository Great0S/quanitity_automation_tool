import requests
import json

url = "https://sellingpartnerapi-eu.amazon.com/listings/2021-08-01/items/A2Z045PNNSBEVP/MER4060?marketplaceIds=A33AVAJ2PDY3EV&issueLocale=en_US&mode=VALIDATION_PREVIEW"

payload = json.dumps({
    "productType":"HOME_BED_AND_BATH",
    "patches":[
        {
            "op": "replace",
            "path": "/attributes/fulfillment_availability",
            "value": [
                {
                     "fulfillment_channel_code": "DEFAULT",
                     "quantity": 880,
                     "marketplace_id": "A33AVAJ2PDY3EV"
                }
            ]
        }
    ]
})
headers = {
    'x-amz-access-token': 'Atza|IwEBIMqaM3eMw7QrTyGT5iAxA7a0ZUMVbiuoKIzUWIsM8QxpO9-Q7MDG82frqt5WEPaJp8i3y8sI2SyQ54B2T61Y4OgCvvVApmjHf0Rk_YXzQkihP4p0ekiN6xc5azYRNd4nQoa5Ec2bi894xxnmwlTOueeAXVL5xSev44pF-XdjJ3C-YYyetWCgwjhv1WvfJNB6o-Nwm6JDn7qAmY6m6ZE0R0XGueeB_yEG_BVPgoWOcwbb4ithFXK5zUvSbIX0kbsas2S0KIXvK1FqgDmqWuBcJFBUZ0qsAfyocIU3Q77rb-45AQYI9A2lRpVsgIIMgFsl44wyYQShQM4IqwgTUm8CbqQLr5x3gIR1ylcafw24Hlgnww',
    'Content-Type': 'application/json'
}

response = requests.request("PATCH", url, headers=headers, data=payload)

print(response.text)
