# import json
# import os
# import requests
# from sp_api.api import Orders
# from sp_api.api import Reports
# from sp_api.api import DataKiosk
# from sp_api.api import ListingsItems, ProductTypeDefinitions, CatalogItems, CatalogItemsVersion
# from sp_api.base import SellingApiException
# from sp_api.base.reportTypes import ReportType
# from datetime import datetime, timedelta

# # DATA KIOSK API
# client = DataKiosk()

# # orders API
# # try:
# #     res = Orders().get_orders(CreatedAfter=(
# #         datetime.utcnow() - timedelta(days=7)).isoformat())
# #     print(res.payload)  # json data
# # except SellingApiException as ex:
# #     print(ex)


# sid = os.getenv("AMAZONSELLERACCOUNTID")


# defi21 = CatalogItems()
# defi21.version = CatalogItemsVersion.V_2022_04_01
# defi212 = defi21.search_catalog_items(marketplaceIds=['A33AVAJ2PDY3EV'],
#                                              keywords=['paspas', 'halı', 'maket', 'kapı','merdiven'],
#                                              keywordsLocale='tr_TR',
#                                              brandNames='Stepmat,Myfloor',
#                                              includedData='attributes,identifiers,images,productTypes,summaries,dimensions,classifications',
#                                              locale='tr_TR')
# # defi = ProductTypeDefinitions().search_definitions_product_types(keywords='Halı',marketplaceIds=['A33AVAJ2PDY3EV'])
# # defi2 = ProductTypeDefinitions().get_definitions_product_type(productType='RUG',marketplaceIds=['A33AVAJ2PDY3EV'])
# # # print(defi.payload['metaSchema']['link']['resource'])
# # meta = requests.get(defi2.payload['schema']['link']['resource'])

# with open("amazon_rug_attrs.json", "r", encoding="utf-8") as meta:
#     jdata = json.load(meta)

# meta_data = jdata
# browseNodes = {"RUG": "13028044031", "HOME_BED_AND_BATH": "13028044031"}

# bod = {
#     "productType": "RUG",
#     "requirements": "LISTING",
#     "attributes": {
#         "item_name": [{"value": "Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası"}],
#         "brand": [{"value": "Stepmat"}],
#         "supplier_declared_has_product_identifier_exemption": [{"value": True}],
#         "recommended_browse_nodes": [{"value": "13028044031"}],
#         "bullet_point": [
#             {
#                 "language_tag": "tr_TR",
#                 "value": "Premium Kalite İplik ile Üretilmiş Üst Yüzey",
#                 "marketplace_id": "A33AVAJ2PDY3EV",
#             },
#             {
#                 "language_tag": "tr_TR",
#                 "value": "Merdivenlerden Kaymaz , Ahşap Beton ve Merdivende Kullanılabilir.",
#                 "marketplace_id": "A33AVAJ2PDY3EV",
#             },
#             {
#                 "language_tag": "tr_TR",
#                 "value": "Uygulaması ve Temizliği Kolaydır.",
#                 "marketplace_id": "A33AVAJ2PDY3EV",
#             },
#             {
#                 "language_tag": "tr_TR",
#                 "value": "Adet Olarak Satılır. Boyutları : 65 x 25 cm.",
#                 "marketplace_id": "A33AVAJ2PDY3EV",
#             },
#             {
#                 "language_tag": "tr_TR",
#                 "value": "Türkiye'de Üretilmiştir.",
#                 "marketplace_id": "A33AVAJ2PDY3EV",
#             },
#         ],
#         "condition_type": [{"value": "new_new"}],
#         "fulfillment_availability": [
#             {"fulfillment_channel_code": "DEFAULT", "quantity": 100}
#         ],
#         "gift_options": [{"can_be_messaged": "false", "can_be_wrapped": "false"}],
#         "generic_keyword": [
#             {"value": "Bukle,Halıdan,Ekonomik,Basamak,ve,Merdiven,Paspası"}
#         ],
#         "list_price": [{"currency": "TRY", "value_with_tax": "299"}],
#         "manufacturer": [{"value": "Eman Halıcılık San. Ve Tic. Ltd. Şti."}],
#         "material": [{"value": "Polyester"}],
#         "main_product_image_locator": [
#             {
#                 "media_location": "https://cdn.dsmcdn.com/ty1440/product/media/images/prod/QC/20240726/12/208eae59-155e-3a33-8a4b-269689aee1f4/1_org_zoom.jpg"
#             }
#         ],
#         "other_product_image_locator_1": [
#             {
#                 "media_location": "https://cdn.dsmcdn.com/ty1441/product/media/images/prod/QC/20240726/12/140f9130-514e-38f2-a982-0a4059b349e7/1_org_zoom.jpg"
#             }
#         ],
#         "other_product_image_locator_2": [
#             {
#                 "media_location": "https://cdn.dsmcdn.com/ty1440/product/media/images/prod/QC/20240726/12/c721aa22-db74-35eb-ae7a-cf0b18450f10/1_org_zoom.jpg"
#             }
#         ],
#         "other_product_image_locator_3": [
#             {
#                 "media_location": "https://cdn.dsmcdn.com/ty1442/product/media/images/prod/QC/20240726/12/a987d1a6-19b3-3dbb-9929-e9ec78ffec6f/1_org_zoom.jpg"
#             }
#         ],
#         "other_product_image_locator_4": [
#             {
#                 "media_location": "https://cdn.dsmcdn.com/ty1440/product/media/images/prod/QC/20240726/12/a5e6e0b9-f0dc-3253-a3a1-ccf8cf72ea7f/1_org_zoom.jpg"
#             }
#         ],
#         "model_number": [{"value": "EKOKARE"}],
#         "number_of_items": [{"value": 1}],
#         "color": [{"value": "Gri"}],
#         "size": [{"value": "65 x 25 cm"}],
#         "special_feature": [{"value": "Kaymaz"}],
#         "style": [{"value": "Klasik"}],
#         "part_number": [{"value": "EKOKARE"}],
#         "pattern": [{"value": "Düz"}],
#         "product_description": [
#             {
#                 "value": "Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası Evdeki merdivenlerinizi güzelleştirmek ve güvenliğini artırmak için Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası tam da ihtiyacınız olan ürün! Bu paspas, premium kalite iplik kullanılarak üretilmiştir ve üst yüzeyi sayesinde merdivenlerinizde kaymaz bir yüzey sağlar. Ahşap, beton ve mermer merdivenlerde rahatlıkla kullanabilirsiniz. Ayrıca,6 mm hav yüksekliği sayesinde ayaklarınızı yumuşak bir zeminde hissedeceksiniz. Ürün Özellikleri: Malzeme: Premium kalite iplik ; Boyutlar: 25 cm x 65 cm ; Kullanım Alanları: Merdivenler, basamaklar, koridorlar ve daha fazlası ; Temizlik Kolaylığı: Sadece silerek temizlenebilir ; Türkiye Üretimi: Güvenilir ve kaliteli bir ürün ; Bu paspas, uygulaması ve kullanımı son derece kolaydır. Adet olarak satıldığı için ihtiyacınıza göre sipariş verebilirsiniz. Evdeki merdivenlerinizi daha estetik ve güvenli hale getirmek için hemen bu ürünü sepetinize ekleyin!"
#             }
#         ],
#         "product_site_launch_date": [{"value": "2022-06-15T07:41:20.632Z"}],
#         "pile_height": [{"value": "Düşük Hav"}],
#         "purchasable_offer": [
#             {"currency": "TRY", "our_price": [
#                 {"schedule": [{"value_with_tax": 299}]}]}
#         ],
#         "included_components": [
#             {"value": "Tek adet Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası"}
#         ],
#         "item_dimensions": [
#             {
#                 "length": {"value": "5", "unit": "millimeters"},
#                 "width": {"value": "65", "unit": "centimeters"},
#                 "height": {"value": "25", "unit": "centimeters"},
#             }
#         ],
#         "item_shape": [{"value": "Dikdörtgen"}],
#         "item_thickness": [{"decimal_value": "5", "unit": "millimeters"}],
#         "item_length_width": [
#             {
#                 "length": {"unit": "centimeters", "value": 65.0},
#                 "width": {"unit": "centimeters", "value": 25.0},
#             }
#         ],
#         "country_of_origin": [{"value": "TR"}],
#         "rug_form_type": [{"value": "doormat"}],
#     },
#     "offers": [
#         {
#             "offerType": "B2C",
#             "price": {
#                 "currency": "TRY",
#                 "currencyCode": "TRY",
#                 "amount": 299
#             }
#         }
#     ]
# }
# new_ui = ListingsItems().put_listings_item(
#     sellerId=sid,
#     sku="EKOKAREACGRİ2",
#     marketplaceIds=["A33AVAJ2PDY3EV"],
#     body=bod,
#     # mode="VALIDATION_PREVIEW",
# )
# print(new_ui.payload["status"])
# # # Orders(restricted_data_token='<token>').get_orders(CreatedAfter=(datetime.utcnow() - timedelta(days=7)).isoformat())

# # # or use the shortcut
# # orders = Orders().get_orders(
# #     RestrictedResources=['buyerInfo', 'shippingAddress'],
# #     LastUpdatedAfter=(datetime.utcnow() - timedelta(days=1)).isoformat()
# # )


# # import json

# # amzn_attrs = {}
# # attrss = {}
# # temp_attr = {}


# # with open('amazonRUGattrs.json', 'r', encoding='utf-8') as attrFile:
# #     amzn_attrs = json.load(attrFile)

# # attrsproperties = amzn_attrs['properties']

# # for amznAttr in attrsproperties:

# #     sub_attrs = attrsproperties[amznAttr]
# #     if amznAttr == 'color':

# #         pass

# #     for item_attr in sub_attrs:

# #         lower_sub_attrs = sub_attrs['items']

# #         lower_sub_attrs_props = lower_sub_attrs['properties']
# #         temp_attr[amznAttr] = {}

# #         for property_item in lower_sub_attrs_props:

# #             temp_attr[amznAttr][property_item] = {}

# #             if 'examples' in lower_sub_attrs_props[property_item]:
# #                 temp_attr[amznAttr][property_item] =lower_sub_attrs_props[property_item].get(['examples'][0], None)

# #             else:

# #                 if 'items' in lower_sub_attrs_props[property_item]:
# #                     lower_prop_items = lower_sub_attrs_props[property_item]['items']

# #                     if 'required' in lower_prop_items:
# #                         for objs in lower_prop_items['required']:

# #                             temp_attr[amznAttr][property_item][objs] ={}

# #                             if 'properties' in lower_prop_items['properties'][objs]:

# #                                 temp_attr[amznAttr][property_item][objs] =  lower_prop_items['required'].get (['examples'][0], None)

# #                             else:
# #                                 lower_prop_items_sub = lower_prop_items['properties'][objs]['items']
# #                                 if 'properties' in lower_prop_items_sub.keys ():
# #                                     for ika in lower_prop_items_sub['required']:

# #                                         temp_attr[amznAttr][property_item]  [objs][ika] =lower_prop_items_sub   ['properties'][ika].get(['examples']    [0], None)
# #                                 else:
# #                                     pass
# #                     else:
# #                         pass
# #                 else:
# #                     if 'properties' in lower_sub_attrs_props[property_item]:
# #                         for prop_item in lower_sub_attrs_props[property_item]['properties']:

# #                             temp_attr[amznAttr][property_item][prop_item] = lower_sub_attrs_props[property_item]['properties'][prop_item].get(['examples']    [0], None)

# #     if 'type' in sub_attrs:

# #         if sub_attrs['type'] == 'array':
# #             type_attr = list
# #         elif sub_attrs['type'] == 'object':
# #             type_attr = str

# #         elif sub_attrs['type'] == 'number':
# #             type_attr = int

# #     if type_attr == list:

# #         attrss[amznAttr] = [temp_attr[amznAttr]]

# #     else:

# #         attrss[amznAttr] = temp_attr[amznAttr]


# # if attrss:

# #     with open('amazon_rug_attrs.json', 'w', encoding='utf-8') as attrFile:
# #         json.dump(attrss, attrFile, indent=4)

# # print(attrss)

import re


gf = 'Nem Alıcı Paspaslar'
category = re.sub(r"(\bPaspas\b|\bPaspaslar\b)", "", gf, re.IGNORECASE).strip()
if re.search(category, gf):
    print(gf)
