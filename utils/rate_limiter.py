import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.logger import logger

class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.timestamps: List[datetime] = []
        
    async def acquire(self) -> None:
        """Acquire permission to make an API call"""
        now = datetime.now()
        
        # Remove timestamps outside the current period
        self.timestamps = [ts for ts in self.timestamps 
                         if ts > now - timedelta(seconds=self.period)]
        
        if len(self.timestamps) >= self.calls:
            # Calculate sleep time
            sleep_time = (self.timestamps[0] + 
                         timedelta(seconds=self.period) - now).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Waiting {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
        
        self.timestamps.append(now)
