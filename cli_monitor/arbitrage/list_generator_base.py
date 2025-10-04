"""
Базовий клас для генераторів списків (whitelist, blacklist).
"""

import json
from abc import ABC, abstractmethod
from loguru import logger

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config


class BaseListGenerator(ABC):
    """Абстрактний базовий клас для генераторів списків."""

    def __init__(self):
        """Ініціалізує базовий генератор, завантажуючи необхідні дані."""
        self.client = BinanceClient()
        self.config = config
        self.exchange_info = None
        self.tickers = None

    def _fetch_data(self):
        """Отримує базові дані з біржі."""
        logger.info("Отримання даних з біржі (exchange info, tickers)...")
        self.exchange_info = self.client.get_exchange_info()
        self.tickers = self.client.get_24h_ticker()
        if not self.exchange_info or not self.tickers:
            logger.error("Не вдалося отримати інформацію про біржу або тікери. Скасування.")
            return False
        logger.info(f"Отримано {len(self.exchange_info.get('symbols', []))} символів та {len(self.tickers)} тікерів.")
        return True

    def _save_list(self, data, output_path):
        """
        Зберігає згенерований список у JSON-файл.

        Args:
            data (dict): Дані для збереження.
            output_path (str): Шлях до вихідного файлу.
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Список успішно збережено у {output_path}")
        except IOError as e:
            logger.error(f"Помилка збереження списку у {output_path}: {e}")

    @abstractmethod
    def _generate_list(self):
        """
        Абстрактний метод, який має бути реалізований у класах-нащадках.
        Саме тут міститься унікальна логіка генерації кожного списку.
        """
        pass

    def run(self):
        """Основний метод, що запускає процес генерації списку."""
        if self._fetch_data():
            self._generate_list()
