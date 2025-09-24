import json
import logging
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from . import constants

logging.basicConfig(level=logging.INFO)

class CycleFinder:
    """
    Finds potential arbitrage cycles on the exchange.
    """

    def __init__(self):
        """Initializes the CycleFinder."""
        self.client = BinanceClient()
        self.base_currency = config.base_currency
        self.monitored_coins = config.monitored_coins
        self.max_cycle_length = config.max_cycle_length
        self.exchange_info = None
        self.trading_pairs = None

    def _get_trading_pairs(self):
        """
        Builds a graph of all possible trading pairs from the exchange info.
        """
        pairs = {}
        for s in self.exchange_info['symbols']:
            base = s['baseAsset']
            quote = s['quoteAsset']
            if base not in pairs:
                pairs[base] = []
            if quote not in pairs:
                pairs[quote] = []
            pairs[base].append(quote)
            pairs[quote].append(base)
        return pairs

    def _find_cycles_dfs(self, graph, start_node, max_length):
        """
        Finds all simple cycles in the graph starting from start_node
        using a depth-first search algorithm.
        """
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

    def _save_cycles(self, cycles):
        """Saves the found cycles to JSON and TXT files."""
        logging.info(f"Found {len(cycles)} potential arbitrage cycles.")

        with open(constants.POSSIBLE_CYCLES_FILE, 'w') as f:
            json.dump(cycles, f, indent=2)
        logging.info(f"Saved cycles to {constants.POSSIBLE_CYCLES_FILE}")

        txt_path = constants.POSSIBLE_CYCLES_FILE.replace('.json', '.txt')
        with open(txt_path, 'w') as f:
            for cycle in cycles:
                f.write(f"{ ' -> '.join(cycle)}\n")
        logging.info(f"Saved cycles to {txt_path}")

    def run(self):
        """
        The main method to run the cycle finding process.
        """
        logging.info("-- Starting Cycle Finder --")
        try:
            self.exchange_info = self.client.get_exchange_info()
        except Exception as e:
            logging.error(f"Error fetching exchange info from Binance: {e}")
            return

        all_trading_pairs = self._get_trading_pairs()

        # Filter the trading pairs to only include monitored coins
        allowed_coins = set(self.monitored_coins + [self.base_currency])
        self.trading_pairs = {}
        for coin, neighbors in all_trading_pairs.items():
            if coin in allowed_coins:
                filtered_neighbors = [n for n in neighbors if n in allowed_coins]
                if filtered_neighbors:
                    self.trading_pairs[coin] = filtered_neighbors

        found_cycles = self._find_cycles_dfs(self.trading_pairs, self.base_currency, self.max_cycle_length)

        self._save_cycles(found_cycles)
        logging.info("-- Cycle Finder Finished --")


if __name__ == '__main__':
    finder = CycleFinder()
    finder.run()
