"""
Custom exceptions for the application
"""

class BaseError(Exception):
    """Base exception for all application errors"""
    pass

class APIError(BaseError):
    """Base exception for API errors"""
    pass

class AuthenticationError(APIError):
    """Exception raised when authentication fails"""
    pass

class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded"""
    pass

class NetworkError(APIError):
    """Exception raised when network connection fails"""
    pass

class SyncError(BaseError):
    """Exception raised when synchronization fails"""
    pass

class ExportError(BaseError):
    """Exception raised when data export fails"""
    pass

class ValidationError(BaseError):
    """Exception raised when data validation fails"""
    pass