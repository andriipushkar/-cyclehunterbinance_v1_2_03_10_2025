import logging
import time
from datetime import datetime
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.utils import save_to_json, format_balances, setup_logging
from cli_monitor.common.exceptions import SymbolPriceError

class BalanceMonitor:
    """Monitors and retrieves account balances."""

    def __init__(self):
        self.client = BinanceClient()
        self.ignored_assets = ['LDBNB', 'LDDOGE', 'ETHW', 'HEMI']

    def _process_balances(self, balances, balance_key='total', min_value=1):
        """Filters balances and calculates their total USD value."""
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
                if value >= min_value:
                    filtered_balances.append(balance)
            except SymbolPriceError as e:
                logging.warning(e)
                continue
        return filtered_balances, total_balance_usd

    def _get_total_balance_usd(self, balances, balance_key='balance'):
        """Calculates the total USD value of a list of balances."""
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
                logging.warning(e)
                continue
        return total_balance_usd

    def _get_and_save_balances(self):
        """Fetches balances and saves them to the JSON file."""
        spot_balances = self.client.get_spot_balance()
        futures_balances = self.client.get_futures_balance()
        earn_balances = self.client.get_earn_balance()

        filtered_spot_balances, total_spot_balance_usd = self._process_balances(spot_balances)
        total_futures_balance_usd = self._get_total_balance_usd(futures_balances)
        filtered_earn_balances, total_earn_balance_usd = self._process_balances(earn_balances)

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
        save_to_json(balances, "output/balance_output.json")
        return balances

    def get_balances(self):
        """Gets balances, saves them to file and prints to console."""
        setup_logging()
        logging.info("Fetching balances...")
        try:
            balances = self._get_and_save_balances()
            formatted_balances = format_balances(balances["balances"])
            logging.info(f"Balances fetched successfully.\n{formatted_balances}")
            with open("output/balance_output.txt", "w") as f:
                f.write(formatted_balances)
        except Exception as e:
            logging.error(f"An error occurred in get_balances: {e}", exc_info=True)


    def monitor_balances(self):
        """Monitors balances in a loop, saving them to file."""
        setup_logging()
        logging.info("Starting monitoring mode. Press Ctrl+C to stop.")
        while True:
            try:
                balances = self._get_and_save_balances()
                formatted_balances = format_balances(balances["balances"])
                with open("output/balance_output.txt", "w") as f:
                    f.write(formatted_balances)
                logging.info(f"Data updated at {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(60)
            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user.")
                break
            except Exception as e:
                logging.error(f"An error occurred during monitoring: {e}", exc_info=True)
                time.sleep(60)
