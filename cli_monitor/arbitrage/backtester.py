"""
Цей модуль надає функціонал для бектестування арбітражних стратегій на історичних даних.

Він завантажує історичні дані про ціни (K-лінії) для потрібних торгових пар,
симулює виконання циклів у минулому та логує потенційно прибуткові угоди.
"""

import asyncio
import json
import os
from loguru import logger
import argparse
import sys
from datetime import datetime
from decimal import getcontext

from binance.client import Client

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from cli_monitor.common.utils import structure_cycles_and_get_pairs
from .cycle import Cycle
from . import constants


# Встановлюємо точність для розрахунків з Decimal
getcontext().prec = 15

class Backtester:
    """Клас для запуску бектестування арбітражної стратегії на історичних даних."""

    def __init__(self, start_date, end_date):
        """
        Ініціалізує бектестер.

        Args:
            start_date (str): Початкова дата для бектестування у форматі 'YYYY-MM-DD'.
            end_date (str): Кінцева дата для бектестування у форматі 'YYYY-MM-DD'.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.client = BinanceClient()
        self.min_profit_threshold = config.min_profit_threshold
        self.symbols_info = {s['symbol']: s for s in self.client.get_exchange_info()['symbols']}
        self.trade_fees = self.client.get_trade_fees()

    def _load_cycles(self):
        """Завантажує цикли з файлу `possible_cycles.json`."""
        if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
            logging.error("Помилка: Файл з циклами не знайдено.")
            return None
        with open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
            return json.load(f)

    def _get_historical_klines(self, symbol, start_str, end_str):
        """
        Отримує історичні дані K-ліній (свічок) для вказаного символу.

        Args:
            symbol (str): Торгова пара (наприклад, 'BTCUSDT').
            start_str (str): Початкова дата у строковому форматі.
            end_str (str): Кінцева дата у строковому форматі.

        Returns:
            list: Список K-ліній.
        """
        logging.info(f"Отримання K-ліній для {symbol} з {start_str} по {end_str}...")
        try:
            return self.client.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_str, end_str)
        except Exception as e:
            logging.error(f"Помилка отримання K-ліній для {symbol}: {e}")
            return []

    def _fetch_and_align_historical_data(self, all_pairs):
        """
        Завантажує та вирівнює історичні дані для всіх торгових пар.

        Дані вирівнюються похвилинно, щоб для кожної хвилини у нас був зріз цін
        для всіх пар, які нас цікавлять.

        Args:
            all_pairs (set): Множина всіх торгових пар, для яких потрібні дані.

        Returns:
            dict: Словник, де ключ - це мітка часу (timestamp), а значення -
                  словник з цінами закриття для кожної пари в цю хвилину.
        """
        logging.info("Завантаження та вирівнювання історичних даних...")
        aligned_prices = {}
        for pair in all_pairs:
            klines = self._get_historical_klines(pair, self.start_date, self.end_date)
            for kline in klines:
                # Групуємо дані по хвилинах
                timestamp = int(kline[0] / 60000)
                if timestamp not in aligned_prices:
                    aligned_prices[timestamp] = {}
                # Використовуємо ціну закриття (індекс 4)
                aligned_prices[timestamp][pair] = kline[4]
        return aligned_prices

    def _run_simulation(self, structured_cycles, aligned_prices):
        """
        Запускає симуляцію бектестування та логує прибуткові можливості.

        Проходить по кожній хвилині в `aligned_prices`, розраховує прибутковість
        кожного циклу з цими цінами і записує результат, якщо він перевищує поріг.

        Args:
            structured_cycles (list): Список об'єктів `Cycle`.
            aligned_prices (dict): Словник з вирівняними історичними цінами.
        """
        logging.info("Запуск симуляції...")
        profitable_count = 0
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        log_file = os.path.join(constants.LOG_DIR, 'backtest_results.log')

        with open(log_file, 'w') as f:
            f.write(f"Бектест з {self.start_date} по {self.end_date}\n---\n")

            # Ітеруємо по кожній хвилині, для якої є дані
            for timestamp in sorted(aligned_prices.keys()):
                prices_at_timestamp = aligned_prices[timestamp]
                # Адаптуємо формат цін для функції розрахунку
                adapted_prices = {pair: {"a": price, "b": price} for pair, price in prices_at_timestamp.items()}

                for cycle in structured_cycles:
                    # Перевіряємо, чи є ціни для всіх кроків циклу в дану хвилину
                    if not all(s['pair'] in adapted_prices for s in cycle.steps):
                        continue

                    profit_pct = cycle.calculate_profit(adapted_prices, self.symbols_info, self.trade_fees)

                    if profit_pct is not None and profit_pct > self.min_profit_threshold:
                        profitable_count += 1
                        dt_object = datetime.fromtimestamp(timestamp * 60)
                        log_message = (
                            f"[{dt_object.strftime('%Y-%m-%d %H:%M:%S')}] УСПІХ!\n"
                            f"Цикл: {cycle}\n"
                            f"ПРИБУТОК: {profit_pct:.4f}%\n---\n"
                        )
                        f.write(log_message)

        logging.info(f"Симуляцію завершено. Знайдено {profitable_count} прибуткових можливостей.")
        logging.info(f"Результати збережено у {log_file}")

    async def run(self):
        """Основний метод для запуску процесу бектестування."""
        logging.info("--- Запуск Бектесту --- ")
        cycles_coins = self._load_cycles()
        if not cycles_coins:
            return

        structured_cycles_data, all_pairs = structure_cycles_and_get_pairs(cycles_coins, self.symbols_info)
        structured_cycles = [Cycle(c['coins'], c['steps']) for c in structured_cycles_data]

        aligned_prices = self._fetch_and_align_historical_data(all_pairs)

        self._run_simulation(structured_cycles, aligned_prices)

        logging.info("--- Бектест Завершено ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Бектестування арбітражної стратегії.")
    parser.add_argument("start_date", help="Початкова дата для бектестування (YYYY-MM-DD).")
    parser.add_argument("end_date", help="Кінцева дата для бектестування (YYYY-MM-DD).")
    args = parser.parse_args()

    # Валідація формату дати
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        logging.error("Помилка: Неправильний формат дати. Будь ласка, використовуйте YYYY-MM-DD.")
        sys.exit(1)

    backtester = Backtester(args.start_date, args.end_date)
    asyncio.run(backtester.run())
