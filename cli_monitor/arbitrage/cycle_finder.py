"""Цей модуль відповідає за пошук потенційних арбітражних циклів на біржі.

Він завантажує інформацію про торгові пари, будує з них граф і знаходить
всі можливі цикли, що починаються і закінчуються в базовій валюті.
"""

import json
import asyncio
import aiofiles
from loguru import logger
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from . import constants

class CycleFinder:
    """
    Клас для пошуку потенційних арбітражних циклів на біржі.

    Аналізує доступні торгові пари, будує з них граф та знаходить замкнені 
    ланцюжки обміну (цикли), які можуть бути використані для арбітражу.
    """

    def __init__(self, client):
        """
        Ініціалізує екземпляр CycleFinder.
        """
        self.client = client
        self.base_currency = config.base_currency
        self.monitored_coins = config.monitored_coins
        self.max_cycle_length = config.max_cycle_length
        self.exchange_info = None
        self.trading_pairs = None

    @classmethod
    async def create(cls):
        """
        Створює та асинхронно ініціалізує екземпляр CycleFinder.
        """
        client = await BinanceClient.create()
        return cls(client)

    async def _get_trading_pairs(self):
        """
        Створює граф торгових пар на основі інформації з біржі.
        """
        if not self.exchange_info:
            self.exchange_info = await self.client.get_exchange_info()

        pairs = {}
        for s in self.exchange_info['symbols']:
            if s['status'] == 'TRADING':
                base = s['baseAsset']
                quote = s['quoteAsset']

                if base not in pairs:
                    pairs[base] = []
                if quote not in pairs:
                    pairs[quote] = []
                pairs[base].append(quote)
                pairs[quote].append(base)
        return pairs

    def _find_cycles_dfs(self, graph, start_node, max_length):
        """
        Знаходить усі прості цикли в графі за допомогою алгоритму пошуку в глибину (DFS).
        """
        cycles = []
        stack = [(start_node, [start_node])]

        while stack:
            (vertex, path) = stack.pop()

            if len(path) > max_length:
                continue

            for neighbor in graph.get(vertex, []):
                if neighbor == start_node and len(path) >= 3:
                    cycles.append(path + [neighbor])
                elif neighbor not in path:
                    stack.append((neighbor, path + [neighbor]))
        return cycles

    import aiofiles

    async def _save_cycles(self, cycles):
        """
        Зберігає знайдені цикли у файли формату JSON та TXT.
        """
        logger.info(f"Знайдено {len(cycles)} потенційних арбітражних циклів.")

        async with aiofiles.open(constants.POSSIBLE_CYCLES_FILE, 'w') as f:
            await f.write(json.dumps(cycles, indent=2))
        logger.info(f"Цикли збережено у {constants.POSSIBLE_CYCLES_FILE}")

        txt_path = constants.POSSIBLE_CYCLES_FILE.replace('.json', '.txt')
        async with aiofiles.open(txt_path, 'w') as f:
            for cycle in cycles:
                await f.write(f"{ ' -> '.join(cycle)}\n")
        logger.info(f"Цикли збережено у {txt_path}")

    async def _get_coins_by_volatility(self):
        """
        Відбирає монети на основі їхньої 24-годинної волатильності.
        """
        logger.info("Відбір монет за стратегією волатильності...")
        tickers = await self.client.get_24h_ticker()
        if not tickers:
            logger.error("Не вдалося отримати дані тікерів для розрахунку волатильності.")
            return set()

        for ticker in tickers:
            try:
                price_change_percent = float(ticker.get('priceChangePercent', 0))
                ticker['volatility'] = abs(price_change_percent)
            except (ValueError, TypeError):
                ticker['volatility'] = 0

        sorted_tickers = sorted(tickers, key=lambda t: t['volatility'], reverse=True)
        
        top_n_pairs = config.whitelist_top_n_pairs
        top_volatile_pairs = sorted_tickers[:top_n_pairs]

        allowed_coins = set([self.base_currency])
        if not self.exchange_info:
            self.exchange_info = await self.client.get_exchange_info()

        for ticker in top_volatile_pairs:
            symbol_info = next((s for s in self.exchange_info['symbols'] if s['symbol'] == ticker['symbol']), None)
            if symbol_info:
                allowed_coins.add(symbol_info['baseAsset'])
                allowed_coins.add(symbol_info['quoteAsset'])
        
        logger.info(f"Відібрано {len(allowed_coins)} монет на основі волатильності.")
        return allowed_coins

    async def get_allowed_coins(self, strategy='liquidity'):
        """
        Повертає набір дозволених монет на основі обраної стратегії.
        """
        if not self.exchange_info:
            try:
                self.exchange_info = await self.client.get_exchange_info()
            except Exception as e:
                logger.error(f"Помилка отримання інформації з біржі Binance: {e}")
                return set()

        allowed_coins = set()
        if strategy == 'liquidity':
            logger.info("Використання 'білого списку' для фільтрації монет.")
            try:
                async with aiofiles.open(constants.WHITELIST_FILE, 'r') as f:
                    content = await f.read()
                    whitelist_data = json.loads(content)
                allowed_coins = set(whitelist_data.get('whitelist_assets', []))
            except FileNotFoundError:
                logger.warning(f"Файл 'білого списку' {constants.WHITELIST_FILE} не знайдено. Спробуйте згенерувати його спочатку.")
                allowed_coins = set(config.whitelist_base_coins + [self.base_currency])
            except json.JSONDecodeError:
                logger.error(f"Помилка декодування JSON з {constants.WHITELIST_FILE}.")
                return set()
        elif strategy == 'volatility':
            allowed_coins = await self._get_coins_by_volatility()
        else:
            logger.info("Використання 'monitored_coins' з конфігурації для фільтрації.")
            allowed_coins = set(self.monitored_coins + [self.base_currency])
        
        return allowed_coins

    async def run(self, strategy='liquidity'):
        """
        Основний метод для запуску процесу пошуку циклів.
        """
        logger.info(f"-- Запуск Пошуку Циклів (Стратегія: {strategy}) --")
        
        allowed_coins = await self.get_allowed_coins(strategy)

        if not allowed_coins:
            logger.error("Список дозволених монет порожній. Пошук неможливий.")
            return

        all_trading_pairs = await self._get_trading_pairs()

        self.trading_pairs = {}
        for coin, neighbors in all_trading_pairs.items():
            if coin in allowed_coins:
                filtered_neighbors = [n for n in neighbors if n in allowed_coins]
                if filtered_neighbors:
                    self.trading_pairs[coin] = filtered_neighbors

        found_cycles = self._find_cycles_dfs(self.trading_pairs, self.base_currency, self.max_cycle_length)

        await self._save_cycles(found_cycles)
        logger.info("-- Пошук Циклів Завершено --")


async def main():
    finder = await CycleFinder.create()
    await finder.run()

if __name__ == '__main__':
    asyncio.run(main())