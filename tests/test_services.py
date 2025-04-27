import unittest
from unittest.mock import patch, MagicMock
from services.product_service import ProductService
from services.sync_service import SyncService
from services.export_service import ExportService
from core.exceptions import ServiceError, SyncError

class TestProductService(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.service = ProductService(self.mock_client)

    def test_fetch_products_success(self):
        self.mock_client.get_products.return_value = []
        products = self.service.fetch_products()
        self.assertIsInstance(products, list)

    def test_fetch_products_failure(self):
        self.mock_client.get_products.side_effect = Exception()
        with self.assertRaises(ServiceError):
            self.service.fetch_products()

    def test_update_product_success(self):
        product_data = {'sku': 'TEST001'}
        self.mock_client.update_product.return_value = product_data
        result = self.service.update_product(product_data)
        self.assertEqual(result, product_data)

class TestSyncService(unittest.TestCase):
    def setUp(self):
        self.source_service = MagicMock()
        self.target_service = MagicMock()
        self.sync_service = SyncService(self.source_service, self.target_service)

    def test_sync_products_success(self):
        products = [{'sku': 'TEST001'}]
        self.source_service.fetch_products.return_value = products
        self.target_service.update_product.return_value = products[0]
        
        result = self.sync_service.sync_products(products)
        self.assertEqual(result['successful'], 1)
        self.assertEqual(result['failed'], 0)

    def test_sync_products_partial_failure(self):
        products = [{'sku': 'TEST001'}, {'sku': 'TEST002'}]
        self.target_service.update_product.side_effect = [
            products[0],
            Exception()
        ]
        
        result = self.sync_service.sync_products(products)
        self.assertEqual(result['successful'], 1)
        self.assertEqual(result['failed'], 1)

class TestExportService(unittest.TestCase):
    def setUp(self):
        self.service = ExportService()
        self.test_data = [{'sku': 'TEST001', 'name': 'Test Product'}]

    def test_export_csv(self):
        result = self.service.export_data(self.test_data, 'csv')
        self.assertIsInstance(result, bytes)

    def test_export_excel(self):
        result = self.service.export_data(self.test_data, 'excel')
        self.assertIsInstance(result, bytes)

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            self.service.export_data(self.test_data, 'invalid')
