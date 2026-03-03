import logging
from rich.logging import RichHandler

def setup_logger(name="noorbook_scraper"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    # Prevent duplicate logging to root
    logger.propagate = False
    return logger

logger = setup_logger()
