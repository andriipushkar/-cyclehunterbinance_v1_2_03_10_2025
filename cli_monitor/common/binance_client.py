import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .config import API_KEY, API_SECRET

logging.basicConfig(level=logging.INFO)

class BinanceClient:
    """A wrapper for the Binance API client."""

    def __init__(self):
        """Initializes the BinanceClient."""
        try:
            self.client = Client(API_KEY, API_SECRET)
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
            return None

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
