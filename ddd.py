# import json
# import os
# import requests
# from sp_api.api import Orders
# from sp_api.api import Reports
# from sp_api.api import DataKiosk
# from sp_api.api import ListingsItems, ProductTypeDefinitions
# from sp_api.base import SellingApiException
# from sp_api.base.reportTypes import ReportType
# from datetime import datetime, timedelta

# # DATA KIOSK API
# client = DataKiosk()

# # res = client.create_query(
# #     query="{analytics_salesAndTraffic_2023_11_15{salesAndTrafficByAsin(startDate:"2022-09-01" endDate:"2022-09-30" aggregateBy:SKU marketplaceIds:["ATVPDKIKX0DER"]){childAsin endDate marketplaceId parentAsin sales{orderedProductSales{amount currencyCode}totalOrderItems totalOrderItemsB2B}sku startDate traffic{browserPageViews browserPageViewsB2B browserPageViewsPercentage browserPageViewsPercentageB2B browserSessionPercentage unitSessionPercentageB2B unitSessionPercentage}}}}")
# # print(res)

# # orders API
# # try:
# #     res = Orders().get_orders(CreatedAfter=(
# #         datetime.utcnow() - timedelta(days=7)).isoformat())
# #     print(res.payload)  # json data
# # except SellingApiException as ex:
# #     print(ex)


# # # report request
# # createReportResponse = Reports().create_report(
# #     reportType=ReportType.GET_MERCHANT_LISTINGS_ALL_DATA)
# sid = os.getenv('AMAZONSELLERACCOUNTID')
# defi = ProductTypeDefinitions().search_definitions_product_types(keywords='Halı',marketplaceIds=['A33AVAJ2PDY3EV'])
# defi2 = ProductTypeDefinitions().get_definitions_product_type(productType='RUG',marketplaceIds=['A33AVAJ2PDY3EV'])
# # print(defi.payload['metaSchema']['link']['resource'])
# meta = requests.get(defi2.payload['schema']['link']['resource'])
# meta_data = json.loads(meta.text)
# # print(meta_data)
# bod = {
#     "productType": "RUG",
#     "requirements": "LISTING",
#     "attributes": {
#         "item_name": [{
#             "value": "Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası"
#         }],
#         "brand": [{
#             "value": "Stepmat"
#         }],
#         "supplier_declared_has_product_identifier_exemption": [{
#             "value": True
#         }],
#         "recommended_browse_nodes": [{
#             "value": "13028044031"
#         }],
#         "model_number": [{
#             "value": "EKOKARE"
#         }],
#         "manufacturer": [{
#             "value": "Eman Halıcılık San. Ve Tic. Ltd. Şti."
#         }],
#         "fulfillment_availability": [{
#             "fulfillment_channel_code": "DEFAULT",
#             "quantity": "1000",
#             "is_inventory_available": True
#         }],
#         "condition_type": [{
#             "value": "new_new"
#         }],
#         "skip_offer": [{
#             "value": True
#         }],
#         "pattern": [
#             {
#                 "value": "Düz"
#             }
#         ],
#         "pile_height": [{
#             "value": "Düşük Hav"
#         }],
#         "included_components": [{
#             "value": "Tek adet Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası"
#         }],
#         "list_price": [{
#             "currency": "TRY",
#             "value_with_tax": 129
#         }],
#         "gift_options": [{
#             "can_be_messaged": "false",
#             "can_be_wrapped": "false"
#         }],
#         "product_description": [{
#             "value": "Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası Evdeki merdivenlerinizi güzelleştirmek ve güvenliğini artırmak için Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası tam da ihtiyacınız olan ürün! Bu paspas, premium kalite iplik kullanılarak üretilmiştir ve üst yüzeyi sayesinde merdivenlerinizde kaymaz bir yüzey sağlar. Ahşap, beton ve mermer merdivenlerde rahatlıkla kullanabilirsiniz. Ayrıca,6 mm hav yüksekliği sayesinde ayaklarınızı yumuşak bir zeminde hissedeceksiniz. Ürün Özellikleri: Malzeme: Premium kalite iplik ; Boyutlar: 25 cm x 65 cm ; Kullanım Alanları: Merdivenler, basamaklar, koridorlar ve daha fazlası ; Temizlik Kolaylığı: Sadece silerek temizlenebilir ; Türkiye Üretimi: Güvenilir ve kaliteli bir ürün ; Bu paspas, uygulaması ve kullanımı son derece kolaydır. Adet olarak satıldığı için ihtiyacınıza göre sipariş verebilirsiniz. Evdeki merdivenlerinizi daha estetik ve güvenli hale getirmek için hemen bu ürünü sepetinize ekleyin!"
#         }],
#         "bullet_point": [{
#             "value": "Bukle Halıdan Ekonomik Basamak ve Merdiven Paspası"
#         }],
#         "generic_keyword": [{
#             "value": "Bukle,Halıdan,Ekonomik,Basamak,ve,Merdiven,Paspası"
#         }],
#         "special_feature": [{
#             "language_tag": 'tr_TR',
#             "value": "Kaymaz"
#         }],
#         "style": [{
#             "value": "Klasik"
#         }],
#         "material": [{
#             "value": "Polyester"
#         }],
#         "number_of_items": [{
#             "value": 1
#         }],
#         "color": [{
#             "value": "Gri"
#         }],
#         "size": [{
#             "value": "25 x 65"
#         }],
#         "part_number": [{
#             "value": "EKOKARE"
#         }],
#         "item_length_width": [{
#             "length": {
#                 "unit": "centimeters",
#                 "value": 25
#             },
#             "width": {
#                 "unit": "centimeters",
#                 "value": 65
#             },
#         }],
#         "item_shape": [{
#             "value": "Dikdörtgen"
#         }],
#         "item_thickness": [{
#             "decimal_value": "5",
#             "unit": 'millimeters'
#         }],
#         "country_of_origin": [{
#             "value": "TR"
#         }],
#         "rug_form_type": [
#             {
#                 "value": "doormat",
#                 "marketplace_id": "A33AVAJ2PDY3EV"
#             }
#         ],
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
#         ]
#     }
# }
# new_ui = ListingsItems().put_listings_item(sellerId=sid, sku='EKOKAREACGRİ',
#                                            marketplaceIds=['A33AVAJ2PDY3EV'], body=bod)
# print(new_ui.payload['status'])
# # Orders(restricted_data_token='<token>').get_orders(CreatedAfter=(datetime.utcnow() - timedelta(days=7)).isoformat())

# # or use the shortcut
# orders = Orders().get_orders(
#     RestrictedResources=['buyerInfo', 'shippingAddress'],
#     LastUpdatedAfter=(datetime.utcnow() - timedelta(days=1)).isoformat()
# )

# dad = {"merchantId": "1343cf54-cf2b-4d63-9d38-53c589795a42",
#        "items": [
#            {"Image1": "https://cdn.dsmcdn.com/ty1315/product/media/images/prod/QC/20240516/06/a5be782e-8cd1-37ec-a6ff-9b6c06feb5dc/1_org_zoom.jpg",
#             "Image2": "https://cdn.dsmcdn.com/ty1316/product/media/images/prod/QC/20240516/06/465bb1f1-db6d-31e6-8d03-22c1e5023a35/1_org_zoom.jpg",
#             "Image3": "https://cdn.dsmcdn.com/ty1316/product/media/images/prod/QC/20240516/06/5bd61a47-750b-3f78-a058-aafb97a24917/1_org_zoom.jpg",
#             "Image4": "https://cdn.dsmcdn.com/ty1314/product/media/images/prod/QC/20240516/05/269afd59-bbbd-3dc5-88c5-38a690be2b63/1_org_zoom.jpg",
#             "Image5": "https://cdn.dsmcdn.com/ty1314/product/media/images/prod/QC/20240516/06/c70c9cc8-b8b0-3cff-94b6-00cd60455e82/1_org_zoom.jpg",
#             "hbsku": "HBCV00005YK3Y8",
#             "merchantSku": "2S-NM4X-I06J",
#             "VaryantGroupID": "2S-NM4X-I06J",
#             "Barcode": "789393947221",
#             "UrunAdi": "Nem Alu0131cu0131 Kaymaz Taban Kapu0131 u00d6nu00fc Paspasu0131",
#             "UrunAciklamasi": "u00dcru00fcn Ebatlaru0131 :45cm x 75cm Nem Alu0131cu0131 Kaymaz Tabanlu0131 Kapu0131 u00d6nu00fc Paspasu0131 Islak Alanlarda Kullanu0131m u0130u00e7in Uygunluk Su Geu00e7irmez Kaymaz Nitril Taban Tu00fcrkiye'de u00dcretilmiu015ftir.",
#             "Marka": "Myfloor",
#             "GarantiSuresi": 24,
#             "kg": "1",
#             "tax_vat_rate": "8",
#             "price": 249,
#             "stock": 994,
#             "Video1": ""}]}


import json

amzn_attrs = {}
attrss = {}
temp_attr = {}

with open('amazonRUGattrs.json', 'r', encoding='utf-8') as attrFile:
    amzn_attrs = json.load(attrFile)
    
attrsproperties = amzn_attrs['properties']    

for amznAttr in attrsproperties:

    sub_attrs = attrsproperties[amznAttr]
    if amznAttr == 'purchasable_offer':

        pass

    for item_attr in sub_attrs:

        lower_sub_attrs = sub_attrs['items']
          
        if lower_sub_attrs['required']:
            for required in lower_sub_attrs['required']:
                if required != 'language_tag':
                    temp_attr[amznAttr] = {required: lower_sub_attrs['properties'][required].get(['examples'][0], None)}
            
        else:
            lower_sub_attrs_props = lower_sub_attrs['properties']
            for property_item in lower_sub_attrs_props:
                    if 'examples' in lower_sub_attrs_props[property_item]:
                        temp_attr[amznAttr] = {property_item: lower_sub_attrs_props[property_item].get(['examples'][0], None)}
                    else:
                        lower_prop_items = lower_sub_attrs_props[property_item]['items']
                        if 'required' in lower_prop_items:
                            for objs in lower_prop_items['required']:
                                    if 'properties' in lower_prop_items['properties'][objs]:
                                        temp_attr[amznAttr] = {property_item: {objs: lower_prop_items['required'].get(['examples'][0], None)}}
                                    else:
                                        lower_prop_items_sub = lower_prop_items['properties'][objs]['items']
                                        if 'properies' in lower_prop_items_sub:
                                            for ika in lower_prop_items_sub['required']:
                                                    
                                                    temp_attr[amznAttr] = {property_item: {objs: {ika: lower_prop_items_sub['properties'].get(['examples'][0], None)}}}
                        
                        else:
                            pass

    

        if sub_attrs['type'] == 'array':
            type_attr = list
        elif sub_attrs['type'] == 'object':
            type_attr = str
            
        elif sub_attrs['type'] == 'number':
            type_attr = int

    if type_attr == list:
        
        attrss[amznAttr] = [temp_attr[amznAttr]]
        temp_attr = {}
    
    else:

        attrss[amznAttr] = temp_attr[amznAttr]

print(attrss)

