import os
import logging, traceback
from pathlib import Path
from datetime import datetime

class Logger:
    # standard logger
    @staticmethod
    def __logger(name: str):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        logger.addHandler(console_handler)

        log_path = Path('logs')
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        file_handler = logging.FileHandler(log_path / f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def __init__(self, name):
        self.s_logger = self.__logger(name)
    
    def debug(self, msg: str):
        self.s_logger.debug(msg)
    
    def info(self, msg: str):
        self.s_logger.info(msg)
    
    def warning(self, msg: str):
        self.s_logger.warning(msg)
    
    def error(self, msg: str, e: Exception = None):
        if e is not None:
            err_msg = traceback.format_exc()
            msg = f"{msg}\n{err_msg}"
        self.s_logger.error(msg)
    
    def critical(self, msg: str):
        self.s_logger.critical(msg)

logger = Logger("app")