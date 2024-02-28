import datetime
import os
from sp_api.api import Catalog, Reports, Orders
from sp_api.base import SellingApiException, Marketplaces
from sp_api.base.reportTypes import ReportType
from sp_api.util import throttle_retry, load_all_pages
from simple_dotenv import GetEnv

credentials=dict(
        refresh_token=str(GetEnv('SP_API_REFRESH_TOKEN')),
        lwa_app_id=str(GetEnv('LWA_APP_ID')),
        lwa_client_secret=str(GetEnv('LWA_CLIENT_SECRET'))
    )
market = str(GetEnv('AMAZONTURKEYMARKETID'))
#wd = Orders(credentials=credentials, marketplace=[os.environ.get('SP_API_DEFAULT_MARKETPLACE')]).get_orders(CreatedAfter=("2019-10-07T17:58:48.017Z"))

@throttle_retry(rate=0.0167, tries=10, delay=5)
@load_all_pages(next_token_param='next_token', use_rate_limit_header=True)
def load_all_orders(**kwargs):
    """
    a generator function to return all pages, obtained by NextToken
    """
    return Orders().get_orders(**kwargs)

orders = []

for page in load_all_orders(LastUpdatedAfter=("2019-10-07T17:58:48.017Z")):
    for order in page.payload.get('Orders'):
        orders.append(order)
        print(order['AmazonOrderId'])
print(len(orders))