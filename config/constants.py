"""
Application constants
"""

from enum import Enum

class ExportFormat(Enum):
    """Export format options"""
    CSV = 'csv'
    EXCEL = 'xlsx'
    JSON = 'json'
    XML = 'xml'

# MIME types for export formats
MIME_TYPES = {
    ExportFormat.CSV.value: 'text/csv',
    ExportFormat.EXCEL.value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ExportFormat.JSON.value: 'application/json',
    ExportFormat.XML.value: 'application/xml'
}

# API rate limits (requests per minute)
RATE_LIMITS = {
    'default': 60,
    'n11': 30,
    'trendyol': 60,
    'hepsiburada': 120,
    'pazarama': 60,
    'pttavm': 30
}

# Cache TTL (seconds)
CACHE_TTL = {
    'products': 3600,  # 1 hour
    'categories': 86400,  # 24 hours
    'auth_token': 3600  # 1 hour
}

# Task refresh interval (milliseconds)
TASK_REFRESH_INTERVAL = 2000  # 2 seconds