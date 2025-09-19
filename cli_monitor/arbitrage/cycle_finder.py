import json
import os
import logging
from itertools import permutations
from cli_monitor.common.binance_client import BinanceClient

logging.basicConfig(level=logging.INFO)

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

POSSIBLE_CYCLES_JSON_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.json')
POSSIBLE_CYCLES_TXT_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.txt')

def get_trading_pairs(exchange_info):
    pairs = {}
    for s in exchange_info['symbols']:
        base = s['baseAsset']
        quote = s['quoteAsset']
        if base not in pairs:
            pairs[base] = []
        if quote not in pairs:
            pairs[quote] = []
        pairs[base].append(quote)
        pairs[quote].append(base)
    return pairs

def find_cycles(graph, start_node, max_length):
    cycles = []
    stack = [(start_node, [start_node])]
    while stack:
        (vertex, path) = stack.pop()
        if len(path) > max_length:
            continue
        for neighbor in graph.get(vertex, []):
            if neighbor == start_node and len(path) > 2:
                cycles.append(path + [neighbor])
            elif neighbor not in path:
                stack.append((neighbor, path + [neighbor]))
    return cycles

def find_arbitrage_cycles():
    """
    Finds all arbitrage cycles based on the configuration
    and saves them to output files.
    """
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    base_currency = config['base_currency']
    coins_to_monitor = config['monitored_coins']
    max_cycle_length = config.get('max_cycle_length', 3)

    client = BinanceClient()
    try:
        exchange_info = client.get_exchange_info()
    except Exception as e:
        logging.error(f"Error fetching exchange info from Binance: {e}")
        return

    trading_pairs = get_trading_pairs(exchange_info)
    all_cycles = find_cycles(trading_pairs, base_currency, max_cycle_length + 1)

    found_cycles = []
    for cycle in all_cycles:
        if all(coin in coins_to_monitor or coin == base_currency for coin in cycle):
            found_cycles.append(cycle)

    logging.info(f"Found {len(found_cycles)} potential arbitrage cycles.")

    with open(POSSIBLE_CYCLES_JSON_FILE, 'w') as f:
        json.dump(found_cycles, f, indent=2)
    logging.info(f"Saved cycles to {POSSIBLE_CYCLES_JSON_FILE}")

    with open(POSSIBLE_CYCLES_TXT_FILE, 'w') as f:
        for cycle in found_cycles:
            f.write(f"{ ' -> '.join(cycle)}\n")
    logging.info(f"Saved cycles to {POSSIBLE_CYCLES_TXT_FILE}")

if __name__ == '__main__':
    find_arbitrage_cycles()