import logging
from pathlib import Path
from datetime import datetime

def __logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)
            
    log_path = Path('logs')
    file_handler = logging.FileHandler(log_path / f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = __logger()