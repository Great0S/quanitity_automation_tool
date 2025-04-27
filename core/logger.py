import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_rich_traceback

class CustomLogger:
    """
    Custom logger implementation with advanced features
    - Console logging with rich formatting
    - File logging with rotation
    - JSON formatting for structured logging
    - Error tracking
    - Performance monitoring
    """
    
    def __init__(self, name: str = "quantity_automation_tool"):
        self.name = name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create loggers
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handlers()
        
        # Install rich traceback handler
        install_rich_traceback(show_locals=True)
        
        # Performance monitoring
        self.perf_logger = self._setup_performance_logger()
        
        # Error tracking
        self.error_logger = self._setup_error_logger()

    def _setup_console_handler(self) -> None:
        """Setup console handler with rich formatting"""
        console_handler = RichHandler(
            rich_tracebacks=True,
            console=Console(style="blue"),
            show_time=True,
            show_path=True
        )
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(message)s',
            datefmt='[%X]'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handlers(self) -> None:
        """Setup file handlers for different log types"""
        # Main log file with rotation by size
        main_handler = RotatingFileHandler(
            filename=self.log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(self._get_detailed_formatter())
        self.logger.addHandler(main_handler)
        
        # Daily rotating log file
        daily_handler = TimedRotatingFileHandler(
            filename=self.log_dir / "daily.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(self._get_detailed_formatter())
        self.logger.addHandler(daily_handler)
        
        # JSON log file
        json_handler = RotatingFileHandler(
            filename=self.log_dir / "json.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(json_handler)

    def _setup_performance_logger(self) -> logging.Logger:
        """Setup performance logging"""
        perf_logger = logging.getLogger(f"{self.name}.performance")
        perf_logger.setLevel(logging.INFO)
        
        handler = RotatingFileHandler(
            filename=self.log_dir / "performance.log",
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(self._get_json_formatter())
        perf_logger.addHandler(handler)
        
        return perf_logger

    def _setup_error_logger(self) -> logging.Logger:
        """Setup error logging"""
        error_logger = logging.getLogger(f"{self.name}.error")
        error_logger.setLevel(logging.ERROR)
        
        handler = RotatingFileHandler(
            filename=self.log_dir / "error.log",
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(self._get_detailed_formatter())
        error_logger.addHandler(handler)
        
        return error_logger

    def _get_detailed_formatter(self) -> logging.Formatter:
        """Get detailed log formatter"""
        return logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON log formatter"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'function': record.funcName,
                    'line': record.lineno,
                    'message': record.getMessage(),
                }
                
                if hasattr(record, 'props'):
                    log_data.update(record.props)
                
                if record.exc_info:
                    log_data['exception'] = self.formatException(record.exc_info)
                    
                return json.dumps(log_data)
                
        return JsonFormatter()

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = True, **kwargs: Any) -> None:
        """Log error message"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
        
        # Also log to error logger
        if kwargs:
            self.error_logger.error(f"{message} - Context: {kwargs}", exc_info=exc_info)
        else:
            self.error_logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = True, **kwargs: Any) -> None:
        """Log critical message"""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)

    def _log(self, level: int, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Internal logging method"""
        if kwargs:
            record = logging.LogRecord(
                name=self.logger.name,
                level=level,
                pathname=__file__,
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            record.props = kwargs
            self.logger.handle(record)
        else:
            self.logger.log(level, message, exc_info=exc_info)

    def log_performance(self, operation: str, duration: float, **kwargs: Any) -> None:
        """Log performance metrics"""
        log_data = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        self.perf_logger.info('Performance metric', extra={'props': log_data})

    def log_api_request(self, method: str, url: str, status_code: Optional[int] = None,
                       duration: Optional[float] = None, **kwargs: Any) -> None:
        """Log API request details"""
        log_data = {
            'method': method,
            'url': url,
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2) if duration else None,
            **kwargs
        }
        self.info('API Request', **log_data)

# Create global logger instance
logger = CustomLogger()

# Usage examples:
"""
# Basic logging
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Logging with context
logger.info("User action", user_id="123", action="login")

# Performance logging
import time
start_time = time.time()
# ... some operation ...
duration = time.time() - start_time
logger.log_performance("database_query", duration, query_type="select", rows=100)

# API request logging
logger.log_api_request(
    method="GET",
    url="https://api.example.com/data",
    status_code=200,
    duration=0.5,
    response_size=1024
)

# Error logging with exception
try:
    # ... some operation ...
    raise ValueError("Something went wrong")
except Exception as e:
    logger.error("Operation failed", exc_info=True, operation="data_import")
"""
