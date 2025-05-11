"""
Cache implementation for API responses and frequently accessed data
"""

import time
import threading
import json
import os
from typing import Dict, Any, Optional, Callable, TypeVar, List, Tuple
from datetime import datetime, timedelta
from functools import wraps

from core.logger import logger

T = TypeVar('T')

class Cache:
    """
    In-memory cache with disk persistence
    """
    
    def __init__(self, cache_dir: str = 'cache', default_ttl: int = 300):
        """
        Initialize cache
        
        Args:
            cache_dir: Directory to store persistent cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load persistent cache
        self._load_persistent_cache()
        
        # Start background cleanup thread
        self._start_cleanup_thread()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found or expired
            
        Returns:
            Cached value or default
        """
        with self.lock:
            if key not in self.cache:
                return default
                
            entry = self.cache[key]
            
            # Check if entry has expired
            if entry['expires_at'] < time.time():
                del self.cache[key]
                return default
                
            # Update access time
            entry['last_accessed'] = time.time()
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, persist: bool = False) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
            persist: Whether to persist to disk
        """
        with self.lock:
            ttl = ttl if ttl is not None else self.default_ttl
            
            self.cache[key] = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl,
                'last_accessed': time.time(),
                'persist': persist
            }
            
            # Persist to disk if requested
            if persist:
                self._persist_entry(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key was found and deleted, False otherwise
        """
        with self.lock:
            if key in self.cache:
                # Check if entry was persisted
                if self.cache[key].get('persist', False):
                    self._delete_persisted_entry(key)
                
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            # Delete all persisted entries
            for key, entry in self.cache.items():
                if entry.get('persist', False):
                    self._delete_persisted_entry(key)
            
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_entries = len(self.cache)
            expired_entries = sum(1 for entry in self.cache.values() if entry['expires_at'] < time.time())
            persisted_entries = sum(1 for entry in self.cache.values() if entry.get('persist', False))
            
            # Calculate memory usage (approximate)
            try:
                import sys
                memory_usage = sum(sys.getsizeof(entry['value']) for entry in self.cache.values())
            except:
                memory_usage = -1
            
            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired_entries,
                'expired_entries': expired_entries,
                'persisted_entries': persisted_entries,
                'memory_usage_bytes': memory_usage,
                'cache_dir': self.cache_dir
            }
    
    def _persist_entry(self, key: str) -> None:
        """Persist cache entry to disk"""
        try:
            entry = self.cache[key]
            
            # Only persist serializable data
            try:
                # Create a copy of the entry for persistence
                persist_data = {
                    'value': entry['value'],
                    'created_at': entry['created_at'],
                    'expires_at': entry['expires_at']
                }
                
                # Save to file
                file_path = os.path.join(self.cache_dir, f"{key.replace('/', '_')}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(persist_data, f)
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not persist cache entry '{key}': {str(e)}")
                # Mark as non-persistable
                entry['persist'] = False
        except Exception as e:
            logger.error(f"Error persisting cache entry '{key}': {str(e)}")
    
    def _delete_persisted_entry(self, key: str) -> None:
        """Delete persisted cache entry"""
        try:
            file_path = os.path.join(self.cache_dir, f"{key.replace('/', '_')}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error deleting persisted cache entry '{key}': {str(e)}")
    
    def _load_persistent_cache(self) -> None:
        """Load persistent cache from disk"""
        try:
            if not os.path.exists(self.cache_dir):
                return
                
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                    
                try:
                    file_path = os.path.join(self.cache_dir, filename)
                    key = filename[:-5].replace('_', '/')
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Skip expired entries
                    if data['expires_at'] < time.time():
                        os.remove(file_path)
                        continue
                    
                    # Add to cache
                    self.cache[key] = {
                        'value': data['value'],
                        'created_at': data['created_at'],
                        'expires_at': data['expires_at'],
                        'last_accessed': time.time(),
                        'persist': True
                    }
                except Exception as e:
                    logger.warning(f"Error loading cache entry from {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading persistent cache: {str(e)}")
    
    def _start_cleanup_thread(self) -> None:
        """Start background thread for cache cleanup"""
        def cleanup_task():
            while True:
                try:
                    # Sleep first to avoid immediate cleanup
                    time.sleep(60)  # Run every minute
                    
                    with self.lock:
                        # Find expired entries
                        expired_keys = [
                            key for key, entry in self.cache.items()
                            if entry['expires_at'] < time.time()
                        ]
                        
                        # Delete expired entries
                        for key in expired_keys:
                            self.delete(key)
                            
                        # Log cleanup
                        if expired_keys:
                            logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {str(e)}")
        
        # Start daemon thread
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()


# Global cache instance
_cache = Cache()

def get_cache() -> Cache:
    """Get global cache instance"""
    return _cache

def cached(ttl: Optional[int] = None, key_prefix: str = "", 
           key_func: Optional[Callable[..., str]] = None,
           persist: bool = False):
    """
    Cache decorator for functions
    
    Args:
        ttl: Time-to-live in seconds (None for default)
        key_prefix: Prefix for cache key
        key_func: Function to generate cache key from arguments
        persist: Whether to persist to disk
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key generation
                arg_str = str(args) + str(sorted(kwargs.items()))
                key = f"{key_prefix}:{func.__module__}.{func.__name__}:{hash(arg_str)}"
            
            # Try to get from cache
            cache = get_cache()
            result = cache.get(key)
            
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl, persist=persist)
            
            return result
        
        # Add cache control methods to the function
        wrapper.invalidate_cache = lambda *args, **kwargs: get_cache().delete(
            key_func(*args, **kwargs) if key_func else 
            f"{key_prefix}:{func.__module__}.{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
        )
        
        return wrapper
    
    return decorator


def async_cached(ttl: Optional[int] = None, key_prefix: str = "",
                key_func: Optional[Callable[..., str]] = None,
                persist: bool = False):
    """
    Cache decorator for async functions
    
    Args:
        ttl: Time-to-live in seconds (None for default)
        key_prefix: Prefix for cache key
        key_func: Function to generate cache key from arguments
        persist: Whether to persist to disk
        
    Returns:
        Decorated async function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key generation
                arg_str = str(args) + str(sorted(kwargs.items()))
                key = f"{key_prefix}:{func.__module__}.{func.__name__}:{hash(arg_str)}"
            
            # Try to get from cache
            cache = get_cache()
            result = cache.get(key)
            
            if result is not None:
                return result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl=ttl, persist=persist)
            
            return result
        
        # Add cache control methods to the function
        wrapper.invalidate_cache = lambda *args, **kwargs: get_cache().delete(
            key_func(*args, **kwargs) if key_func else 
            f"{key_prefix}:{func.__module__}.{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
        )
        
        return wrapper
    
    return decorator