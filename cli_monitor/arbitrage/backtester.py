"""
Цей модуль надає функціонал для бектестування арбітражних стратегій на історичних даних.

Він завантажує історичні дані про ціни (K-лінії) для потрібних торгових пар,
симулює виконання циклів у минулому та логує потенційно прибуткові угоди.
"""

import asyncio
import json
import os
import argparse
import sys
import aiofiles
from datetime import datetime
from decimal import getcontext

from loguru import logger
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

    def __init__(self, start_date, end_date, client):
        """
        Ініціалізує бектестер.

        Args:
            start_date (str): Початкова дата для бектестування у форматі 'YYYY-MM-DD'.
            end_date (str): Кінцева дата для бектестування у форматі 'YYYY-MM-DD'.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.client = client
        self.min_profit_threshold = config.min_profit_threshold
        self.symbols_info = None
        self.trade_fees = None

    @classmethod
    async def create(cls, start_date, end_date):
        client = await BinanceClient.create()
        return cls(start_date, end_date, client)

    async def _load_cycles(self):
        """Завантажує цикли з файлу `possible_cycles.json`."""
        if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
            logger.error("Помилка: Файл з циклами не знайдено.")
            return None
        async with aiofiles.open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def _get_historical_klines(self, symbol, start_str, end_str):
        """
        Отримує історичні дані K-ліній (свічок) для вказаного символу.
        """
        logger.info(f"Отримання K-ліній для {symbol} з {start_str} по {end_str}...")
        try:
            return await self.client.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_str, end_str)
        except Exception as e:
            logger.error(f"Помилка отримання K-ліній для {symbol}: {e}")
            return []

    async def _fetch_and_align_historical_data(self, all_pairs):
        """
        Завантажує та вирівнює історичні дані для всіх торгових пар.
        """
        logger.info("Завантаження та вирівнювання історичних даних...")
        aligned_prices = {}
        tasks = [self._get_historical_klines(pair, self.start_date, self.end_date) for pair in all_pairs]
        results = await asyncio.gather(*tasks)

        for pair, klines in zip(all_pairs, results):
            for kline in klines:
                timestamp = int(kline[0] / 60000)
                if timestamp not in aligned_prices:
                    aligned_prices[timestamp] = {}
                aligned_prices[timestamp][pair] = kline[4]
        return aligned_prices

    async def _run_simulation(self, structured_cycles, aligned_prices):
        """
        Запускає симуляцію бектестування та логує прибуткові можливості.
        """
        logger.info("Запуск симуляції...")
        profitable_count = 0
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        log_file = os.path.join(constants.LOG_DIR, 'backtest_results.log')

        async with aiofiles.open(log_file, 'w') as f:
            await f.write(f"Бектест з {self.start_date} по {self.end_date}\n---\n")

            for timestamp in sorted(aligned_prices.keys()):
                prices_at_timestamp = aligned_prices[timestamp]
                adapted_prices = {pair: {"a": price, "b": price} for pair, price in prices_at_timestamp.items()}

                for cycle in structured_cycles:
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
                        await f.write(log_message)

        logger.info(f"Симуляцію завершено. Знайдено {profitable_count} прибуткових можливостей.")
        logger.info(f"Результати збережено у {log_file}")

    async def run(self):
        """Основний метод для запуску процесу бектестування."""
        logger.info("--- Запуск Бектесту ---")
        self.symbols_info = {s['symbol']: s for s in (await self.client.get_exchange_info())['symbols']}
        self.trade_fees = await self.client.get_trade_fees()

        cycles_coins = await self._load_cycles()
        if not cycles_coins:
            return

        structured_cycles_data, all_pairs = structure_cycles_and_get_pairs(cycles_coins, self.symbols_info)
        structured_cycles = [Cycle(c['coins'], c['steps']) for c in structured_cycles_data]

        aligned_prices = await self._fetch_and_align_historical_data(all_pairs)

        await self._run_simulation(structured_cycles, aligned_prices)

        await self.client.close_connection()
        logger.info("--- Бектест Завершено ---")


async def main():
    parser = argparse.ArgumentParser(description="Бектестування арбітражної стратегії.")
    parser.add_argument("start_date", help="Початкова дата для бектестування (YYYY-MM-DD).")
    parser.add_argument("end_date", help="Кінцева дата для бектестування (YYYY-MM-DD).")
    args = parser.parse_args()

    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        logger.error("Помилка: Неправильний формат дати. Будь ласка, використовуйте YYYY-MM-DD.")
        sys.exit(1)

    backtester = await Backtester.create(args.start_date, args.end_date)
    await backtester.run()