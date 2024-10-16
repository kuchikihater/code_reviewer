import logging
from logging.handlers import RotatingFileHandler


log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

log_file = "logs.log"

file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logging setup complete. Logs will be written to 'app.log' and console.")