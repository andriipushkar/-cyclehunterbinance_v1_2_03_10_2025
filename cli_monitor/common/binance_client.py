"""
Цей модуль надає клас-обгортку (`BinanceClient`) для взаємодії з API біржі Binance.

Він інкапсулює логіку для виконання основних запитів до API, таких як
отримання балансів, цін, інформації про біржу та торгових комісій,
а також обробку можливих помилок з використанням механізму повторних спроб.
"""

from loguru import logger
from decimal import Decimal
from binance import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
from aiohttp.client_exceptions import ClientConnectorError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import config
from .exceptions import SymbolPriceError

# Створюємо логер для цього модуля


def _log_retry_attempt(retry_state):
    """
    Функція для логування перед кожною повторною спробою.
    Використовується в `before_sleep` декоратора `@retry`.
    """
    logger.warning(
        f"Помилка API, повторна спроба №{retry_state.attempt_number} через "
        f"{retry_state.next_action.sleep:.2f} секунд. Причина: {retry_state.outcome.exception()}"
    )

# Налаштування декоратора retry для всіх методів клієнта
# - 5 спроб
# - Експоненційна затримка (2с, 4с, 8с, 16с)
# - Повтор при мережевих помилках або помилках API Binance (коди 5xx або таймаути)
api_retry = retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((ClientConnectorError, BinanceAPIException, BinanceRequestException)),
    before_sleep=_log_retry_attempt
)

class BinanceClient:
    """Клас-обгортка для клієнта API Binance з вбудованою стійкістю до помилок."""

    def __init__(self):
        """
        Ініціалізує клієнт Binance.
        """
        self._trade_fees = {}
        self.client = None

    @classmethod
    async def create(cls):
        """
        Створює та асинхронно ініціалізує екземпляр BinanceClient.
        """
        self = cls()
        await self._connect()
        return self

    @api_retry
    async def _connect(self):
        """Встановлює з'єднання з Binance API."""
        try:
            self.client = await AsyncClient.create(config.api_key, config.api_secret)
            await self.client.ping()
            logger.info("Успішно підключено до API Binance.")
        except (BinanceAPIException, BinanceRequestException, ClientConnectorError) as e:
            logger.error(f"Помилка підключення до API Binance: {e}")
            raise

    @api_retry
    async def get_spot_balance(self):
        """
        Отримує баланс спотового гаманця.
        """
        account = await self.client.get_account()
        balances = account.get('balances', [])
        return [
            {"asset": b["asset"], "total": b["free"]}
            for b in balances
            if float(b["free"]) > 0
        ]

    @api_retry
    async def get_futures_balance(self):
        """
        Отримує баланс ф'ючерсного гаманця.
        """
        account = await self.client.futures_account_balance()
        return [
            {"asset": b["asset"], "balance": b["balance"]}
            for b in account
            if float(b["balance"]) > 0
        ]

    @api_retry
    async def get_symbol_price(self, asset):
        """
        Отримує ціну активу відносно USDT.
        """
        if asset in ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'PAX', 'HUSD']:
            return 1.0
        try:
            ticker = await self.client.get_symbol_ticker(symbol=f"{asset}USDT")
            return float(ticker['price'])
        except (BinanceAPIException, BinanceRequestException) as e:
            raise SymbolPriceError(f"Не вдалося отримати ціну для {asset}: {e}") from e

    @api_retry
    async def get_earn_balance(self):
        """
        Отримує баланс гаманця "Earn" (Simple Earn).
        """
        earn_balances = []
        flexible_positions = await self.client.get_simple_earn_flexible_product_position()
        if flexible_positions and 'rows' in flexible_positions:
            for position in flexible_positions['rows']:
                earn_balances.append({"asset": position['asset'], "total": position['totalAmount']})

        locked_positions = await self.client.get_simple_earn_locked_product_position()
        if locked_positions and 'rows' in locked_positions:
            for position in locked_positions['rows']:
                found = False
                for balance in earn_balances:
                    if balance['asset'] == position['asset']:
                        balance['total'] = str(float(balance['total']) + float(position['amount']))
                        found = True
                        break
                if not found:
                    earn_balances.append({"asset": position['asset'], "total": position['amount']})
        return earn_balances

    @api_retry
    async def get_exchange_info(self):
        """
        Отримує загальну інформацію про біржу (ліміти, торгові пари тощо).
        """
        return await self.client.get_exchange_info()

    @api_retry
    async def get_24h_ticker(self):
        """
        Отримує статистику цін за останні 24 години для всіх пар.
        """
        return await self.client.get_ticker()

    @api_retry
    async def get_tickers_for_symbols(self, symbols):
        """
        Отримує статистику цін за останні 24 години для списку пар.
        """
        # Використовуємо list comprehension для більш чистого коду
        return [await self.client.get_ticker(symbol=symbol) for symbol in symbols]

    @api_retry
    async def get_trade_fees(self):
        """
        Отримує торгові комісії для всіх пар і кешує їх.
        """
        if self._trade_fees:
            return self._trade_fees
        
        fees = await self.client.get_trade_fee()
        if fees and 'tradeFee' in fees:
            for fee in fees['tradeFee']:
                self._trade_fees[fee['symbol']] = Decimal(fee['takerCommission'])
        return self._trade_fees

    @api_retry
    async def get_trade_fee(self, symbol):
        """
        Отримує торгову комісію для конкретної торгової пари.
        """
        if not self._trade_fees:
            await self.get_trade_fees()
        
        if symbol not in self._trade_fees:
            fees = await self.client.get_trade_fee(symbol=symbol)
            if fees and 'tradeFee' in fees and len(fees['tradeFee']) > 0:
                fee = Decimal(fees['tradeFee'][0]['takerCommission'])
                self._trade_fees[symbol] = fee
                return fee
            return None

        return self._trade_fees.get(symbol)

    @api_retry
    async def get_order_book(self, symbol):
        """
        Отримує стакан ордерів (order book) для вказаної пари.
        """
        return await self.client.get_order_book(symbol=symbol)

    async def create_market_order(self, symbol, side, quantity, dry_run=True):
        """
        Створює ринковий ордер (Market Order).
        Цей метод не обгорнутий в retry, оскільки повторне відправлення ордера може бути небезпечним.
        """
        logger.info(f"[DRY RUN] Спроба створити ордер: {side} {quantity} {symbol}")
        
        if dry_run:
            logger.info("[DRY RUN] Ордер не відправлено.")
            return {
                "symbol": symbol,
                "orderId": "DRY_RUN_ORDER",
                "status": "FILLED",
                "side": side,
                "type": "MARKET",
                "executedQty": str(quantity),
                "cummulativeQuoteQty": "DRY_RUN_TOTAL",
            }
        
        return None

    async def close_connection(self):
        if self.client:
            await self.client.close_connection()
            logger.info("З'єднання з API Binance закрито.")
