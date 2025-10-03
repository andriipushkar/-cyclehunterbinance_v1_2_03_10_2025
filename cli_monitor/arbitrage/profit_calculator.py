"""
Цей модуль реалізує моніторинг прибутковості арбітражних циклів у реальному часі.

Він підключається до WebSocket стрімів Binance для отримання цін, розраховує
прибутковість для знайдених циклів і логує вигідні можливості.
"""

import asyncio
import json
import os
import websockets
import logging
from datetime import datetime
from decimal import Decimal, getcontext
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from cli_monitor.common.utils import structure_cycles_and_get_pairs

from . import constants
from .cycle import Cycle

logging.basicConfig(level=logging.DEBUG)

class ProfitMonitor:
    """Клас для розрахунку та логування арбітражних можливостей."""

    def __init__(self, profitable_cycles_queue=None):
        """Ініціалізує монітор прибутковості."""
        self.profitable_cycles_queue = profitable_cycles_queue
        self.latest_prices = {}  # Словник для зберігання останніх цін (ask/bid)
        self.pair_to_cycles = {}  # Відображення торгової пари на цикли, в які вона входить
        self.latest_profits_by_cycle = {}  # Словник для зберігання останньої розрахованої прибутковості для кожного циклу
        self.profits_lock = asyncio.Lock()  # Блокування для безпечного доступу до `latest_profits_by_cycle`
        self._load_latest_prices()  # Завантаження останніх збережених цін
        self.structured_cycles = []  # Список структурованих об'єктів циклів
        self.tasks = []  # Список для зберігання запущених асинхронних завдань

    def _load_latest_prices(self):
        """Завантажує останні ціни з файлу, якщо він існує."""
        if os.path.exists(constants.LATEST_PRICES_FILE):
            with open(constants.LATEST_PRICES_FILE, 'r') as f:
                self.latest_prices = json.load(f)

    def _write_to_file(self, path, content):
        """Синхронний метод для запису текстового контенту у файл."""
        with open(path, 'w') as f:
            f.write(content)

    def _write_json_to_file(self, path, data):
        """Синхронний метод для запису JSON даних у файл."""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    async def _save_latest_prices(self):
        """Асинхронно зберігає останні ціни у файл."""
        try:
            await asyncio.to_thread(self._write_json_to_file, constants.LATEST_PRICES_FILE, self.latest_prices)
        except Exception as e:
            logging.error(f"Помилка збереження останніх цін: {e}")

    def get_exchange_info_map(self):
        """Отримує інформацію про всі торгові символи і створює з неї словник."""
        try:
            client = BinanceClient()
            exchange_info = client.get_exchange_info()
            return {s['symbol']: s for s in exchange_info['symbols']}
        except Exception as e:
            logging.error(f"Помилка отримання інформації з біржі Binance: {e}")
            return None

    def _load_cycles(self):
        """Завантажує знайдені цикли з файлу."""
        if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
            logging.error(f"Помилка: Не вдалося знайти файл з циклами: {constants.POSSIBLE_CYCLES_FILE}")
            return None
        with open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
            return json.load(f)

    def load_cycles_and_map_pairs(self, symbols_info):
        """Завантажує цикли, структурує їх і створює карту `pair_to_cycles`."""
        cycles_coins = self._load_cycles()
        if cycles_coins is None:
            return [], set()

        structured_cycles_data, all_trade_pairs = structure_cycles_and_get_pairs(cycles_coins, symbols_info)

        self.structured_cycles = [Cycle(c['coins'], c['steps']) for c in structured_cycles_data]

        # Створюємо відображення пари на цикли для швидкого доступу
        for cycle in self.structured_cycles:
            for step in cycle.steps:
                pair = step['pair']
                if pair not in self.pair_to_cycles:
                    self.pair_to_cycles[pair] = []
                self.pair_to_cycles[pair].append(cycle)

        return self.structured_cycles, all_trade_pairs

    async def _write_profits_to_txt(self, sorted_cycles, timestamp):
        """Записує останні прибутки у текстовий файл."""
        txt_content = f"Останнє оновлення: {timestamp}\n\n"
        for cycle_str, profit in sorted_cycles:
            txt_content += f"Цикл: {cycle_str}, Прибуток: {profit:.4f}%\n"
        try:
            await asyncio.to_thread(self._write_to_file, constants.ALL_PROFITS_TXT_FILE, txt_content)
        except Exception as e:
            logging.error(f"Помилка запису в all_profits.txt: {e}")

    async def _write_profits_to_json(self, sorted_cycles, timestamp):
        """Записує останні прибутки у JSON файл."""
        json_data = {
            "last_updated": timestamp,
            "profits": [{"cycle": cycle_str, "profit_pct": f"{profit:.4f}"} for cycle_str, profit in sorted_cycles]
        }
        try:
            await asyncio.to_thread(self._write_json_to_file, constants.ALL_PROFITS_JSON_FILE, json_data)
        except Exception as e:
            logging.error(f"Помилка запису в all_profits.json: {e}")

    async def log_all_profits_periodically(self):
        """Періодично записує останню прибутковість для кожного циклу у файли."""
        while True:
            await asyncio.sleep(2)  # Частота оновлення файлів

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            async with self.profits_lock:
                latest_profits_copy = self.latest_profits_by_cycle.copy()

            all_profits = {}
            for cycle in self.structured_cycles:
                cycle_str = str(cycle)
                all_profits[cycle_str] = latest_profits_copy.get(cycle_str, Decimal('-1.0'))

            sorted_cycles = sorted(all_profits.items(), key=lambda item: item[1], reverse=True)

            await self._write_profits_to_txt(sorted_cycles, timestamp)
            await self._write_profits_to_json(sorted_cycles, timestamp)
            await self._save_latest_prices() # Зберігаємо останні ціни

    async def _log_profitable_opportunity(self, cycle, profit_pct, prices):
        """Логує вигідну можливість і додає її в чергу для бота."""
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        date_dir = os.path.join(constants.OUTPUT_DIR, 'profits', now.strftime('%Y-%m-%d'))
        os.makedirs(date_dir, exist_ok=True)
        
        hour_file_path_txt = os.path.join(date_dir, f"{now.strftime('%H')}.txt")

        txt_log_message = (
            f"[{timestamp}] УСПІХ!\n"
            f"Цикл: {cycle}\n"
            f"ПРИБУТОК: {profit_pct:.4f}%\n"
            f"Ціни: {prices}\n---\n"
        )
        logging.info(txt_log_message)
        with open(hour_file_path_txt, 'a') as f:
            f.write(txt_log_message)
        
        if self.profitable_cycles_queue:
            await self.profitable_cycles_queue.put({"cycle": cycle, "profit_pct": profit_pct, "prices": prices})


    async def calculate_and_log_profit(self, cycle, symbols_info, trade_fees, min_profit_threshold):
        """Розраховує прибуток для циклу та оновлює глобальний словник прибутків."""
        steps = cycle.steps
        
        if not all(s['pair'] in self.latest_prices for s in steps):
            return

        try:
            profit_pct = cycle.calculate_profit(self.latest_prices, symbols_info, trade_fees)
            logging.debug(f"Calculated profit for {cycle}: {profit_pct:.4f}%")
            
            cycle_str = str(cycle)
            async with self.profits_lock:
                self.latest_profits_by_cycle[cycle_str] = profit_pct

            if profit_pct > min_profit_threshold:
                prices = {s['pair']: self.latest_prices[s['pair']] for s in steps}
                await self._log_profitable_opportunity(cycle, profit_pct, prices)

        except (KeyError, ValueError) as e:
            logging.debug(f"Помилка розрахунку для циклу {cycle}: {type(e).__name__} - {e}")

    async def _handle_websocket_message(self, message, symbols_info, trade_fees, min_profit_threshold):
        """Обробляє повідомлення, отримане з WebSocket."""
        data = json.loads(message)['data']
        
        pair_symbol = data['s']
        self.latest_prices[pair_symbol] = {'b': data['b'], 'a': data['a']}
        
        if pair_symbol in self.pair_to_cycles:
            for cycle in self.pair_to_cycles[pair_symbol]:
                await self.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)

    async def listen_to_chunk(self, chunk, symbols_info, trade_fees, min_profit_threshold):
        """Підключається до WebSocket для частини пар і слухає повідомлення."""
        streams = [f'{pair.lower()}@bookTicker' for pair in chunk]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        while True:
            try:
                async with websockets.connect(ws_url, ping_timeout=60) as ws:
                    logging.info(f"Підключено до стріму для {len(chunk)} пар.")
                    while True:
                        message = await ws.recv()
                        await self._handle_websocket_message(message, symbols_info, trade_fees, min_profit_threshold)
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidStatusCode) as e:
                logging.warning(f"Помилка з'єднання WebSocket: {e}. Перепідключення...")
                await asyncio.sleep(5) # Пауза перед перепідключенням
            except Exception as e:
                logging.error(f"Неочікувана помилка WebSocket: {e}")
                break

    def _setup(self):
        """Виконує початкове налаштування монітора."""
        logging.info("Запуск Монітора Прибутковості...")
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        os.makedirs(constants.OUTPUT_DIR, exist_ok=True)

        min_profit_threshold = Decimal(config.min_profit_threshold)

        client = BinanceClient()
        symbols_info = self.get_exchange_info_map()
        if not symbols_info:
            return None, None, None, None

        self.structured_cycles, all_trade_pairs = self.load_cycles_and_map_pairs(symbols_info)
        if not self.structured_cycles:
            logging.warning("Не знайдено валідних циклів для моніторингу.")
            return None, None, None, None

        trade_fees = client.get_trade_fees()

        logging.info(f"Моніторинг {len(self.structured_cycles)} циклів, що включають {len(all_trade_pairs)} пар.")
        return symbols_info, all_trade_pairs, trade_fees, min_profit_threshold

    async def start(self):
        """Основна функція для запуску моніторингу."""
        symbols_info, all_trade_pairs, trade_fees, min_profit_threshold = self._setup()
        if not symbols_info:
            return

        pair_chunks = [list(all_trade_pairs)[i:i + constants.CHUNK_SIZE] for i in range(0, len(all_trade_pairs), constants.CHUNK_SIZE)]

        listener_tasks = [asyncio.create_task(self.listen_to_chunk(chunk, symbols_info, trade_fees, min_profit_threshold)) for chunk in pair_chunks]
        logger_task = asyncio.create_task(self.log_all_profits_periodically())

        self.tasks = listener_tasks + [logger_task]
        await asyncio.gather(*self.tasks)

    async def stop(self):
        """Зупиняє монітор прибутковості, скасовуючи всі завдання."""
        logging.info("Зупинка Монітора Прибутковості...")
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logging.info("Монітор Прибутковості зупинено.")

async def main():
    monitor = ProfitMonitor()
    try:
        await monitor.start()
    except asyncio.CancelledError:
        logging.info("Головне завдання моніторингу було скасовано.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nМоніторинг зупинено користувачем.")