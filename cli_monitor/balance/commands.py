"""
Цей модуль містить клас `BalanceMonitor`, який реалізує логіку
отримання та моніторингу балансів користувача на біржі Binance.
"""

from loguru import logger
import time
from datetime import datetime
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.utils import save_to_json, format_balances
from cli_monitor.common.exceptions import SymbolPriceError

class BalanceMonitor:
    """Клас для моніторингу та отримання балансів з гаманців Binance."""

    def __init__(self):
        """
        Ініціалізує монітор балансів.
        Створює екземпляр клієнта Binance та визначає список ігнорованих активів.
        """
        self.client = BinanceClient()
        # Активи, які слід ігнорувати при розрахунку загальної вартості
        self.ignored_assets = ['LDBNB', 'LDDOGE', 'ETHW', 'HEMI']

    def _process_balances(self, balances, balance_key='total', min_value=1):
        """
        Обробляє список балансів: фільтрує, конвертує в USD та підсумовує.

        Args:
            balances (list): Список словників з балансами.
            balance_key (str): Ключ у словнику, де зберігається сума активу.
            min_value (int): Мінімальна вартість в USD для включення у відфільтрований список.

        Returns:
            tuple: Кортеж, що містить:
                   - `filtered_balances` (list): Відфільтрований список балансів.
                   - `total_balance_usd` (float): Загальна вартість цих балансів у USD.
        """
        filtered_balances = []
        total_balance_usd = 0
        for balance in balances:
            asset = balance['asset']
            if asset in self.ignored_assets:
                continue
            
            total = float(balance[balance_key])
            try:
                price = self.client.get_symbol_price(asset)
                value = total * price
                total_balance_usd += value
                # Додаємо до відфільтрованого списку тільки ті активи, вартість яких перевищує `min_value`
                if value >= min_value:
                    filtered_balances.append(balance)
            except SymbolPriceError as e:
                logger.warning(e)
                continue
        return filtered_balances, total_balance_usd

    def _get_total_balance_usd(self, balances, balance_key='balance'):
        """
        Розраховує загальну вартість списку балансів у USD.
        
        На відміну від `_process_balances`, цей метод не фільтрує активи за мінімальною вартістю.

        Args:
            balances (list): Список словників з балансами.
            balance_key (str): Ключ у словнику, де зберігається сума активу.

        Returns:
            float: Загальна вартість балансів у USD.
        """
        total_balance_usd = 0
        for balance in balances:
            asset = balance['asset']
            if asset in self.ignored_assets:
                continue
            
            total = float(balance[balance_key])
            try:
                price = self.client.get_symbol_price(asset)
                value = total * price
                total_balance_usd += value
            except SymbolPriceError as e:
                logger.warning(e)
                continue
        return total_balance_usd

    def _get_and_save_balances(self):
        """
        Отримує баланси з усіх гаманців (Spot, Futures, Earn), обробляє їх
        та зберігає результат у JSON файл.

        Returns:
            dict: Словник з усіма даними про баланси.
        """
        # Отримання сирих даних з API
        spot_balances = self.client.get_spot_balance()
        futures_balances = self.client.get_futures_balance()
        earn_balances = self.client.get_earn_balance()

        # Обробка та розрахунок вартості
        filtered_spot_balances, total_spot_balance_usd = self._process_balances(spot_balances)
        total_futures_balance_usd = self._get_total_balance_usd(futures_balances)
        filtered_earn_balances, total_earn_balance_usd = self._process_balances(earn_balances)

        total_balance_usd = total_spot_balance_usd + total_futures_balance_usd + total_earn_balance_usd

        # Формування фінального об'єкта для збереження
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
        save_to_json(balances, "output/balance_output.json")
        return balances

    def get_balances(self):
        """
        Публічний метод для одноразового отримання балансів.
        
        Виводить результат у консоль та зберігає у файли `*.json` та `*.txt`.
        """
        logger.info("Отримання балансів...")
        try:
            balances = self._get_and_save_balances()
            formatted_balances = format_balances(balances["balances"])
            logger.info(f"Баланси успішно отримано.\n{formatted_balances}")
            with open("output/balance_output.txt", "w") as f:
                f.write(formatted_balances)
        except Exception as e:
            logger.error(f"Під час отримання балансів сталася помилка: {e}", exc_info=True)


    def monitor_balances(self):
        """
        Публічний метод для запуску безперервного моніторингу балансів.
        
        Оновлює дані кожну хвилину до зупинки користувачем (Ctrl+C).
        """
        logger.info("Запуск режиму моніторингу. Натисніть Ctrl+C для зупинки.")
        while True:
            try:
                balances = self._get_and_save_balances()
                formatted_balances = format_balances(balances["balances"])
                with open("output/balance_output.txt", "w") as f:
                    f.write(formatted_balances)
                logger.info(f"Дані оновлено о {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(60) # Пауза на 60 секунд
            except KeyboardInterrupt:
                logger.info("Моніторинг зупинено користувачем.")
                break
            except Exception as e:
                logger.error(f"Під час моніторингу сталася помилка: {e}", exc_info=True)
                time.sleep(60)