# logging_init.py
import os
import logging
from rich.logging import RichHandler

# Ensure the log directory exists
log_dir = 'app/logs'
os.makedirs(log_dir, exist_ok=True)

# Create a logger
logger = logging.getLogger("quantity_automation_tool")
logger.setLevel(logging.DEBUG)  # Set default logging level

# Create a file handler
file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
file_handler.setLevel(logging.INFO)  # File logging level
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create a RichHandler for console output
rich_handler = RichHandler(rich_tracebacks=True)
rich_handler.setLevel(logging.DEBUG)  # Console logging level

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(rich_handler)

