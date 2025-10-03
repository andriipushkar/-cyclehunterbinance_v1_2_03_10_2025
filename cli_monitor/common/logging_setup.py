"""
Централізоване налаштування логування за допомогою Loguru.
"""

import sys
from loguru import logger

def setup_logging():
    """
    Налаштовує Loguru для розділення логів на різні файли.
    """
    logger.remove()  # Видаляємо стандартний обробник

    # Додаємо обробник для виводу в консоль з рівнем INFO
    logger.add(
        sys.stderr, 
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # Лог для API клієнта
    logger.add(
        "logs/api.log",
        level="DEBUG",
        filter="cli_monitor.common.binance_client",
        rotation="10 MB",
        compression="zip",
        backtrace=True,
        diagnose=True,
        format="{time} {level} {name}:{function}:{line} {message}"
    )

    # Лог для арбітражного модуля
    logger.add(
        "logs/arbitrage.log",
        level="INFO",
        filter=lambda record: "arbitrage" in record["name"],
        rotation="10 MB",
        compression="zip",
        format="{time} {level} {name}:{function}:{line} {message}"
    )

    # Лог для моніторингу балансу
    logger.add(
        "logs/monitor.log",
        level="INFO",
        filter=lambda record: "balance" in record["name"],
        rotation="10 MB",
        compression="zip",
        format="{time} {level} {name}:{function}:{line} {message}"
    )

    logger.info("Логування успішно налаштовано через Loguru.")
