import core.exceptions

class BaseError(Exception):
    """Base exception for the application"""
    pass

class APIError(BaseError):
    """Raised when an API request fails"""
    pass

class ServiceError(BaseError):
    """Raised when a service operation fails"""
    pass

class SyncError(BaseError):
    """Raised when product synchronization fails"""
    pass

class ValidationError(BaseError):
    """Raised when data validation fails"""
    pass

class ConfigError(BaseError):
    """Raised when configuration is invalid"""
    pass

class DatabaseError(BaseError):
    """Raised when a database operation fails"""
    pass
class NetworkError(BaseError):
    """Raised when a network operation fails"""
    pass
class AuthenticationError(BaseError):
    """Raised when authentication fails"""
    pass
class PermissionError(BaseError):
    """Raised when a user does not have permission to perform an action"""
    pass
class RateLimitError(BaseError):
    """Raised when the rate limit for an API is exceeded"""
    pass
class TimeoutError(BaseError):
    """Raised when an operation times out"""
    pass
class NotFoundError(BaseError):
    """Raised when a requested resource is not found"""
    pass
class ExportError(BaseError):
    """Raised when an export operation fails"""
    pass
