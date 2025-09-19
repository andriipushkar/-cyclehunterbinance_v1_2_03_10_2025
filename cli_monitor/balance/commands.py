import logging
import time
from datetime import datetime
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.utils import save_to_json, format_balances, setup_logging

def _process_balances(balances, client, balance_key='total', min_value=1):
    """Filters balances and calculates their total USD value."""
    filtered_balances = []
    total_balance_usd = 0
    for balance in balances:
        asset = balance['asset']
        total = float(balance[balance_key])
        price = client.get_symbol_price(asset)
        if price is not None:
            value = total * price
            total_balance_usd += value
            if value >= min_value:
                filtered_balances.append(balance)
    return filtered_balances, total_balance_usd

def _get_total_balance_usd(balances, client, balance_key='balance'):
    """Calculates the total USD value of a list of balances."""
    total_balance_usd = 0
    for balance in balances:
        asset = balance['asset']
        total = float(balance[balance_key])
        price = client.get_symbol_price(asset)
        if price is not None:
            value = total * price
            total_balance_usd += value
    return total_balance_usd

def _get_and_save_balances():
    """Fetches balances and saves them to the JSON file."""
    client = BinanceClient()
    spot_balances = client.get_spot_balance()
    futures_balances = client.get_futures_balance()
    earn_balances = client.get_earn_balance()

    filtered_spot_balances, total_spot_balance_usd = _process_balances(spot_balances, client)
    total_futures_balance_usd = _get_total_balance_usd(futures_balances, client)
    filtered_earn_balances, total_earn_balance_usd = _process_balances(earn_balances, client)

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

def get_balances():
    """Gets balances, saves them to file and prints to console."""
    setup_logging()
    logging.info("Fetching balances...")
    try:
        balances = _get_and_save_balances()
        formatted_balances = format_balances(balances["balances"])
        logging.info(f"Balances fetched successfully.\n{formatted_balances}")
        with open("output/balance_output.txt", "w") as f:
            f.write(formatted_balances)
    except Exception as e:
        logging.error(f"An error occurred in get_balances: {e}", exc_info=True)


def monitor_balances():
    """Monitors balances in a loop, saving them to file."""
    setup_logging()
    logging.info("Starting monitoring mode. Press Ctrl+C to stop.")
    while True:
        try:
            balances = _get_and_save_balances()
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
