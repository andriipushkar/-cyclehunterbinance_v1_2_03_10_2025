"""
Цей модуль визначає головний клас `ArbitrageBot`, який тепер відповідає за
оркестрацію всього процесу арбітражу, включаючи виконання угод.
"""

import asyncio
import logging
import csv
import os
from datetime import datetime
from decimal import Decimal

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config

from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .cycle_finder import CycleFinder
from .profit_calculator import ProfitMonitor


class TradeExecutor:
    """
    Клас, що відповідає за виконання торгових циклів.
    В поточному стані працює в режимі "dry run", імітуючи угоди.
    """

    def __init__(self, client: BinanceClient):
        """Ініціалізує екзекутор."""
        self.client = client
        self.initial_investment = Decimal(config.initial_investment_usd)
        self.min_volume_threshold = Decimal(config.min_trade_volume_usd)
        self.exchange_info = {s['symbol']: s for s in self.client.get_exchange_info()['symbols']}

    async def _log_to_csv(self, cycle_str, profit_pct, initial_amount, final_amount, initial_asset, final_asset):
        """Logs the result of a trade cycle to a CSV file."""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        hour_str = now.strftime('%H')
        
        dir_path = os.path.join('output', 'trades', date_str)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{hour_str}.csv")
        
        file_exists = os.path.isfile(file_path)
        
        fieldnames = [
            'timestamp', 'cycle', 'profit_pct', 
            'initial_asset', 'initial_amount', 
            'final_asset', 'final_amount'
        ]
        
        row_data = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'cycle': cycle_str,
            'profit_pct': f"{profit_pct:.4f}",
            'initial_asset': initial_asset,
            'initial_amount': f"{initial_amount:.8f}",
            'final_asset': final_asset,
            'final_amount': f"{final_amount:.8f}"
        }

        try:
            with open(file_path, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row_data)
        except IOError as e:
            logging.error(f"[CSV LOG] Помилка запису у файл {file_path}: {e}")

    async def execute_cycle(self, profitable_cycle: dict):
        """
        Виконує торговий цикл в режимі "dry run".

        Args:
            profitable_cycle (dict): Словник з інформацією про прибутковий цикл.
        """
        cycle = profitable_cycle['cycle']
        profit_pct = profitable_cycle['profit_pct']
        prices = profitable_cycle['prices']

        # --- Перевірка ліквідності ---
        pairs_in_cycle = [step['pair'] for step in cycle.steps]
        tickers = await asyncio.to_thread(self.client.get_tickers_for_symbols, pairs_in_cycle)

        if not tickers or len(tickers) != len(pairs_in_cycle):
            logging.warning(f"[LIQUIDITY CHECK] Не вдалося отримати дані тікера для циклу {cycle}. Цикл пропущено.")
            return

        for ticker in tickers:
            volume = Decimal(ticker.get('quoteVolume', '0'))
            if volume < self.min_volume_threshold:
                logging.warning(f"[LIQUIDITY CHECK] Пара {ticker['symbol']} має недостатній обсяг торгів (${volume:,.2f}). Поріг: ${self.min_volume_threshold:,.2f}. Цикл {cycle} пропущено.")
                return
        
        logging.info(f"[LIQUIDITY CHECK] Усі пари в циклі {cycle} пройшли перевірку на ліквідність.")
        # --- Кінець перевірки ліквідності ---
        
        logging.info("="*50)
        logging.info(f"[DRY RUN] ОТРИМАНО ПРИБУТКОВИЙ ЦИКЛ: {cycle} | Прибуток: {profit_pct:.4f}%")
        logging.info(f"[DRY RUN] Початкова інвестиція: {self.initial_investment} {cycle.steps[0]['from']}")

        current_amount = self.initial_investment
        current_asset = cycle.steps[0]['from']

        for i, step in enumerate(cycle.steps):
            pair = step['pair']
            from_asset = step['from']
            to_asset = step['to']
            
            if current_asset != from_asset:
                logging.error(f"[DRY RUN] Помилка логіки: поточний актив {current_asset} не співпадає з очікуваним {from_asset}")
                return

            pair_info = self.exchange_info.get(pair)
            if not pair_info:
                logging.error(f"[DRY RUN] Не вдалося знайти інформацію про пару {pair}")
                return

            base_asset = pair_info['baseAsset']
            quote_asset = pair_info['quoteAsset']

            side = None
            if from_asset == quote_asset and to_asset == base_asset:
                side = "BUY"
            elif from_asset == base_asset and to_asset == quote_asset:
                side = "SELL"
            
            if side is None:
                logging.error(f"[DRY RUN] Не вдалося визначити напрямок торгівлі для кроку {step}")
                return

            price = Decimal(prices[pair]['a']) if side == "BUY" else Decimal(prices[pair]['b'])

            if side == "BUY":
                # Купуємо 'to_asset' за 'from_asset'
                quantity_to_buy = current_amount / price
                logging.info(f"[DRY RUN] Крок {i+1}: {side} {quantity_to_buy:.8f} {to_asset} за ціною {price} (пара {pair})")
                current_amount = quantity_to_buy
                current_asset = to_asset
            else: # SELL
                # Продаємо 'from_asset' за 'to_asset'
                quantity_to_sell = current_amount
                logging.info(f"[DRY RUN] Крок {i+1}: {side} {quantity_to_sell:.8f} {from_asset} за ціною {price} (пара {pair})")
                current_amount = quantity_to_sell * price
                current_asset = to_asset
        
        final_amount = current_amount
        final_asset = current_asset

        logging.info(f"[DRY RUN] Очікуваний кінцевий баланс: {final_amount:.8f} {final_asset}")
        logging.info("="*50)

        await self._log_to_csv(
            cycle_str=str(cycle),
            profit_pct=profit_pct,
            initial_amount=self.initial_investment,
            final_amount=final_amount,
            initial_asset=cycle.steps[0]['from'],
            final_asset=final_asset
        )


class ArbitrageBot:
    """Головний клас бота, що керує процесом арбітражу."""

    def __init__(self):
        """Ініціалізує бота."""
        self.profit_monitor = None
        self.client = BinanceClient()
        self.trade_executor = TradeExecutor(self.client)

    async def _perform_setup(self):
        """
        Виконує початкові кроки налаштування.
        """
        logging.info("Початок налаштування...")
        
        logging.info("Генерація білого списку...")
        generate_whitelist()
        
        logging.info("Генерація чорного списку...")
        generate_blacklist()
        
        logging.info("Пошук арбітражних циклів на основі білого списку...")
        finder = CycleFinder()
        finder.run(use_whitelist=True)
        
        logging.info("Налаштування завершено.")

    async def start(self):
        """
        Запускає головний цикл роботи бота.
        """
        try:
            # 1. Виконання налаштувань
            await self._perform_setup()

            # 2. Створення черги та запуск моніторингу
            profitable_cycles_queue = asyncio.Queue()
            self.profit_monitor = ProfitMonitor(profitable_cycles_queue=profitable_cycles_queue)
            monitor_task = asyncio.create_task(self.profit_monitor.start())
            logging.info("Монітор прибутковості запущено. Очікування на вигідні цикли...")

            # 3. Обробка циклів з черги
            while True:
                profitable_cycle = await profitable_cycles_queue.get()
                await self.trade_executor.execute_cycle(profitable_cycle)
                profitable_cycles_queue.task_done()

        except asyncio.CancelledError:
            logging.info("Роботу бота зупинено.")
            if self.profit_monitor:
                await self.profit_monitor.stop()
        except Exception as e:
            logging.error(f"В головному циклі бота сталася неочікувана помилка: {e}", exc_info=True)
            if self.profit_monitor:
                await self.profit_monitor.stop()


async def main():
    """Асинхронна функція для запуску бота."""
    bot = ArbitrageBot()
    await bot.start()
