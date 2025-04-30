from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

class Cache:
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
            
        item = self._cache[key]
        if datetime.now() > item['expires']:
            del self._cache[key]
            return None
            
        return item['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        self._cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        }

    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
