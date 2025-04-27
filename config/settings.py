import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        load_dotenv()
        
        # API Settings
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
        self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
        
        # N11 Settings
        self.N11_API_KEY = os.getenv('N11_API_KEY')
        self.N11_API_SECRET = os.getenv('N11_API_SECRET')
        self.N11_API_URL = os.getenv('N11_API_URL', 'https://api.n11.com/ws')
        
        # Trendyol Settings
        self.TRENDYOL_API_KEY = os.getenv('TRENDYOL_API_KEY')
        self.TRENDYOL_API_SECRET = os.getenv('TRENDYOL_API_SECRET')
        self.TRENDYOL_SELLER_ID = os.getenv('TRENDYOL_SELLER_ID')
        
        # Amazon Settings
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.AWS_REGION = os.getenv('AWS_REGION', 'eu-west-1')
        self.AMAZON_MARKETPLACE_ID = os.getenv('AMAZON_MARKETPLACE_ID')
        
        # Application Settings
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
        self.AUTO_REFRESH_INTERVAL = int(os.getenv('AUTO_REFRESH_INTERVAL', '300'))
        
        # Export Settings
        self.EXPORT_FOLDER = os.getenv('EXPORT_FOLDER', 'exports')
        self.MAX_EXPORT_ROWS = int(os.getenv('MAX_EXPORT_ROWS', '10000'))
        
        # Database Settings
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = int(os.getenv('DB_PORT', '5432'))
        self.DB_NAME = os.getenv('DB_NAME', 'product_manager')
        self.DB_USER = os.getenv('DB_USER', 'postgres')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD')

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return getattr(self, key, default)

    def get_api_credentials(self, platform: str) -> Dict[str, str]:
        """Get API credentials for specific platform"""
        credentials = {
            'N11': {
                'api_key': self.N11_API_KEY,
                'api_secret': self.N11_API_SECRET,
                'api_url': self.N11_API_URL
            },
            'TRENDYOL': {
                'api_key': self.TRENDYOL_API_KEY,
                'api_secret': self.TRENDYOL_API_SECRET,
                'seller_id': self.TRENDYOL_SELLER_ID
            },
            'AMAZON': {
                'access_key_id': self.AWS_ACCESS_KEY_ID,
                'secret_access_key': self.AWS_SECRET_ACCESS_KEY,
                'region': self.AWS_REGION,
                'marketplace_id': self.AMAZON_MARKETPLACE_ID
            }
        }
        return credentials.get(platform.upper(), {})

    def validate(self) -> List[str]:
        """Validate configuration"""
        errors = []
        
        # Check required API credentials
        if not all([self.N11_API_KEY, self.N11_API_SECRET]):
            errors.append("N11 API credentials are missing")
            
        if not all([self.TRENDYOL_API_KEY, self.TRENDYOL_API_SECRET]):
            errors.append("Trendyol API credentials are missing")
            
        if not all([self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY]):
            errors.append("AWS credentials are missing")
            
        # Check numeric values
        if self.API_TIMEOUT < 1:
            errors.append("API_TIMEOUT must be greater than 0")
            
        if self.MAX_RETRIES < 1:
            errors.append("MAX_RETRIES must be greater than 0")
            
        if self.BATCH_SIZE < 1:
            errors.append("BATCH_SIZE must be greater than 0")
            
        return errors
