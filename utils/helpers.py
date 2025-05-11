"""
Helper functions for the application with enhanced functionality
"""

import os
import asyncio
import functools
import time
import uuid
import random
import shutil
import threading
from typing import (
    Dict,
    List,
    Any,
    Tuple,
    TypeVar,
    Callable,
    Awaitable,
    Union,
    Optional,
    Protocol,
    cast,
    Type,
)
from datetime import datetime
import pandas as pd
from core.logger import logger

# Define type aliases for XlsxWriter objects to avoid import errors
# These are structural types that match the XlsxWriter API
class XlsxWorkbook:
    def add_format(self, properties: Dict[str, Any]) -> "XlsxFormat":
        raise NotImplementedError("This method should be implemented by a subclass")

    def add_chartsheet(self, name: str) -> "XlsxChartsheet":
        raise NotImplementedError("This method should be implemented by a subclass")

    def add_chart(self, options: Dict[str, Any]) -> "XlsxChart":
        raise NotImplementedError("This method should be implemented by a subclass")


class XlsxFormat:
    pass


class XlsxWorksheet:
    def write(
        self, row: int, col: int, data: Any, cell_format: Optional[XlsxFormat] = None
    ) -> None: ...
    def set_column(
        self, first_col: int, last_col: int, width: float, cell_format: Optional[XlsxFormat] = None
    ) -> None: ...
    def add_table(
        self, first_row: int, first_col: int, last_row: int, last_col: int, options: Dict[str, Any]
    ) -> None: ...


class XlsxChart:
    def add_series(self, options: Dict[str, str]) -> None: ...
    def set_title(self, options: Dict[str, str]) -> None: ...
    def set_x_axis(self, options: Dict[str, str]) -> None: ...
    def set_y_axis(self, options: Dict[str, str]) -> None: ...
    def set_style(self, style_id: int) -> None: ...


class XlsxChartsheet:
    def set_chart(self, chart: XlsxChart) -> None: ...


T = TypeVar("T")


# Define a Protocol for tasks with get_progress method
class ProgressReporter(Protocol):
    def get_progress(self) -> float: ...


# Type alias for asyncio.Task with optional get_progress method
TaskWithProgress = Union[asyncio.Task, ProgressReporter]


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures

    The circuit breaker has three states:
    - CLOSED: All requests are allowed
    - OPEN: All requests are blocked
    - HALF-OPEN: A limited number of requests are allowed to test if the service is healthy
    """

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: int = 30, half_open_max_calls: int = 3
    ):
        """
        Initialize the circuit breaker

        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before transitioning from OPEN to HALF-OPEN
            half_open_max_calls: Maximum number of calls allowed in HALF-OPEN state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = "CLOSED"
        self.failures = 0
        self.successes = 0
        self.last_failure_time = 0
        self.half_open_calls = 0

        self._lock = threading.RLock()

    def allow_request(self) -> bool:
        """Check if a request should be allowed"""
        with self._lock:
            if self.state == "CLOSED":
                return True

            if self.state == "OPEN":
                # Check if recovery timeout has elapsed
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF-OPEN"
                    self.half_open_calls = 0
                    logger.info("Circuit breaker state changed from OPEN to HALF-OPEN")
                    return True
                return False

            if self.state == "HALF-OPEN":
                # Allow limited calls in HALF-OPEN state
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

            return False  # Default safety

    def record_success(self) -> None:
        """Record a successful call"""
        with self._lock:
            self.failures = 0  # Reset failure count

            if self.state == "HALF-OPEN":
                self.successes += 1
                if self.successes >= self.half_open_max_calls:
                    self.state = "CLOSED"
                    self.successes = 0
                    logger.info("Circuit breaker state changed from HALF-OPEN to CLOSED")

    def record_failure(self) -> None:
        """Record a failed call"""
        with self._lock:
            self.failures += 1
            self.last_failure_time = int(time.time())

            if self.state == "CLOSED" and self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker state changed to OPEN after {self.failures} failures"
                )

            if self.state == "HALF-OPEN":
                self.state = "OPEN"
                self.successes = 0
                logger.warning(
                    "Circuit breaker state changed from HALF-OPEN to OPEN due to failure"
                )

    def reset(self) -> None:
        """Reset the circuit breaker to CLOSED state"""
        with self._lock:
            self.state = "CLOSED"
            self.failures = 0
            self.successes = 0
            self.half_open_calls = 0
            logger.info("Circuit breaker has been reset to CLOSED state")


def retry_async(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> Callable[..., Callable[..., Awaitable[object]]]:
    """
    Enhanced retry decorator for async functions with circuit breaker support

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Exceptions to catch and retry
        circuit_breaker: Optional circuit breaker instance to prevent cascading failures

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: BaseException = RuntimeError("Function execution failed with no specific exception")
            current_delay = delay

            # Check if circuit breaker is open
            if circuit_breaker and not circuit_breaker.allow_request():
                raise CircuitBreakerOpenError(f"Circuit breaker is open for {func.__name__}")

            # Add metadata for tracking
            operation_id = kwargs.pop("operation_id", None) or str(uuid.uuid4())
            start_time = time.time()

            for attempt in range(max_retries):
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)

                    # Record successful execution if using circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_success()

                    # Log performance metrics
                    execution_time = time.time() - start_time
                    logger.debug(f"Operation {operation_id} completed in {execution_time:.2f}s")

                    return result

                except exceptions as e:
                    last_exception = e

                    # Record failure if using circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    # Log the retry attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for operation {operation_id} failed: {str(e)}"
                    )

                    # Apply backoff and delay
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # Add context to the exception
            if hasattr(last_exception, "add_note"):  # Python 3.11+ feature
                last_exception.add_note(f"Failed after {max_retries} retries")

            raise last_exception

        # Preserve function metadata
        functools.update_wrapper(wrapper, func)
        return wrapper

    return decorator

class CircuitBreakerOpenError(Exception):
    """Exception raised when a circuit breaker is open"""

    pass


def run_async(async_func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """
    Helper function to run async code in Streamlit

    This is an improved version that supports progress tracking and cancellation

    Args:
        async_func: Async function to run
        *args: Arguments to pass to the async function
        **kwargs: Keyword arguments to pass to the async function

    Returns:
        Result of the async function
    """
    import asyncio
    import concurrent.futures

    # Extract progress callback if provided
    progress_callback = kwargs.pop("progress_callback", None)
    timeout = kwargs.pop("timeout", None)

    # Define a function to run in a new thread
    def run_in_thread(
        async_func: Callable[..., Any],
        *args: Any,
        progress_callback: Optional[Callable[[float], None]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Run an asynchronous function in a separate thread.

        Args:
            async_func: The asynchronous function to run.
            *args: Positional arguments for the async function.
            progress_callback: Optional callback to report progress.
            timeout: Optional timeout for the async function.
            **kwargs: Keyword arguments for the async function.

        Returns:
            The result of the async function.
        """
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Create the coroutine
            if asyncio.iscoroutinefunction(async_func):
                coro = async_func(*args, **kwargs)
            else:
                raise TypeError("Provided async_func must be an async function")

            # If we have a progress callback, wrap the coroutine
            if progress_callback:
                # Create a task to allow progress reporting
                task = asyncio.ensure_future(coro, loop=loop)

                # Monitor the task for progress
                async def monitor_progress() -> None:
                    while not task.done():
                        # Report progress if the task has a get_progress method
                        # Using getattr with default None to avoid AttributeError
                        get_progress_fn = getattr(task, "get_progress", None)
                        if callable(get_progress_fn):
                            progress = get_progress_fn()
                            if progress is not None:
                                if isinstance(progress, (int, float)):
                                    progress_callback(float(progress))
                                else:
                                    logger.warning(f"Progress value {progress} is not convertible to float")
                        await asyncio.sleep(0.1)

                # Run both the task and the monitor
                monitor_task = asyncio.ensure_future(monitor_progress(), loop=loop)

                # Wait for the main task to complete
                if timeout:
                    return loop.run_until_complete(asyncio.wait_for(task, timeout))
                else:
                    result = loop.run_until_complete(task)

                # Cancel the monitor task
                monitor_task.cancel()
                try:
                    loop.run_until_complete(monitor_task)
                except asyncio.CancelledError:
                    pass

                return result
            else:
                # Run without progress monitoring
                if timeout:
                    return loop.run_until_complete(asyncio.wait_for(coro, timeout))
                else:
                    return loop.run_until_complete(coro)
        finally:
            # Clean up the loop
            loop.close()

    # Use ThreadPoolExecutor for better thread management
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread, async_func, *args, **kwargs)
        try:
            return future.result()
        except concurrent.futures.TimeoutError:
            # Convert timeout to string safely
            timeout_str = "unknown" if timeout is None else str(timeout)
            logger.error(f"Operation timed out after {timeout_str} seconds")
            raise TimeoutError(f"Operation timed out after {timeout_str} seconds")
        except Exception as e:
            logger.error(f"Error in async operation: {str(e)}")
            raise


def validate_sku(sku: str) -> bool:
    """
    Validate SKU format

    Args:
        sku: SKU to validate

    Returns:
        True if valid, False otherwise
    """
    if not sku:
        return False

    # SKU should be alphanumeric with optional hyphens and underscores
    import re

    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, sku))


def parse_date(date_str: str) -> datetime:
    """
    Parse date string in various formats

    Args:
        date_str: Date string

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If the date format is not recognized
    """
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Date format not recognized: {date_str}")


def format_price(price: Union[float, str], currency: str = "TRY", decimal_places: int = 2) -> str:
    """
    Format price with currency

    Args:
        price: Price value
        currency: Currency code
        decimal_places: Number of decimal places

    Returns:
        Formatted price string
    """
    try:
        # Convert to float if string
        if isinstance(price, str):
            price = float(price.replace(",", "."))

        # Format with specified decimal places
        formatted = f"{price:.{decimal_places}f}"

        # Add currency symbol
        currency_symbols = {"TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"}

        symbol = currency_symbols.get(currency, currency)
        return f"{symbol}{formatted}"
    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting price {price}: {str(e)}")
        return f"{currency}0.00"


def create_excel_report(
    data: List[Dict[str, Any]],
    file_path: str,
    sheet_name: str = "Report",
    styling: bool = True,
    include_charts: bool = False,
    template_path: str = "",
) -> None:
    """
    Create enhanced Excel report from data with styling and optional charts

    Args:
        data: List of dictionaries to save
        file_path: Path to the Excel file
        sheet_name: Name of the sheet
        styling: Whether to apply styling to the Excel file
        include_charts: Whether to include charts in the report
        template_path: Optional path to a template Excel file
    """
    try:
        if not data:
            logger.warning(f"No data to save to {file_path}")
            return

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Determine if we should use a template
        if template_path and os.path.exists(template_path):
            # Copy template to destination
            shutil.copy2(template_path, file_path)
            mode = "a"  # Append mode
        else:
            mode = "w"  # Write mode

        # Save to Excel
        with pd.ExcelWriter(
            file_path, engine="xlsxwriter", mode="a" if mode == "a" else "w"
        ) as writer:
            # Write data
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Get workbook and worksheet objects
            # Use type annotations to help the type checker
            workbook = cast(XlsxWorkbook, getattr(writer, "book", None))
            worksheet = cast(XlsxWorksheet, writer.sheets.get(sheet_name))

            if styling and workbook is not None and worksheet is not None:
                # Define formats
                header_format = workbook.add_format(
                    {
                        "bold": True,
                        "text_wrap": True,
                        "valign": "top",
                        "fg_color": "#D7E4BC",
                        "border": 1,
                    }
                )

                numeric_format = workbook.add_format({"num_format": "#,##0.00", "align": "right"})

                date_format = workbook.add_format({"num_format": "yyyy-mm-dd", "align": "center"})

                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Apply data formats based on column types
                for i, col in enumerate(df.columns):
                    # Detect column type
                    col_dtype = str(df[col].dtype)
                    if col_dtype in ["float64", "int64"] or col.lower() in [
                        "price",
                        "amount",
                        "cost",
                        "revenue",
                    ]:
                        worksheet.set_column(i, i, 12, numeric_format)
                    elif col.lower() in ["date", "created_at", "updated_at"]:
                        worksheet.set_column(i, i, 12, date_format)
                    else:
                        # Auto-adjust column widths
                        max_len = 0
                        if len(df) > 0:
                            # Calculate max length safely
                            col_lengths = df[col].astype(str).str.len()
                            if not col_lengths.empty:
                                max_col_len = col_lengths.max()
                                if not pd.isna(max_col_len):
                                    max_len = int(max_col_len)

                        # Ensure max_len is at least the length of the column name
                        max_len = max(max_len, len(col)) + 2
                        worksheet.set_column(i, i, max_len)

                # Add table with filtering
                table_options = {
                    "columns": [{"header": col} for col in df.columns],
                    "style": "Table Style Medium 2",
                    "first_column": False,
                    "last_column": False,
                    "banded_rows": True,
                }
                worksheet.add_table(0, 0, len(df), len(df.columns) - 1, table_options)

            if include_charts and len(df) > 0 and workbook is not None:
                # Create chart sheet
                chart_sheet = workbook.add_chartsheet(f"{sheet_name} Chart")

                # Try to identify numeric columns for charting
                numeric_cols = df.select_dtypes(include=["number"]).columns

                if len(numeric_cols) > 0:
                    # Create chart
                    chart = workbook.add_chart({"type": "column"})

                    # Add series to the chart
                    for i, col in enumerate(numeric_cols[:3]):  # Limit to first 3 numeric columns
                        # Get column index safely
                        try:
                            col_idx = df.columns.get_loc(col)
                            if isinstance(col_idx, int):
                                # Calculate Excel column letter
                                if col_idx < 26:
                                    col_letter = chr(65 + col_idx)  # A-Z
                                else:
                                    # For columns beyond Z (AA, AB, etc.)
                                    first_letter = chr(64 + (col_idx // 26))
                                    second_letter = chr(65 + (col_idx % 26))
                                    col_letter = f"{first_letter}{second_letter}"

                                chart.add_series(
                                    {
                                        "name": f"={sheet_name}!${col_letter}$1",
                                        "categories": f"={sheet_name}!$A$2:$A${len(df) + 1}",
                                        "values": f"={sheet_name}!${col_letter}$2:${col_letter}${len(df) + 1}",
                                    }
                                )
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Error adding chart series for column {col}: {str(e)}")

                    # Configure the chart
                    chart.set_title({"name": f"{sheet_name} Summary"})
                    chart.set_x_axis({"name": str(df.columns[0])})
                    chart.set_y_axis({"name": "Values"})
                    chart.set_style(11)

                    # Insert the chart into the chart sheet
                    chart_sheet.set_chart(chart)

        logger.info(f"Enhanced Excel report saved to {file_path}")
    except Exception as e:
        logger.error(f"Error creating Excel report {file_path}: {str(e)}")
        raise
