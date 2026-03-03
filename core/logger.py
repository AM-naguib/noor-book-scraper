import logging
from rich.logging import RichHandler

def setup_logger(name="noorbook_scraper"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        # Console Handler (Rich)
        console_handler = RichHandler(rich_tracebacks=True, markup=True)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File Handler
        try:
            file_handler = logging.FileHandler("scraper.log", encoding="utf-8")
            file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if file logging fails (e.g. permissions)
            pass
            
    # Prevent duplicate logging to root
    logger.propagate = False
    return logger

logger = setup_logger()
