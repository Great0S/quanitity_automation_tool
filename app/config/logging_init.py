import logging
from rich.logging import RichHandler
import os

# Ensure the log directory exists
log_dir = 'app/logs'
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Adjust the log level as needed

# Create a file handler
file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
file_handler.setLevel(logging.INFO)  # Adjust the file handler level

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Create a RichHandler for console output
rich_handler = RichHandler(rich_tracebacks=True)
rich_handler.setLevel(logging.DEBUG)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(rich_handler)