import asyncio
import json
import os
import logging
from decimal import Decimal, getcontext
from datetime import datetime, timedelta

import argparse
import sys
from binance.client import Client

from cli_monitor.common.binance_client import BinanceClient
from .profit_utils import calculate_profit

logging.basicConfig(level=logging.INFO)

# Set precision for Decimal calculations
getcontext().prec = 15

# --- Constants ---
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
POSSIBLE_CYCLES_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
BACKTEST_LOG_FILE = os.path.join(LOG_DIR, 'backtest_results.log')

# --- Backtesting Logic ---

def load_config_and_cycles():
    """Loads config and cycles from their respective files."""
    if not os.path.exists(CONFIG_FILE) or not os.path.exists(POSSIBLE_CYCLES_FILE):
        logging.error("Error: Config or cycles file not found.")
        return None, None, None, None

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    with open(POSSIBLE_CYCLES_FILE, 'r') as f:
        cycles = json.load(f)
        
    trading_fee = Decimal(config.get('trading_fee', '0.001'))
    min_profit_threshold = Decimal(config.get('min_profit_threshold', '0.0'))
    return config, cycles, trading_fee, min_profit_threshold

def get_historical_klines(client, symbol, start_str, end_str):
    """Fetches historical k-line data for a symbol."""
    logging.info(f"Fetching k-lines for {symbol} from {start_str} to {end_str}...")
    try:
        klines = client.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_str, end_str)
        return klines
    except Exception as e:
        logging.error(f"Error fetching k-lines for {symbol}: {e}")
        return []

def _structure_cycles_and_get_pairs(cycles_coins, all_symbols):
    """Structures cycles and gets all unique pairs."""
    structured_cycles = []
    all_pairs = set()
    for coins in cycles_coins:
        from_coin, coin1, coin2, to_coin = coins
        steps = []
        pair1 = f'{coin1}{from_coin}' if f'{coin1}{from_coin}' in all_symbols else f'{from_coin}{coin1}'
        pair2 = f'{coin2}{coin1}' if f'{coin2}{coin1}' in all_symbols else f'{coin1}{coin2}'
        pair3 = f'{to_coin}{coin2}' if f'{to_coin}{coin2}' in all_symbols else f'{coin2}{to_coin}'
        
        if all(p in all_symbols for p in [pair1, pair2, pair3]):
            steps.append({"pair": pair1, "from": from_coin, "to": coin1})
            steps.append({"pair": pair2, "from": coin1, "to": coin2})
            steps.append({"pair": pair3, "from": coin2, "to": to_coin})
            structured_cycles.append({"coins": coins, "steps": steps})
            all_pairs.update([pair1, pair2, pair3])
    return structured_cycles, all_pairs

def _fetch_and_align_historical_data(client, all_pairs, start_date_str, end_date_str):
    """Fetches and aligns historical data for all pairs."""
    logging.info("Fetching and aligning historical data...")
    aligned_prices = {}
    for pair in all_pairs:
        klines = get_historical_klines(client, pair, start_date_str, end_date_str)
        for kline in klines:
            # Group by minute
            timestamp = int(kline[0] / 60000) 
            if timestamp not in aligned_prices:
                aligned_prices[timestamp] = {}
            # Use close price for backtesting
            aligned_prices[timestamp][pair] = kline[4] 
    return aligned_prices

def _run_simulation(structured_cycles, aligned_prices, symbols_info, trading_fee, min_profit_threshold, start_date_str, end_date_str):
    """Runs the backtesting simulation and logs profitable opportunities."""
    logging.info("Running simulation...")
    profitable_count = 0
    with open(BACKTEST_LOG_FILE, 'w') as f:
        f.write(f"Backtest from {start_date_str} to {end_date_str}\n---\n")

        # Iterate through each minute of historical data
        for timestamp in sorted(aligned_prices.keys()):
            prices_at_timestamp = aligned_prices[timestamp]
            
            # Adapt prices for calculate_profit function
            adapted_prices = {pair: {"a": price, "b": price} for pair, price in prices_at_timestamp.items()}

            # Check each cycle for profitability
            for cycle in structured_cycles:
                # Ensure all pairs for the cycle are present in the current timestamp
                if not all(s['pair'] in adapted_prices for s in cycle['steps']):
                    continue

                profit_pct = calculate_profit(cycle['steps'], adapted_prices, symbols_info, trading_fee)
                
                if profit_pct is not None and profit_pct > min_profit_threshold:
                    profitable_count += 1
                    dt_object = datetime.fromtimestamp(timestamp * 60)
                    cycle_str = ' -> '.join(cycle['coins'])
                    log_message = (
                        f"[{dt_object.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS!\n"
                        f"Cycle: {cycle_str}\n"
                        f"PROFIT: {profit_pct:.4f}%\n---\n"
                    )
                    f.write(log_message)
    
    logging.info(f"Simulation finished. Found {profitable_count} profitable opportunities.")
    logging.info(f"Results saved to {BACKTEST_LOG_FILE}")

async def run_backtest(start_date_str, end_date_str):
    """
    Runs the backtesting simulation.
    """
    logging.info("--- Starting Backtest ---")
    config, cycles_coins, trading_fee, min_profit_threshold = load_config_and_cycles()
    if not config or not cycles_coins:
        return

    client = BinanceClient()
    symbols_info = {s['symbol']: s for s in client.get_exchange_info()['symbols']}
    all_symbols = symbols_info.keys()

    structured_cycles, all_pairs = _structure_cycles_and_get_pairs(cycles_coins, all_symbols)

    aligned_prices = _fetch_and_align_historical_data(client, all_pairs, start_date_str, end_date_str)

    _run_simulation(structured_cycles, aligned_prices, symbols_info, trading_fee, min_profit_threshold, start_date_str, end_date_str)

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

    asyncio.run(run_backtest(args.start_date, args.end_date))
