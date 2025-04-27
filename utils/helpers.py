from typing import Dict, Any, List, Optional
import hashlib
import base64
from datetime import datetime
import os
import json

class FileHelper:
    @staticmethod
    def ensure_directory(path: str) -> None:
        """Ensure directory exists"""
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def save_json(data: Any, filepath: str) -> None:
        """Save data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_json(filepath: str) -> Any:
        """Load data from JSON file"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

class SecurityHelper:
    @staticmethod
    def generate_hash(data: str) -> str:
        """Generate SHA-256 hash"""
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def encode_base64(data: str) -> str:
        """Encode string to base64"""
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode_base64(data: str) -> str:
        """Decode base64 string"""
        return base64.b64decode(data.encode()).decode()

class DataHelper:
    @staticmethod
    def deep_get(obj: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Get nested dictionary value by dot notation path"""
        try:
            parts = path.split('.')
            for part in parts:
                obj = obj[part]
            return obj
        except (KeyError, TypeError):
            return default

    @staticmethod
    def deep_set(obj: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested dictionary value by dot notation path"""
        parts = path.split('.')
        for i, part in enumerate(parts[:-1]):
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    @staticmethod
    def filter_dict(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """Filter dictionary by keys"""
        return {k: v for k, v in data.items() if k in keys}

class DateHelper:
    @staticmethod
    def get_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get list of dates between start and end date"""
        date_list = []
        current_date = start_date
        
        while current_date <= end_date:
            date_list.append(current_date)
            current_date = current_date.replace(day=current_date.day + 1)
            
        return date_list

    @staticmethod
    def is_valid_date(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
        """Check if string is valid date"""
        try:
            datetime.strptime(date_str, format_str)
            return True
        except ValueError:
            return False

class CacheHelper:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set cache value with TTL"""
        self.cache[key] = value
        self.timestamps[key] = datetime.now().timestamp() + ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        if key in self.cache:
            if datetime.now().timestamp() < self.timestamps[key]:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.timestamps.clear()
