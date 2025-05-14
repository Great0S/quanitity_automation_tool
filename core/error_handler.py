# core/error_handler.py

import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, Type, TypeVar, cast
import logging

from functools import wraps
import asyncio

from core.logger import logger
from core.exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ValidationError,
    BaseError,
)

T = TypeVar("T", bound=Callable[..., Any])


# Define ServiceError directly in this module
class ServiceError(BaseError):
    """Service error for handling service-related exceptions"""

    pass


class ErrorHandler:
    """
    Global error handler for the application

    Provides centralized error handling and reporting
    """

    def __init__(self) -> None:
        self.logger = logger
        self.error_callbacks: Dict[Type[Exception], Callable[[Exception], Any]] = {}
        self.default_error_callback: Optional[Callable[[Exception], Any]] = None

    def register_error_callback(
        self, error_type: Type[Exception], callback: Callable[[Exception], Any]
    ) -> None:
        """
        Register a callback for a specific error type

        Args:
            error_type: Type of exception to handle
            callback: Function to call when the exception occurs
        """
        self.error_callbacks[error_type] = callback

    def set_default_callback(self, callback: Callable[[Exception], Any]) -> None:
        """
        Set the default error callback

        Args:
            callback: Function to call for unhandled exceptions
        """
        self.default_error_callback = callback

    def handle_error(self, error: Exception) -> Any:
        """
        Handle an error using registered callbacks

        Args:
            error: Exception to handle

        Returns:
            Result of the callback, or None if no callback is registered
        """
        # Log the error
        self.logger.error(f"Error: {str(error)}", exc_info=True)

        # Find the most specific callback
        for error_type, callback in self.error_callbacks.items():
            if isinstance(error, error_type):
                return callback(error)

        # Use default callback if available
        if self.default_error_callback:
            return self.default_error_callback(error)

        # Re-raise if no callback is found
        raise error

    def catch(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator to catch and handle exceptions

        Args:
            func: Function to wrap

        Returns:
            Wrapped function that catches exceptions
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return self.handle_error(e)

        return wrapper

    def catch_async(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator to catch and handle exceptions in async functions

        Args:
            func: Async function to wrap

        Returns:
            Wrapped async function that catches exceptions
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return self.handle_error(e)

        return wrapper

    def format_error_message(self, error: Exception) -> Dict[str, Any]:
        """
        Format an error message for reporting

        Args:
            error: Exception to format

        Returns:
            Formatted error message
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Get traceback
        tb = traceback.format_exception(type(error), error, error.__traceback__)

        # Format error message
        return {
            "error_type": error_type,
            "error_message": error_message,
            "traceback": tb,
            "timestamp": asyncio.get_event_loop().time(),
        }

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with context

        Args:
            error: Exception to log
            context: Additional context information
        """
        error_info = self.format_error_message(error)
        error_message = str(error)

        if context:
            error_info["context"] = context

        # Log the error
        if isinstance(error, AuthenticationError):
            self.logger.error(f"Authentication error: {error_message}", extra=error_info)
        elif isinstance(error, NetworkError):
            self.logger.error(f"Network error: {error_message}", extra=error_info)
        elif isinstance(error, RateLimitError):
            self.logger.error(f"Rate limit error: {error_message}", extra=error_info)
        elif isinstance(error, APIError):
            self.logger.error(f"API error: {error_message}", extra=error_info)
        elif isinstance(error, ValidationError):
            self.logger.error(f"Validation error: {error_message}", extra=error_info)
        elif isinstance(error, ServiceError):
            self.logger.error(f"Service error: {error_message}", extra=error_info)
        elif isinstance(error, BaseError):
            self.logger.error(f"Application error: {error_message}", extra=error_info)
        else:
            self.logger.error(f"Unexpected error: {error_message}", extra=error_info)

    def report_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Report an error to monitoring service

        Args:
            error: Exception to report
            context: Additional context information
        """
        # Log the error with context if provided, otherwise with an empty dictionary
        self.log_error(error, context if context is not None else {})

        # Here you could add integration with error reporting services
        # like Sentry, Rollbar, etc.
        # For example:
        # if sentry_sdk is available:
        # import sentry_sdk
        # sentry_sdk.capture_exception(error)


# Create a global instance
error_handler = ErrorHandler()


def handle_exceptions(func: T) -> T:
    """
    Decorator to handle exceptions in functions

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that handles exceptions
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler.log_error(e, {"function": func.__name__})
            raise

    return cast(T, wrapper)  # Explicitly cast the wrapper to type T


def safe_execute(
    func: Callable[..., Any], *args: Any, default_value: Optional[Any] = None, **kwargs: Any
) -> Any:
    """
    Safely execute a function and return a default value on error

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default_value: Value to return on error
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function or default value on error
    """
    try:
        if asyncio.iscoroutinefunction(func):
            # This should be run in an async context
            raise ValueError(
                "Cannot use safe_execute with async functions, use safe_execute_async instead"
            )
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.log_error(e, {"function": func.__name__, "args": args, "kwargs": kwargs})
        return default_value


async def safe_execute_async(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    default_value: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """
    Safely execute an async function and return a default value on error

    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        default_value: Value to return on error
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function or default value on error
    """
    try:
        if not asyncio.iscoroutinefunction(func):
            # Convert to async if it's not already
            async def wrapper() -> Any:
                return func(*args, **kwargs)

            return await wrapper()
        return await func(*args, **kwargs)
    except Exception as e:
        error_handler.log_error(e, {"function": func.__name__, "args": args, "kwargs": kwargs})
        return default_value


def setup_global_exception_handler() -> None:
    """
    Setup global exception handler for asyncio
    """
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    
    def handle_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
        exception: Optional[BaseException] = context.get("exception")

        # Check if exception is None
        if exception is None:
            logging.error("No exception found in context")
            return

        # Use the loop to handle the exception (example: schedule a callback)
        loop.call_soon_threadsafe(handle_exception_callback, exception)

        # Log the exception
        logging.error("Exception occurred", exc_info=exception)

    def handle_exception_callback(exception: BaseException) -> None:
        # Define what to do with the exception
        # For example, you could report it to an external monitoring service
        print(f"Handling exception: {exception}")
