"""
Цей модуль налаштовує логування для всього додатку з використанням бібліотеки Loguru.
"""

import sys
from loguru import logger
from .config import config

def setup_logging():
    """
    Налаштовує Loguru для асинхронного логування у файл та консоль.
    """
    logger.remove()
    log_level = config.log_level.upper()

    # Логування в консоль
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True,  # Робить логування асинхронним
        backtrace=True,
        diagnose=True
    )

    # Логування у файл
    logger.add(
        "logs/runtime.log",
        level=log_level,
        rotation="10 MB",
        retention="10 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,  # Асинхронне логування
        backtrace=True,
        diagnose=True,
        encoding='utf-8'
    )

    logger.info("Логування налаштовано.")