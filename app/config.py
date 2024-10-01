import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

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

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger('app')