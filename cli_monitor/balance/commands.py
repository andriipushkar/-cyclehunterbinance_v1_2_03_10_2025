"""
Цей модуль містить клас `BalanceMonitor`, який реалізує логіку
отримання та моніторингу балансів користувача на біржі Binance.
"""

import asyncio
import aiofiles
from loguru import logger
from datetime import datetime
from cli_monitor.common.config import config
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.utils import save_to_json, format_balances
from cli_monitor.common.exceptions import SymbolPriceError

class BalanceMonitor:
    """Клас для моніторингу та отримання балансів з гаманців Binance."""

    def __init__(self, client):
        """
        Ініціалізує монітор балансів.
        """
        self.client = client

    @classmethod
    async def create(cls):
        client = await BinanceClient.create()
        return cls(client)

    async def _calculate_balances_usd(self, balances, balance_key):
        """
        Розраховує вартість кожного балансу в USD та загальну вартість.
        """
        ignored_assets = config.balance_monitor_ignored_assets
        processed_balances = []
        total_usd = 0
        for balance in balances:
            asset = balance['asset']
            if asset in ignored_assets:
                continue
            
            total = float(balance[balance_key])
            try:
                price = await self.client.get_symbol_price(asset)
                value = total * price
                total_usd += value
                processed_balances.append((balance, value))
            except SymbolPriceError as e:
                logger.warning(e)
                continue
        return processed_balances, total_usd

    async def _process_balances(self, balances, balance_key='total'):
        """
        Обробляє список балансів: фільтрує, конвертує в USD та підсумовує.
        """
        min_value = config.balance_monitor_min_value_to_display
        processed_balances, total_balance_usd = await self._calculate_balances_usd(balances, balance_key)
        
        filtered_balances = [balance for balance, value in processed_balances if value >= min_value]
        
        return filtered_balances, total_balance_usd

    async def _get_total_balance_usd(self, balances, balance_key='balance'):
        """
        Розраховує загальну вартість списку балансів у USD.
        """
        _, total_balance_usd = await self._calculate_balances_usd(balances, balance_key)
        return total_balance_usd

    async def _get_and_save_balances(self):
        """
        Отримує баланси з усіх гаманців (Spot, Futures, Earn), обробляє їх
        та зберігає результат у JSON файл.
        """
        spot_balances = await self.client.get_spot_balance()
        futures_balances = await self.client.get_futures_balance()
        earn_balances = await self.client.get_earn_balance()

        filtered_spot_balances, total_spot_balance_usd = await self._process_balances(spot_balances)
        total_futures_balance_usd = await self._get_total_balance_usd(futures_balances)
        filtered_earn_balances, total_earn_balance_usd = await self._process_balances(earn_balances)

        total_balance_usd = total_spot_balance_usd + total_futures_balance_usd + total_earn_balance_usd

        balances = {
            "balances": {
                "spot": filtered_spot_balances,
                "futures": futures_balances,
                "earn": filtered_earn_balances,
                "total_spot_balance_usd": total_spot_balance_usd,
                "total_futures_balance_usd": total_futures_balance_usd,
                "total_earn_balance_usd": total_earn_balance_usd,
                "total_balance_usd": total_balance_usd,
            }
        }
        await save_to_json(balances, config.balance_monitor_output_json_path)
        return balances

    async def get_balances(self):
        """
        Публічний метод для одноразового отримання балансів.
        """
        logger.info("Отримання балансів...")
        try:
            balances = await self._get_and_save_balances()
            formatted_balances = format_balances(balances["balances"])
            logger.info(f"Баланси успішно отримано.\n{formatted_balances}")
            async with aiofiles.open(config.balance_monitor_output_txt_path, "w") as f:
                await f.write(formatted_balances)
        except Exception as e:
            logger.error(f"Під час отримання балансів сталася помилка: {e}", exc_info=True)
        finally:
            await self.client.close_connection()

    async def monitor_balances(self):
        """
        Публічний метод для запуску безперервного моніторингу балансів.
        """
        logger.info("Запуск режиму моніторингу. Натисніть Ctrl+C для зупинки.")
        while True:
            try:
                balances = await self._get_and_save_balances()
                formatted_balances = format_balances(balances["balances"])
                async with aiofiles.open(config.balance_monitor_output_txt_path, "w") as f:
                    await f.write(formatted_balances)
                logger.info(f"Дані оновлено о {datetime.now().strftime('%H:%M:%S')}")
                await asyncio.sleep(config.balance_monitor_monitoring_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Моніторинг зупинено користувачем.")
                break
            except Exception as e:
                logger.error(f"Під час моніторингу сталася помилка: {e}", exc_info=True)
                await asyncio.sleep(config.balance_monitor_monitoring_interval_seconds)
        await self.client.close_connection()
