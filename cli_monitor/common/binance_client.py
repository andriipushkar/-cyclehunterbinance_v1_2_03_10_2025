"""
Цей модуль надає клас-обгортку (`BinanceClient`) для взаємодії з API біржі Binance.

Він інкапсулює логіку для виконання основних запитів до API, таких як
отримання балансів, цін, інформації про біржу та торгових комісій,
а також обробку можливих помилок.
"""

import logging
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .config import config
from .exceptions import SymbolPriceError

class BinanceClient:
    """Клас-обгортка для клієнта API Binance."""

    def __init__(self):
        """
        Ініціалізує клієнт Binance.

        Використовує API ключ та секрет з конфігурації для створення екземпляра
        клієнта. Також виконує `ping` до сервера Binance для перевірки
        з'єднання та валідності ключів.

        Raises:
            BinanceAPIException: Якщо виникає помилка з боку API Binance.
            BinanceRequestException: Якщо виникає помилка під час запиту.
        """
        # Кеш для зберігання торгових комісій, щоб уникнути повторних запитів
        self._trade_fees = {}
        try:
            self.client = Client(config.api_key, config.api_secret)
            # Перевірка з'єднання
            self.client.ping()
            logging.info("Успішно підключено до API Binance.")
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка підключення до API Binance: {e}")
            # Перевикликаємо виняток, щоб програма, яка використовує клієнт, знала про помилку
            raise

    def get_spot_balance(self):
        """
        Отримує баланс спотового гаманця.

        Returns:
            list: Список словників, що представляють баланси активів.
                  Повертає тільки активи з балансом більше нуля.
                  Приклад: [{"asset": "BTC", "total": "0.1"}]
        """
        try:
            account = self.client.get_account()
            balances = account.get('balances', [])
            # Фільтруємо активи, залишаючи тільки ті, що мають позитивний баланс
            return [
                {"asset": b["asset"], "total": b["free"]}
                for b in balances
                if float(b["free"]) > 0
            ]
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка отримання спотового балансу: {e}")
            return []

    def get_futures_balance(self):
        """
        Отримує баланс ф'ючерсного гаманця.

        Returns:
            list: Список словників, що представляють баланси активів.
                  Приклад: [{"asset": "USDT", "balance": "1000"}]
        """
        try:
            account = self.client.futures_account_balance()
            return [
                {"asset": b["asset"], "balance": b["balance"]}
                for b in account
                if float(b["balance"]) > 0
            ]
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка отримання ф'ючерсного балансу: {e}")
            return []

    def get_symbol_price(self, asset):
        """
        Отримує ціну активу відносно USDT.

        Args:
            asset (str): Назва активу (наприклад, "BTC").

        Returns:
            float: Ціна активу в USDT.

        Raises:
            SymbolPriceError: Якщо не вдається отримати ціну для вказаного активу.
        """
        # Для стейблкоїнів ціна завжди приблизно 1.0 USDT
        if asset in ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'PAX', 'HUSD']:
            return 1.0
        try:
            # Формуємо тікер (наприклад, "BTCUSDT") і запитуємо ціну
            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
            return float(ticker['price'])
        except (BinanceAPIException, BinanceRequestException) as e:
            raise SymbolPriceError(f"Не вдалося отримати ціну для {asset}: {e}") from e

    def get_earn_balance(self):
        """
        Отримує баланс гаманця "Earn" (Simple Earn).

        Збирає інформацію з гнучких (Flexible) та заблокованих (Locked) позицій.

        Returns:
            list: Список словників, що представляють баланси в Earn.
                  Приклад: [{"asset": "BNB", "total": "10.5"}]
        """
        earn_balances = []
        try:
            # Отримуємо позиції з гнучким доходом
            flexible_positions = self.client.get_simple_earn_flexible_product_position()
            if flexible_positions and 'rows' in flexible_positions:
                for position in flexible_positions['rows']:
                    earn_balances.append({"asset": position['asset'], "total": position['totalAmount']})

            # Отримуємо позиції з фіксованим доходом
            locked_positions = self.client.get_simple_earn_locked_product_position()
            if locked_positions and 'rows' in locked_positions:
                for position in locked_positions['rows']:
                    # Перевіряємо, чи такий актив вже є у списку, щоб додати суму
                    found = False
                    for balance in earn_balances:
                        if balance['asset'] == position['asset']:
                            balance['total'] = str(float(balance['total']) + float(position['amount']))
                            found = True
                            break
                    # Якщо активу немає, додаємо його
                    if not found:
                        earn_balances.append({"asset": position['asset'], "total": position['amount']})
            return earn_balances
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Не вдалося отримати баланс Earn: {e}")
            return []

    def get_exchange_info(self):
        """
        Отримує загальну інформацію про біржу (ліміти, торгові пари тощо).

        Returns:
            dict: Словник з повною інформацією про біржу.
        """
        try:
            return self.client.get_exchange_info()
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка отримання інформації про біржу: {e}")
            return None

    def get_24h_ticker(self):
        """
        Отримує статистику цін за останні 24 години для всіх пар.

        Returns:
            list: Список словників зі статистикою для кожної торгової пари.
        """
        try:
            return self.client.get_ticker()
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка отримання 24-годинного тікера: {e}")
            return []

    def get_trade_fees(self):
        """
        Отримує торгові комісії для всіх пар і кешує їх.

        Returns:
            dict: Словник, де ключ - символ пари, а значення - комісія тейкера.
        """
        # Якщо комісії вже закешовані, повертаємо їх
        if self._trade_fees:
            return self._trade_fees
        try:
            fees = self.client.get_trade_fee()
            if fees and 'tradeFee' in fees:
                for fee in fees['tradeFee']:
                    self._trade_fees[fee['symbol']] = Decimal(fee['takerCommission'])
            return self._trade_fees
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Помилка отримання торгових комісій: {e}")
            return {}

    def get_trade_fee(self, symbol):
        """
        Отримує торгову комісію для конкретної торгової пари.

        Якщо комісії ще не завантажені, спочатку завантажує їх усі.
        Якщо комісія для конкретної пари не знайдена, робить окремий запит.

        Args:
            symbol (str): Символ торгової пари (наприклад, "BTCUSDT").

        Returns:
            Decimal: Розмір комісії тейкера або None, якщо не знайдено.
        """
        # Завантажуємо всі комісії, якщо кеш порожній
        if not self._trade_fees:
            self.get_trade_fees()
        
        # Якщо комісії для символу немає в кеші, робимо окремий запит
        if symbol not in self._trade_fees:
            try:
                fees = self.client.get_trade_fee(symbol=symbol)
                if fees and 'tradeFee' in fees and len(fees['tradeFee']) > 0:
                    fee = Decimal(fees['tradeFee'][0]['takerCommission'])
                    self._trade_fees[symbol] = fee
                    return fee
                return None
            except (BinanceAPIException, BinanceRequestException) as e:
                logging.error(f"Помилка отримання комісії для {symbol}: {e}")
                return None

        return self._trade_fees.get(symbol)

    def create_market_order(self, symbol, side, quantity, dry_run=True):
        """
        Створює ринковий ордер (Market Order).

        Args:
            symbol (str): Символ пари (наприклад, "BTCUSDT").
            side (str): 'BUY' або 'SELL'.
            quantity (Decimal): Кількість для купівлі/продажу.
            dry_run (bool): Якщо True, ордер не буде відправлено, лише залоговано.

        Returns:
            dict: Результат виконання ордера (симуляція для dry_run).
        """
        logging.info(f"[DRY RUN] Спроба створити ордер: {side} {quantity} {symbol}")
        
        if dry_run:
            logging.info("[DRY RUN] Ордер не відправлено.")
            # Симулюємо успішну відповідь від Binance
            return {
                "symbol": symbol,
                "orderId": "DRY_RUN_ORDER",
                "status": "FILLED",
                "side": side,
                "type": "MARKET",
                "executedQty": str(quantity),
                "cummulativeQuoteQty": "DRY_RUN_TOTAL",
            }

        # --- ЛОГІКА ДЛЯ РЕАЛЬНОЇ ТОРГІВЛІ (ВИМКНЕНО) ---
        # try:
        #     # Для реальної торгівлі розкоментуйте наступний рядок
        #     # і переконайтеся, що ваші API ключі мають права на торгівлю.
        #     # order = self.client.create_order(
        #     #     symbol=symbol,
        #     #     side=side,
        #     #     type=Client.ORDER_TYPE_MARKET,
        #     #     quantity=float(quantity)
        #     # )
        #     # logging.info(f"РЕАЛЬНИЙ ОРДЕР ВІДПРАВЛЕНО: {order}")
        #     # return order
        # except BinanceAPIException as e:
        #     logging.error(f"Помилка створення реального ордера: {e}")
        #     raise
        # ----------------------------------------------------
        
        return None # Повертаємо None, якщо dry_run=False і реальна логіка закоментована