"""
SSL Helper utilities for handling certificate verification issues
"""

import ssl
import aiohttp
import certifi
import os
import sys
from core.logger import logger

def create_ssl_context(verify=True):
    """
    Create an SSL context that can be used with aiohttp
    
    Args:
        verify: Whether to verify SSL certificates
        
    Returns:
        SSL context object
    """
    if verify:
        # Use certifi's certificate bundle
        ssl_context = ssl.create_default_context(cafile=certifi.where())
    else:
        # Create unverified context (ONLY FOR DEVELOPMENT)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        logger.warning("SSL certificate verification is disabled. This is insecure!")
    
    return ssl_context

def get_aiohttp_ssl_context():
    """
    Get SSL context for aiohttp based on environment settings
    
    Returns:
        SSL context or False to disable verification
    """
    # Check if we should disable SSL verification (development only)
    disable_ssl_verify = os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true'
    
    if disable_ssl_verify:
        logger.warning("SSL certificate verification is disabled. This is insecure!")
        return False  # This will disable SSL verification in aiohttp
    else:
        return create_ssl_context(verify=True)

def fix_macos_certificates():
    """
    Fix SSL certificate issues on macOS
    """
    if sys.platform == 'darwin':
        # Check if the certifi package is installed
        try:
            import certifi
            os.environ['SSL_CERT_FILE'] = certifi.where()
            logger.info(f"Set SSL_CERT_FILE to {certifi.where()}")
        except ImportError:
            logger.warning("certifi package not found. SSL certificate verification may fail.")
            
        # Check if the certificates exist in the expected location
        cert_file = '/Applications/Python 3.x/Install Certificates.command'
        if os.path.exists(cert_file.replace('3.x', '3.13')):
            logger.info("You may need to run the 'Install Certificates.command' in your Python installation folder")