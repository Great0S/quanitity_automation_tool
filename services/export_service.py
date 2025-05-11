"""
Export service for exporting data in various formats
"""

from typing import Dict, List, Any, Optional, cast
import pandas as pd
from io import BytesIO
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import xlsxwriter
from config.constants import ExportFormat, MIME_TYPES
from core.exceptions import ExportError
from core.logger import logger

class ExportService:
    """Service for exporting data in various formats"""
    
    def __init__(self):
        """Initialize the export service"""
        self.supported_formats = [format.value for format in ExportFormat]

    def export_data(self, data: List[Dict[str, Any]], format: str) -> BytesIO:
        """
        Export data in specified format
        
        Args:
            data: List of data items to export
            format: Export format (csv, xlsx, json, xml)
            
        Returns:
            BytesIO object containing the exported data
            
        Raises:
            ValueError: If the format is not supported
            ExportError: If the export fails
        """
        if format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format}")
            
        try:
            if format == ExportFormat.CSV.value:
                return self._export_csv(data)
            elif format == ExportFormat.EXCEL.value:
                return self._export_excel(data)
            elif format == ExportFormat.JSON.value:
                return self._export_json(data)
            elif format == ExportFormat.XML.value:
                return self._export_xml(data)
            else:
                # This should never happen due to the check above, but added for type checking
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            raise ExportError(f"Export failed: {str(e)}")

    def _export_csv(self, data: List[Dict[str, Any]]) -> BytesIO:
        """
        Export data to CSV
        
        Args:
            data: List of data items to export
            
        Returns:
            BytesIO object containing CSV data
        """
        output = BytesIO()
        df = pd.DataFrame(self._flatten_data(data))
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return output

    def _export_excel(self, data: List[Dict[str, Any]]) -> BytesIO:
        """
        Export data to Excel
        
        Args:
            data: List of data items to export
            
        Returns:
            BytesIO object containing Excel data
        """
        output = BytesIO()
        df = pd.DataFrame(self._flatten_data(data))
        
        # Create Excel writer with formatting
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Get workbook and worksheet objects
            # Cast to xlsxwriter.Workbook to help type checker
            workbook = cast(xlsxwriter.Workbook, writer.book)
            worksheet = writer.sheets['Products']
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'border': 1
            })
            
            # Apply formats
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Set column widths
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.set_column(i, i, max_length + 2)
                
        output.seek(0)
        return output

    def _export_json(self, data: List[Dict[str, Any]]) -> BytesIO:
        """
        Export data to JSON
        
        Args:
            data: List of data items to export
            
        Returns:
            BytesIO object containing JSON data
        """
        output = BytesIO()
        json_data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_records': len(data)
            },
            'data': data
        }
        output.write(json.dumps(json_data, indent=2).encode('utf-8'))
        output.seek(0)
        return output

    def _export_xml(self, data: List[Dict[str, Any]]) -> BytesIO:
        """
        Export data to XML
        
        Args:
            data: List of data items to export
            
        Returns:
            BytesIO object containing XML data
        """
        output = BytesIO()
        root = ET.Element('products')
        
        # Add metadata
        metadata = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata, 'exported_at').text = datetime.now().isoformat()
        ET.SubElement(metadata, 'total_records').text = str(len(data))
        
        # Add products
        for item in data:
            product = ET.SubElement(root, 'product')
            self._dict_to_xml(item, product)
            
        tree = ET.ElementTree(root)
        tree.write(output, encoding='utf-8', xml_declaration=True)
        output.seek(0)
        return output

    def _flatten_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten nested data structure
        
        Args:
            data: List of data items to flatten
            
        Returns:
            List of flattened data items
        """
        flattened = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_item[f"{key}_{sub_key}"] = sub_value
                else:
                    flat_item[key] = value
            flattened.append(flat_item)
        return flattened

    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element) -> None:
        """
        Convert dictionary to XML elements
        
        Args:
            data: Dictionary to convert
            parent: Parent XML element
        """
        for key, value in data.items():
            child = ET.SubElement(parent, key)
            if isinstance(value, dict):
                self._dict_to_xml(value, child)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._dict_to_xml(item, ET.SubElement(child, 'item'))
                    else:
                        ET.SubElement(child, 'item').text = str(item)
            else:
                child.text = str(value)

    def get_mime_type(self, format: str) -> str:
        """
        Get MIME type for export format
        
        Args:
            format: Export format
            
        Returns:
            MIME type string
        """
        return MIME_TYPES.get(format, 'application/octet-stream')

    def get_filename(self, format: str, prefix: str = 'export') -> str:
        """
        Generate filename for export
        
        Args:
            format: Export format
            prefix: Filename prefix
            
        Returns:
            Generated filename
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}.{format}"