import logging
from rich.logging import RichHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Adjust the log level as needed

# Create a file handler
file_handler = logging.FileHandler('app/logs/app.log')
file_handler.setLevel(logging.INFO)  # Adjust the file handler level

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)
logger.addHandler(RichHandler())