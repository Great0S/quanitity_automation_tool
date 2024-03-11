from rich import print
import click
from rich import inspect
from rich.color import Color
import logging
from rich.logging import RichHandler


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='app.log', # Specify the log file
                    filemode='a') # Append mode

# Define a handler for console output
console = logging.StreamHandler()
console.setLevel(logging.INFO)  # Set the desired console log level
console.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logging.getLogger('').addHandler(console)

a = 2
b = 0

log = logging.getLogger("rich")
try:
    b=(a / 0)
    print(b)
except Exception:
    log.exception('error')
