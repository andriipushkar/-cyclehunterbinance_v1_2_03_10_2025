import asyncio
import json
import os
import websockets
import logging
from datetime import datetime
from decimal import Decimal, getcontext
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from cli_monitor.common.utils import structure_cycles_and_get_pairs, setup_logging

from . import constants
from .cycle import Cycle

logging.basicConfig(level=logging.DEBUG)

class ProfitCalculator:
    """Calculates and logs arbitrage opportunities."""

    def __init__(self):
        self.latest_prices = {}
        self.pair_to_cycles = {}
        self.latest_profits_by_cycle = {}
        self.profits_lock = asyncio.Lock()
        self._load_latest_prices()
        self.structured_cycles = []

    def _load_latest_prices(self):
        """Loads the latest prices from a file."""
        if os.path.exists(constants.LATEST_PRICES_FILE):
            with open(constants.LATEST_PRICES_FILE, 'r') as f:
                self.latest_prices = json.load(f)

    def _write_to_file(self, path, content):
        with open(path, 'w') as f:
            f.write(content)

    def _write_json_to_file(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    async def _save_latest_prices(self):
        """Saves the latest prices to a file."""
        try:
            await asyncio.to_thread(self._write_json_to_file, constants.LATEST_PRICES_FILE, self.latest_prices)
        except Exception as e:
            logging.error(f"Error saving latest prices: {e}")

    def get_exchange_info_map(self):
        """Fetches all available trading symbols and maps them to their info."""
        try:
            client = BinanceClient()
            exchange_info = client.get_exchange_info()
            return {s['symbol']: s for s in exchange_info['symbols']}
        except Exception as e:
            logging.error(f"Error fetching exchange info from Binance: {e}")
            return None

    def _load_cycles(self):
        """Loads cycles from the possible cycles file."""
        if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
            logging.error(f"Error: Cannot find possible cycles file at {constants.POSSIBLE_CYCLES_FILE}")
            return None
        with open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
            return json.load(f)

    def load_cycles_and_map_pairs(self, symbols_info):
        """Loads cycles and determines the actual trading pairs and their properties."""
        cycles_coins = self._load_cycles()
        if cycles_coins is None:
            return [], set()

        structured_cycles_data, all_trade_pairs = structure_cycles_and_get_pairs(cycles_coins, symbols_info)

        structured_cycles = [Cycle(c['coins'], c['steps']) for c in structured_cycles_data]

        for cycle in structured_cycles:
            for step in cycle.steps:
                pair = step['pair']
                if pair not in self.pair_to_cycles:
                    self.pair_to_cycles[pair] = []
                self.pair_to_cycles[pair].append(cycle)

        return structured_cycles, all_trade_pairs

    async def _write_profits_to_txt(self, sorted_cycles, timestamp):
        """Writes the latest profits to a text file."""
        txt_content = f"Last updated: {timestamp}\n\n"
        for cycle_str, profit in sorted_cycles:
            txt_content += f"Cycle: {cycle_str}, Profit: {profit:.4f}%\n"
        try:
            await asyncio.to_thread(self._write_to_file, constants.ALL_PROFITS_TXT_FILE, txt_content)
        except Exception as e:
            logging.error(f"Error writing to all_profits.txt: {e}")

    async def _write_profits_to_json(self, sorted_cycles, timestamp):
        """Writes the latest profits to a JSON file."""
        json_data = {
            "last_updated": timestamp,
            "profits": [{"cycle": cycle_str, "profit_pct": f"{profit:.4f}"} for cycle_str, profit in sorted_cycles]
        }
        print(f"Writing to all_profits.json: {json_data}")
        try:
            await asyncio.to_thread(self._write_json_to_file, constants.ALL_PROFITS_JSON_FILE, json_data)
        except Exception as e:
            logging.error(f"Error writing to all_profits.json: {e}")

    async def log_all_profits_periodically(self):
        """Periodically writes the latest profit for each cycle to txt and json files."""
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            latest_profits_copy = {}
            async with self.profits_lock:
                latest_profits_copy = self.latest_profits_by_cycle.copy()

            all_profits = {}
            for cycle in self.structured_cycles:
                cycle_str = str(cycle)
                all_profits[cycle_str] = latest_profits_copy.get(cycle_str, Decimal('-1.0'))

            # Sort cycles by profit in descending order
            sorted_cycles = sorted(all_profits.items(), key=lambda item: item[1], reverse=True)

            await self._write_profits_to_txt(sorted_cycles, timestamp)
            await self._write_profits_to_json(sorted_cycles, timestamp)
            await self._save_latest_prices()

    def _log_profitable_opportunity(self, cycle, profit_pct, prices):
        """Logs a profitable opportunity to the console and to files."""
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        date_dir = os.path.join(constants.OUTPUT_DIR, 'profits', now.strftime('%Y-%m-%d'))
        os.makedirs(date_dir, exist_ok=True)
        
        hour_file_path_jsonl = os.path.join(date_dir, f"{now.strftime('%H')}.jsonl")
        hour_file_path_txt = os.path.join(date_dir, f"{now.strftime('%H')}.txt")

        # --- TXT Output ---
        txt_log_message = (
            f"[{timestamp}] SUCCESS!\n"
            f"Cycle: {cycle}\n"
            f"PROFIT: {profit_pct:.4f}%\n"
            f"Prices: {prices}\n---\n"
        )
        logging.info(txt_log_message)
        with open(hour_file_path_txt, 'a') as f:
            f.write(txt_log_message)

        # --- JSONL Output ---
        json_log_data = {
            "timestamp": timestamp,
            "cycle": str(cycle),
            "profit_pct": f"{profit_pct:.4f}",
            "prices": prices
        }
        with open(hour_file_path_jsonl, 'a') as f:
            json.dump(json_log_data, f)
            f.write('\n')

    async def calculate_and_log_profit(self, cycle, symbols_info, trade_fees, min_profit_threshold):
        """Calculates profit for a cycle and updates the global profit dictionary."""
        steps = cycle.steps
        
        has_all_prices = all(s['pair'] in self.latest_prices for s in steps)
        if not has_all_prices:
            missing_prices = [s['pair'] for s in steps if s['pair'] not in self.latest_prices]
            logging.debug(f"Skipping cycle {cycle}. Missing prices for: {missing_prices}")
            return

        try:
            profit_pct = cycle.calculate_profit(self.latest_prices, symbols_info, trade_fees)
            
            cycle_str = str(cycle)
            async with self.profits_lock:
                self.latest_profits_by_cycle[cycle_str] = profit_pct

            # Log only profitable opportunities
            if profit_pct > min_profit_threshold:
                prices = {s['pair']: self.latest_prices[s['pair']] for s in steps}
                self._log_profitable_opportunity(cycle, profit_pct, prices)

        except (KeyError, ValueError) as e:
            logging.debug(f"Calculation error for cycle {cycle}: {type(e).__name__} - {e}")


    async def _handle_websocket_message(self, message, symbols_info, trade_fees, min_profit_threshold):
        """Handles a message from the WebSocket stream."""
        data = json.loads(message)['data']
        
        pair_symbol = data['s']
        self.latest_prices[pair_symbol] = {'b': data['b'], 'a': data['a']}
        
        if pair_symbol in self.pair_to_cycles:
            for cycle in self.pair_to_cycles[pair_symbol]:
                await self.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)

    async def listen_to_chunk(self, chunk, symbols_info, trade_fees, min_profit_threshold):
        """Connects to a WebSocket stream for a chunk of pairs and listens for messages."""
        streams = [f'{pair.lower()}@bookTicker' for pair in chunk]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        reconnect_attempts = 0
        max_reconnect_attempts = 5

        while reconnect_attempts < max_reconnect_attempts:
            try:
                async with websockets.connect(ws_url, ping_timeout=60) as ws:
                    logging.info(f"Connected to stream for {len(chunk)} pairs.")
                    reconnect_attempts = 0 # Reset on successful connection
                    while True:
                        message = await ws.recv()
                        await self._handle_websocket_message(message, symbols_info, trade_fees, min_profit_threshold)
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidStatusCode) as e:
                logging.warning(f"WebSocket connection error on chunk: {e}. Reconnecting...")
                reconnect_attempts += 1
                backoff_time = min(2 ** reconnect_attempts, 60) # Exponential backoff up to 60s
                logging.info(f"Waiting {backoff_time} seconds before attempt {reconnect_attempts+1}...")
                await asyncio.sleep(backoff_time)
            except Exception as e:
                logging.error(f"An unexpected error occurred on WebSocket chunk: {e}")
                break
        logging.error(f"Max reconnect attempts reached for chunk. Giving up.")

    def _setup(self):
        """Sets up the profit calculator."""
        setup_logging()
        logging.info("Starting Profit Calculator...")
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        os.makedirs(constants.OUTPUT_DIR, exist_ok=True)

        min_profit_threshold = Decimal(config.min_profit_threshold)

        client = BinanceClient()
        symbols_info = self.get_exchange_info_map()
        if not symbols_info:
            return None, None, None, None

        self.structured_cycles, all_trade_pairs = self.load_cycles_and_map_pairs(symbols_info)
        if not self.structured_cycles:
            logging.warning("No valid cycles found to monitor.")
            return None, None, None, None

        trade_fees = client.get_trade_fees()

        logging.info(f"Monitoring {len(self.structured_cycles)} cycles involving {len(all_trade_pairs)} pairs.")
        return symbols_info, all_trade_pairs, trade_fees, min_profit_threshold

    async def run(self):
        """
        Main function to connect to WebSocket and run profit calculation.
        """
        symbols_info, all_trade_pairs, trade_fees, min_profit_threshold = self._setup()
        if not symbols_info:
            return

        # Chunk the pairs to avoid overly long URLs
        pair_chunks = [list(all_trade_pairs)[i:i + constants.CHUNK_SIZE] for i in range(0, len(all_trade_pairs), constants.CHUNK_SIZE)]

        # Start a listener task for each chunk
        listener_tasks = [asyncio.create_task(self.listen_to_chunk(chunk, symbols_info, trade_fees, min_profit_threshold)) for chunk in pair_chunks]
        
        # Also start the logger task
        logger_task = asyncio.create_task(self.log_all_profits_periodically())

        # Keep the main task alive
        await asyncio.gather(*listener_tasks, logger_task)


async def main():
    calculator = ProfitCalculator()
    await calculator.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nMonitoring stopped by user.")
