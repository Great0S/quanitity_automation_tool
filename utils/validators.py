from typing import Dict, Any, List, Optional
import re
from datetime import datetime

class ProductValidator:
    @staticmethod
    def validate_product(product_data: Dict[str, Any]) -> List[str]:
        """Validate product data"""
        errors = []
        
        # Required fields
        required_fields = {
            'sku': 'SKU is required',
            'data': 'Product data is required'
        }
        
        for field, message in required_fields.items():
            if field not in product_data:
                errors.append(message)
        
        if 'data' in product_data:
            data_fields = {
                'title': 'Product title is required',
                'price': 'Product price is required',
                'quantity': 'Product quantity is required'
            }
            
            for field, message in data_fields.items():
                if field not in product_data['data']:
                    errors.append(message)
        
        # Validate SKU format
        if 'sku' in product_data:
            if not re.match(r'^[A-Za-z0-9\-_]{3,50}$', product_data['sku']):
                errors.append('Invalid SKU format')
        
        # Validate price
        if 'data' in product_data and 'price' in product_data['data']:
            try:
                price = float(product_data['data']['price'])
                if price < 0:
                    errors.append('Price cannot be negative')
            except ValueError:
                errors.append('Invalid price format')
        
        # Validate quantity
        if 'data' in product_data and 'quantity' in product_data['data']:
            try:
                quantity = int(product_data['data']['quantity'])
                if quantity < 0:
                    errors.append('Quantity cannot be negative')
            except ValueError:
                errors.append('Invalid quantity format')
        
        return errors

class APIValidator:
    @staticmethod
    def validate_api_response(response: Dict[str, Any]) -> List[str]:
        """Validate API response"""
        errors = []
        
        if not isinstance(response, dict):
            errors.append('Invalid response format')
            return errors
        
        required_fields = ['status', 'data']
        for field in required_fields:
            if field not in response:
                errors.append(f'Missing required field: {field}')
        
        return errors

class SyncValidator:
    @staticmethod
    def validate_sync_config(config: Dict[str, Any]) -> List[str]:
        """Validate sync configuration"""
        errors = []
        
        required_fields = {
            'source_platform': 'Source platform is required',
            'target_platform': 'Target platform is required',
            'sync_fields': 'Sync fields are required'
        }
        
        for field, message in required_fields.items():
            if field not in config:
                errors.append(message)
        
        if 'sync_fields' in config and not isinstance(config['sync_fields'], list):
            errors.append('Sync fields must be a list')
        
        return errors

class InputValidator:
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> List[str]:
        """Validate date range"""
        errors = []
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start > end:
                errors.append('Start date must be before end date')
                
            if end > datetime.now():
                errors.append('End date cannot be in the future')
                
        except ValueError:
            errors.append('Invalid date format. Use YYYY-MM-DD')
        
        return errors

    @staticmethod
    def validate_price_range(min_price: float, max_price: float) -> List[str]:
        """Validate price range"""
        errors = []
        
        if min_price < 0:
            errors.append('Minimum price cannot be negative')
            
        if max_price < min_price:
            errors.append('Maximum price must be greater than minimum price')
        
        return errors
