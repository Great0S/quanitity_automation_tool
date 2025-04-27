from enum import Enum

class Platform(Enum):
    N11 = 'n11'
    TRENDYOL = 'trendyol'
    AMAZON = 'amazon'
    HEPSIBURADA = 'hepsiburada'
    PAZARAMA = 'pazarama'
    PTTAVM = 'pttavm'
    WORDPRESS = 'wordpress'

class ExportFormat(Enum):
    CSV = 'csv'
    EXCEL = 'excel'
    JSON = 'json'
    XML = 'xml'

class ProductStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    OUT_OF_STOCK = 'out_of_stock'
    PENDING = 'pending'
    REJECTED = 'rejected'

class SyncStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PARTIAL = 'partial'

class ErrorCodes:
    API_ERROR = 'API_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    AUTH_ERROR = 'AUTH_ERROR'
    SYNC_ERROR = 'SYNC_ERROR'
    EXPORT_ERROR = 'EXPORT_ERROR'
    DATABASE_ERROR = 'DATABASE_ERROR'

MIME_TYPES = {
    'csv': 'text/csv',
    'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'json': 'application/json',
    'xml': 'application/xml'
}

DEFAULT_SETTINGS = {
    'items_per_page': 50,
    'max_export_rows': 10000,
    'api_timeout': 30,
    'max_retries': 3,
    'batch_size': 100,
    'auto_refresh_interval': 300
}

FIELD_MAPPINGS = {
    'n11': {
        'sku': 'stockCode',
        'title': 'title',
        'price': 'price',
        'quantity': 'quantity'
    },
    'trendyol': {
        'sku': 'barcode',
        'title': 'title',
        'price': 'salePrice',
        'quantity': 'quantity'
    },
    'amazon': {
        'sku': 'SellerSKU',
        'title': 'Title',
        'price': 'Price',
        'quantity': 'Quantity'
    }
}
