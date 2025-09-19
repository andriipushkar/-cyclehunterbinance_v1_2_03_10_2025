import json
import os
import logging
from itertools import combinations
from cli_monitor.common.binance_client import BinanceClient

logging.basicConfig(level=logging.INFO)

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

POSSIBLE_CYCLES_JSON_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.json')
POSSIBLE_CYCLES_TXT_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.txt')

def find_triangular_arbitrage_cycles():
    """
    Finds all triangular arbitrage cycles based on the configuration
    and saves them to output files.
    """
    # 1. Load configuration
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    base_currency = config['base_currency']
    coins_to_monitor = config['monitored_coins']

    # 2. Get all available trading pairs from Binance
    client = BinanceClient()
    try:
        exchange_info = client.get_exchange_info()
        all_symbols = {s['symbol'] for s in exchange_info['symbols']}
    except Exception as e:
        logging.error(f"Error fetching exchange info from Binance: {e}")
        return

    logging.info(f"Found {len(all_symbols)} symbols on Binance.")

    # 3. Identify possible cycles
    found_cycles = []

    # For quick lookups
    all_symbols_set = set(all_symbols)

    # Iterate through all combinations of 2 coins from the monitored list
    for coin1, coin2 in combinations(coins_to_monitor, 2):
        # Define the three pairs we need for a triangular arbitrage
        pair_base_c1 = f"{coin1}{base_currency}"
        pair_base_c2 = f"{coin2}{base_currency}"
        pair_c1_c2 = f"{coin1}{coin2}"
        pair_c2_c1 = f"{coin2}{coin1}"

        # Check for the existence of the three required pairs for a triangle
        has_base_c1_pair = pair_base_c1 in all_symbols_set
        has_base_c2_pair = pair_base_c2 in all_symbols_set

        if has_base_c1_pair and has_base_c2_pair:
            # Check for a market between coin1 and coin2
            if pair_c1_c2 in all_symbols_set or pair_c2_c1 in all_symbols_set:
                # If a market exists, both cycles are possible.
                
                # Cycle: base -> c1 -> c2 -> base
                cycle1 = [base_currency, coin1, coin2, base_currency]
                if cycle1 not in found_cycles:
                    found_cycles.append(cycle1)
                
                # Cycle: base -> c2 -> c1 -> base
                cycle2 = [base_currency, coin2, coin1, base_currency]
                if cycle2 not in found_cycles:
                    found_cycles.append(cycle2)

    logging.info(f"Found {len(found_cycles)} potential triangular cycles.")

    # 4. Save results
    # Save to JSON
    with open(POSSIBLE_CYCLES_JSON_FILE, 'w') as f:
        json.dump(found_cycles, f, indent=2)
    logging.info(f"Saved cycles to {POSSIBLE_CYCLES_JSON_FILE}")

    # Save to TXT
    with open(POSSIBLE_CYCLES_TXT_FILE, 'w') as f:
        for cycle in found_cycles:
            f.write(f"{' -> '.join(cycle)}\n")
    logging.info(f"Saved cycles to {POSSIBLE_CYCLES_TXT_FILE}")

if __name__ == '__main__':
    find_triangular_arbitrage_cycles()

