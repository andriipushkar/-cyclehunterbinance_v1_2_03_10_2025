import asyncio
import json
import os
import logging
import argparse
import sys
from datetime import datetime
from decimal import getcontext

from binance.client import Client

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from cli_monitor.common.utils import structure_cycles_and_get_pairs
from .cycle import Cycle
from . import constants

logging.basicConfig(level=logging.INFO)
getcontext().prec = 15

class Backtester:
    """Runs a backtest of the arbitrage strategy on historical data."""

    def __init__(self, start_date, end_date):
        """Initializes the Backtester."""
        self.start_date = start_date
        self.end_date = end_date
        self.client = BinanceClient()
        self.min_profit_threshold = config.min_profit_threshold
        self.symbols_info = {s['symbol']: s for s in self.client.get_exchange_info()['symbols']}
        self.trade_fees = self.client.get_trade_fees()

    def _load_cycles(self):
        """Loads cycles from the possible cycles file."""
        if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
            logging.error("Error: Cycles file not found.")
            return None
        with open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
            return json.load(f)

    def _get_historical_klines(self, symbol, start_str, end_str):
        """Fetches historical k-line data for a symbol."""
        logging.info(f"Fetching k-lines for {symbol} from {start_str} to {end_str}...")
        try:
            return self.client.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_str, end_str)
        except Exception as e:
            logging.error(f"Error fetching k-lines for {symbol}: {e}")
            return []

    def _fetch_and_align_historical_data(self, all_pairs):
        """Fetches and aligns historical data for all pairs."""
        logging.info("Fetching and aligning historical data...")
        aligned_prices = {}
        for pair in all_pairs:
            klines = self._get_historical_klines(pair, self.start_date, self.end_date)
            for kline in klines:
                timestamp = int(kline[0] / 60000)  # Group by minute
                if timestamp not in aligned_prices:
                    aligned_prices[timestamp] = {}
                aligned_prices[timestamp][pair] = kline[4]  # Use close price
        return aligned_prices

    def _run_simulation(self, structured_cycles, aligned_prices):
        """Runs the backtesting simulation and logs profitable opportunities."""
        logging.info("Running simulation...")
        profitable_count = 0
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        log_file = os.path.join(constants.LOG_DIR, 'backtest_results.log')

        with open(log_file, 'w') as f:
            f.write(f"Backtest from {self.start_date} to {self.end_date}\n---\n")

            for timestamp in sorted(aligned_prices.keys()):
                prices_at_timestamp = aligned_prices[timestamp]
                adapted_prices = {pair: {"a": price, "b": price} for pair, price in prices_at_timestamp.items()}

                for cycle in structured_cycles:
                    if not all(s['pair'] in adapted_prices for s in cycle.steps):
                        continue

                    profit_pct = cycle.calculate_profit(adapted_prices, self.symbols_info, self.trade_fees)

                    if profit_pct is not None and profit_pct > self.min_profit_threshold:
                        profitable_count += 1
                        dt_object = datetime.fromtimestamp(timestamp * 60)
                        log_message = (
                            f"[{dt_object.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS!\n"
                            f"Cycle: {cycle}\n"
                            f"PROFIT: {profit_pct:.4f}%\n---\n"
                        )
                        f.write(log_message)

        logging.info(f"Simulation finished. Found {profitable_count} profitable opportunities.")
        logging.info(f"Results saved to {log_file}")

    async def run(self):
        """Runs the backtesting simulation."""
        logging.info("--- Starting Backtest ---")
        cycles_coins = self._load_cycles()
        if not cycles_coins:
            return

        structured_cycles_data, all_pairs = structure_cycles_and_get_pairs(cycles_coins, self.symbols_info)
        structured_cycles = [Cycle(c['coins'], c['steps']) for c in structured_cycles_data]

        aligned_prices = self._fetch_and_align_historical_data(all_pairs)

        self._run_simulation(structured_cycles, aligned_prices)

        logging.info("--- Backtest Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest an arbitrage strategy.")
    parser.add_argument("start_date", help="Start date for backtesting (YYYY-MM-DD).")
    parser.add_argument("end_date", help="End date for backtesting (YYYY-MM-DD).")
    args = parser.parse_args()

    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        logging.error("Error: Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)

    backtester = Backtester(args.start_date, args.end_date)
    asyncio.run(backtester.run())