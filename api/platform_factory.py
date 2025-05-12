"""
Platform factory for creating API clients
"""

from typing import Any
from core.logger import logger
from api.hepsiburada_client import HepsiburadaClient
from api.n11_client import N11Client
from api.trendyol_client import TrendyolClient

def get_platform_client(platform: str) -> Any:
    """
    Get API client for a platform
    
    Args:
        platform: Platform name
        
    Returns:
        API client for the platform
    """
    platform = platform.lower()
    
    if platform == "hepsiburada":
        return HepsiburadaClient()
    elif platform == "n11":
        return N11Client()
    elif platform == "trendyol":
        return TrendyolClient()
    else:
        logger.error(f"Unsupported platform: {platform}")
        raise ValueError(f"Unsupported platform: {platform}")