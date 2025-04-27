import unittest
from unittest.mock import patch, MagicMock
from api.base_client import BaseAPIClient
from api.n11_client import N11Client
from api.trendyol_client import TrendyolClient
from core.exceptions import APIError

class TestBaseAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = BaseAPIClient()

    def test_authenticate_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.client.authenticate()

    def test_get_products_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.client.get_products()

    def test_update_product_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.client.update_product({})

class TestN11Client(unittest.TestCase):
    def setUp(self):
        self.client = N11Client()

    @patch('requests.Session.request')
    def test_authenticate_success(self, mock_request):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {'status': 'success'}
        
        self.client.authenticate()
        self.assertTrue(self.client.authenticated)

    @patch('requests.Session.request')
    def test_authenticate_failure(self, mock_request):
        mock_request.return_value.status_code = 401
        
        with self.assertRaises(APIError):
            self.client.authenticate()

    @patch('requests.Session.request')
    def test_get_products_success(self, mock_request):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {'products': []}
        
        products = self.client.get_products()
        self.assertIsInstance(products, list)

class TestTrendyolClient(unittest.TestCase):
    def setUp(self):
        self.client = TrendyolClient()

    @patch('requests.Session.request')
    def test_authenticate_success(self, mock_request):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {'status': 'success'}
        
        self.client.authenticate()
        self.assertTrue(self.client.authenticated)

    @patch('requests.Session.request')
    def test_get_products_success(self, mock_request):
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {'content': []}
        
        products = self.client.get_products()
        self.assertIsInstance(products, list)
