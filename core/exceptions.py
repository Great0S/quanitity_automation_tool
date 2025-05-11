"""
Custom exceptions for the application
"""

class BaseError(Exception):
    """Base exception class"""
    pass

class AuthenticationError(BaseError):
    """Authentication error"""
    pass

class APIError(BaseError):
    """API error"""
    pass

class ValidationError(BaseError):
    """Validation error"""
    pass

class ConfigurationError(BaseError):
    """Configuration error"""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded error"""
    pass

class NetworkError(APIError):
    """Network connection error"""
    pass

class ResourceNotFoundError(APIError):
    """Resource not found error"""
    pass

class DuplicateResourceError(APIError):
    """Duplicate resource error"""
    pass

class InsufficientPermissionsError(AuthenticationError):
    """Insufficient permissions error"""
    pass

class TokenExpiredError(AuthenticationError):
    """Token expired error"""
    pass
class ExportError(BaseError):
    """Export error"""
    pass