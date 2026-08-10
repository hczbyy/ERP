"""统一日志：控制台 + 滚动文件，测试与请求日志共用。"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def get_logger(name: str = "erp") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # 避免重复初始化
        return logger
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "auto_test.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


logger = get_logger()