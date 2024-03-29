
from api.amazon_seller_api import spapi_getlistings
from api.n11_api import get_n11_stock_data


pro = spapi_getlistings(True)
print(pro[1])
pass