import unittest
from datetime import datetime
from utils.validators import ProductValidator, APIValidator
from utils.formatters import DataFormatter, ExportFormatter
from utils.helpers import FileHelper, SecurityHelper, DataHelper

class TestProductValidator(unittest.TestCase):
    def test_validate_valid_product(self):
        product_data = {
            'sku': 'TEST001',
            'data': {
                'title': 'Test Product',
                'price': 10.99,
                'quantity': 100
            }
        }
        errors = ProductValidator.validate_product(product_data)
        self.assertEqual(len(errors), 0)

    def test_validate_invalid_product(self):
        product_data = {
            'sku': 'TEST001',
            'data': {
                'title': 'Test Product',
                'price': -10.99,  # Invalid price
                'quantity': -100  # Invalid quantity
            }
        }
        errors = ProductValidator.validate_product(product_data)
        self.assertTrue(len(errors) > 0)

class TestDataFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = DataFormatter()

    def test_format_currency(self):
        self.assertEqual(
            self.formatter.format_currency(10.99, 'USD'),
            '$10.99'
        )

    def test_format_date(self):
        date = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(
            self.formatter.format_date(date, '%Y-%m-%d'),
            '2023-01-01'
        )

    def test_format_percentage(self):
        self.assertEqual(
            self.formatter.format_percentage(75.5),
            '75.5%'
        )

class TestDataHelper(unittest.TestCase):
    def setUp(self):
        self.helper = DataHelper()

    def test_deep_get(self):
        data = {'a': {'b': {'c': 1}}}
        self.assertEqual(
            self.helper.deep_get(data, 'a.b.c'),
            1
        )
        self.assertIsNone(
            self.helper.deep_get(data, 'a.b.d')
        )

    def test_deep_set(self):
        data = {}
        self.helper.deep_set(data, 'a.b.c', 1)
        self.assertEqual(data['a']['b']['c'], 1)

    def test_filter_dict(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        filtered = self.helper.filter_dict(data, ['a', 'c'])
        self.assertEqual(filtered, {'a': 1, 'c': 3})

if __name__ == '__main__':
    unittest.main()
