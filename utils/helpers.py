"""
Helper functions for the application
"""

import os
import json
import csv
import time
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, TypeVar
from datetime import datetime, timedelta
import pandas as pd
from core.logger import logger
from core.exceptions import ValidationError

T = TypeVar('T')

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        raise

def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        file_path: Path to the JSON file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.debug(f"Data saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {str(e)}")
        raise

def load_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load data from a CSV file
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries, one for each row
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading CSV file {file_path}: {str(e)}")
        raise

def save_csv_file(data: List[Dict[str, Any]], file_path: str) -> None:
    """
    Save data to a CSV file
    
    Args:
        data: List of dictionaries to save
        file_path: Path to the CSV file
    """
    try:
        if not data:
            logger.warning(f"No data to save to {file_path}")
            return
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Get fieldnames from the first item
        fieldnames = data[0].keys()
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
        logger.debug(f"Data saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving CSV file {file_path}: {str(e)}")
        raise

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """
    Flatten a nested dictionary
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested dictionaries
        sep: Separator for keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            # Convert list to string representation
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)

def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, 
               exceptions: tuple = (Exception,)) -> Callable:
    """
    Retry decorator for async functions
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Exceptions to catch and retry
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__} failed: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {current_delay:.2f} seconds before retry")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} retries failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    
    return decorator

def validate_sku(sku: str) -> bool:
    """
    Validate SKU format
    
    Args:
        sku: SKU to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not sku:
        return False
        
    # SKU should be alphanumeric with optional hyphens and underscores
    import re
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, sku))

def parse_date(date_str: str) -> datetime:
    """
    Parse date string in various formats
    
    Args:
        date_str: Date string
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If the date format is not recognized
    """
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    raise ValueError(f"Date format not recognized: {date_str}")

def format_price(price: Union[float, str], currency: str = 'TRY', decimal_places: int = 2) -> str:
    """
    Format price with currency
    
    Args:
        price: Price value
        currency: Currency code
        decimal_places: Number of decimal places
        
    Returns:
        Formatted price string
    """
    try:
        # Convert to float if string
        if isinstance(price, str):
            price = float(price.replace(',', '.'))
            
        # Format with specified decimal places
        formatted = f"{price:.{decimal_places}f}"
        
        # Add currency symbol
        currency_symbols = {
            'TRY': '₺',
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }
        
        symbol = currency_symbols.get(currency, currency)
        return f"{symbol}{formatted}"
    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting price {price}: {str(e)}")
        return f"{currency}0.00"

def create_excel_report(data: List[Dict[str, Any]], file_path: str, sheet_name: str = 'Report') -> None:
    """
    Create Excel report from data
    
    Args:
        data: List of dictionaries to save
        file_path: Path to the Excel file
        sheet_name: Name of the sheet
    """
    try:
        if not data:
            logger.warning(f"No data to save to {file_path}")
            return
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Save to Excel
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.set_column(i, i, max_len)
            
        logger.info(f"Excel report saved to {file_path}")
    except Exception as e:
        logger.error(f"Error creating Excel report {file_path}: {str(e)}")
        raise