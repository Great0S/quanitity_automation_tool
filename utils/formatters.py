from typing import Dict, Any, List, Union
from datetime import datetime
import json
import csv
import io

class DataFormatter:
    @staticmethod
    def format_currency(amount: float, currency: str = 'USD') -> str:
        """Format currency amount"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'TRY': '₺'
        }
        
        symbol = currency_symbols.get(currency, '')
        return f"{symbol}{amount:,.2f}"

    @staticmethod
    def format_date(date: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Format datetime"""
        return date.strftime(format_str)

    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage"""
        return f"{value:.1f}%"

    @staticmethod
    def format_quantity(quantity: int) -> str:
        """Format quantity with thousand separators"""
        return f"{quantity:,}"

class ExportFormatter:
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """Convert data to CSV format"""
        output = io.StringIO()
        if not data:
            return ""
            
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()

    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        """Convert data to JSON format"""
        return json.dumps(data, indent=2)

    @staticmethod
    def to_xml(data: List[Dict[str, Any]]) -> str:
        """Convert data to XML format"""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<products>')
        
        for item in data:
            xml_lines.append('  <product>')
            for key, value in item.items():
                xml_lines.append(f'    <{key}>{value}</{key}>')
            xml_lines.append('  </product>')
            
        xml_lines.append('</products>')
        
        return '\n'.join(xml_lines)

class ResponseFormatter:
    @staticmethod
    def format_api_response(data: Any, status: str = 'success', 
                          message: str = None) -> Dict[str, Any]:
        """Format API response"""
        response = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        if message:
            response['message'] = message
            
        return response

    @staticmethod
    def format_error_response(error: str, code: str = None) -> Dict[str, Any]:
        """Format error response"""
        response = {
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': error
        }
        
        if code:
            response['code'] = code
            
        return response
