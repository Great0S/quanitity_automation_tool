"""
Cache utility for storing and retrieving data
"""

import asyncio
import json
from typing import Dict, Any, Optional, Union
import time
import os
from core.logger import logger

# Singleton cache instance
_cache_instance = None

class Cache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        """Initialize the cache"""
        self.data: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = None
        self._start_cleanup_task()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.data:
            return None
        
        cache_entry = self.data[key]
        
        # Check if expired
        if cache_entry["expires_at"] and time.time() > cache_entry["expires_at"]:
            # Remove expired entry
            del self.data[key]
            return None
        
        return cache_entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
        """
        expires_at = time.time() + ttl if ttl else None
        
        self.data[key] = {
            "value": value,
            "expires_at": expires_at
        }
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was deleted, False otherwise
        """
        if key in self.data:
            del self.data[key]
            return True
        
        return False
    
    async def clear(self) -> None:
        """Clear the cache"""
        self.data.clear()
    
    def _start_cleanup_task(self) -> None:
        """Start a background task to clean up expired entries"""
        async def cleanup_worker():
            while True:
                try:
                    # Sleep for a while
                    await asyncio.sleep(60)  # Clean up every minute
                    
                    # Find expired entries
                    now = time.time()
                    expired_keys = [
                        key for key, entry in self.data.items()
                        if entry["expires_at"] and now > entry["expires_at"]
                    ]
                    
                    # Remove expired entries
                    for key in expired_keys:
                        del self.data[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {str(e)}")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(cleanup_worker())


def get_cache() -> Cache:
    """Get the singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance