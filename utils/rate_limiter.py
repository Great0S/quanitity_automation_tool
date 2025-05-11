"""
Rate limiter utility for API requests
"""

import time
import asyncio
from typing import Dict, Any, Callable, Awaitable, TypeVar, Optional
from datetime import datetime, timedelta
from core.logger import logger

T = TypeVar('T')

class RateLimiter:
    """
    Rate limiter for API requests
    
    Implements token bucket algorithm for rate limiting
    """
    
    def __init__(self, requests_per_second: float, burst_limit: int = None):
        """
        Initialize rate limiter
        
        Args:
            requests_per_second: Maximum number of requests per second
            burst_limit: Maximum number of requests that can be made in a burst
        """
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit or int(requests_per_second * 2)
        self.tokens = self.burst_limit
        self.last_refill_time = datetime.now()
        self.lock = asyncio.Lock()
        self.logger = logger

    async def acquire(self) -> None:
        """
        Acquire a token for making a request
        
        Blocks until a token is available
        """
        async with self.lock:
            # Refill tokens based on time elapsed
            now = datetime.now()
            time_elapsed = (now - self.last_refill_time).total_seconds()
            new_tokens = time_elapsed * self.requests_per_second
            self.tokens = min(self.burst_limit, self.tokens + new_tokens)
            self.last_refill_time = now
            
            # If no tokens available, calculate wait time
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.requests_per_second
                self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.tokens = 1  # After waiting, we have at least one token
            
            # Consume one token
            self.tokens -= 1

    async def execute(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute a function with rate limiting
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
        """
        await self.acquire()
        return await func(*args, **kwargs)


class PlatformRateLimiter:
    """
    Rate limiter for multiple platforms
    
    Maintains separate rate limiters for each platform
    """
    
    def __init__(self):
        """Initialize platform rate limiter"""
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.default_rates = {
            'n11': 5.0,        # 5 requests per second
            'trendyol': 2.0,   # 2 requests per second
            'hepsiburada': 1.0, # 1 request per second
            'pazarama': 1.0,   # 1 request per second
            'pttavm': 1.0,     # 1 request per second
            'wordpress': 2.0,  # 2 requests per second
            'default': 1.0     # Default rate for other platforms
        }
        self.logger = logger

    def get_rate_limiter(self, platform: str) -> RateLimiter:
        """
        Get rate limiter for a platform
        
        Args:
            platform: Platform name
            
        Returns:
            Rate limiter for the platform
        """
        if platform not in self.rate_limiters:
            rate = self.default_rates.get(platform.lower(), self.default_rates['default'])
            self.rate_limiters[platform] = RateLimiter(rate)
            self.logger.debug(f"Created rate limiter for {platform} with {rate} requests per second")
        
        return self.rate_limiters[platform]

    async def execute(self, platform: str, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute a function with rate limiting for a specific platform
        
        Args:
            platform: Platform name
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
        """
        rate_limiter = self.get_rate_limiter(platform)
        return await rate_limiter.execute(func, *args, **kwargs)

    def update_rate(self, platform: str, requests_per_second: float) -> None:
        """
        Update rate limit for a platform
        
        Args:
            platform: Platform name
            requests_per_second: New rate limit
        """
        self.default_rates[platform.lower()] = requests_per_second
        if platform in self.rate_limiters:
            self.rate_limiters[platform].requests_per_second = requests_per_second
            self.logger.info(f"Updated rate limiter for {platform} to {requests_per_second} requests per second")


# Global instance for use throughout the application
platform_rate_limiter = PlatformRateLimiter()