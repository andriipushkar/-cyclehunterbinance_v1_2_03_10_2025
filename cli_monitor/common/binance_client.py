import logging
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .config import config
from .exceptions import SymbolPriceError

class BinanceClient:
    """A wrapper for the Binance API client."""

    def __init__(self):
        """Initializes the BinanceClient."""
        self._trade_fees = {}
        try:
            self.client = Client(config.api_key, config.api_secret)
            # Test connectivity
            self.client.ping()
            logging.info("Successfully connected to Binance API.")
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Error connecting to Binance API: {e}")
            raise

    def get_spot_balance(self):
        """
        Retrieves the spot account balance.

        Returns:
            list: A list of dictionaries representing the spot balances.
        """
        try:
            account = self.client.get_account()
            balances = account.get('balances', [])
            return [
                {"asset": b["asset"], "total": b["free"]}
                for b in balances
                if float(b["free"]) > 0
            ]
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Error fetching spot balance: {e}")
            return []

    def get_futures_balance(self):
        """
        Retrieves the futures account balance.

        Returns:
            list: A list of dictionaries representing the futures balances.
        """
        try:
            account = self.client.futures_account_balance()
            return [
                {"asset": b["asset"], "balance": b["balance"]}
                for b in account
                if float(b["balance"]) > 0
            ]
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Error fetching futures balance: {e}")
            return []

    def get_symbol_price(self, asset):
        """
        Retrieves the price of a symbol in USDT.

        Args:
            asset (str): The asset to get the price for.

        Returns:
            float: The price of the asset in USDT, or None if not found.
        """
        if asset in ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'PAX', 'HUSD']:
            return 1.0
        try:
            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
            return float(ticker['price'])
        except (BinanceAPIException, BinanceRequestException) as e:
            raise SymbolPriceError(f"Could not fetch price for {asset}: {e}") from e

    def get_earn_balance(self):
        """
        Retrieves the earn account balance.

        Returns:
            list: A list of dictionaries representing the earn balances.
        """
        earn_balances = []
        try:
            flexible_positions = self.client.get_simple_earn_flexible_product_position()
            if flexible_positions and 'rows' in flexible_positions:
                for position in flexible_positions['rows']:
                    earn_balances.append({"asset": position['asset'], "total": position['totalAmount']})

            locked_positions = self.client.get_simple_earn_locked_product_position()
            if locked_positions and 'rows' in locked_positions:
                for position in locked_positions['rows']:
                    # Check if the asset already exists in earn_balances to sum them up
                    found = False
                    for balance in earn_balances:
                        if balance['asset'] == position['asset']:
                            balance['total'] = str(float(balance['total']) + float(position['amount']))
                            found = True
                            break
                    if not found:
                        earn_balances.append({"asset": position['asset'], "total": position['amount']})
            return earn_balances
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Could not retrieve earn balance: {e}")
            return []

    def get_exchange_info(self):
        """
        Retrieves the exchange information.

        Returns:
            dict: A dictionary containing the exchange information.
        """
        try:
            return self.client.get_exchange_info()
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Error fetching exchange info: {e}")
            return None

    def get_trade_fees(self):
        """
        Retrieves all trade fees and caches them.

        Returns:
            dict: A dictionary of trade fees.
        """
        if self._trade_fees:
            return self._trade_fees
        try:
            fees = self.client.get_trade_fee()
            if fees and 'tradeFee' in fees:
                for fee in fees['tradeFee']:
                    self._trade_fees[fee['symbol']] = Decimal(fee['takerCommission'])
            return self._trade_fees
        except (BinanceAPIException, BinanceRequestException) as e:
            logging.error(f"Error fetching trade fees: {e}")
            return {}

    def get_trade_fee(self, symbol):
        """
        Retrieves the trade fee for a specific symbol.

        Args:
            symbol (str): The symbol to get the trade fee for.

        Returns:
            Decimal: The trade fee for the symbol, or None if not found.
        """
        if not self._trade_fees:
            self.get_trade_fees()
        
        if symbol not in self._trade_fees:
            try:
                fees = self.client.get_trade_fee(symbol=symbol)
                if fees and 'tradeFee' in fees and len(fees['tradeFee']) > 0:
                    fee = Decimal(fees['tradeFee'][0]['takerCommission'])
                    self._trade_fees[symbol] = fee
                    return fee
                return None
            except (BinanceAPIException, BinanceRequestException) as e:
                logging.error(f"Error fetching trade fee for {symbol}: {e}")
                return None

        return self._trade_fees.get(symbol)
