import os
import logging


# API Keys
N11_API_KEY = os.getenv('N11_API_KEY')
HEPSIBURADA_API_KEY = os.getenv('HEPSIBURADA_API_KEY')
AMAZON_API_KEY = os.getenv('AMAZON_API_KEY')
PTTAVM_API_KEY = os.getenv('PTTAVM_API_KEY')
PAZARAMA_API_KEY = os.getenv('PAZARAMA_API_KEY')
TRENDYOL_API_KEY = os.getenv('TRENDYOL_API_KEY')
WORDPRESS_API_KEY = os.getenv('WORDPRESS_API_KEY')

# Logging configuration
LOG_FILE = 'app.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
