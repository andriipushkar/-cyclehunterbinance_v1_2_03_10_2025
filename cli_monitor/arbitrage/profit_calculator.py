import asyncio
import json
import os
import websockets
import logging
from datetime import datetime
from decimal import Decimal, getcontext
from cli_monitor.common.binance_client import BinanceClient

from . import constants
from .profit_utils import calculate_profit

logging.basicConfig(level=logging.INFO)

# --- Global State ---
# These dictionaries store the latest market data and arbitrage opportunities.
# They are updated in real-time by the WebSocket listener.
latest_prices = {} # Stores the latest bid/ask prices for each trading pair.
pair_to_cycles = {} # Maps each trading pair to the arbitrage cycles it is a part of.
latest_profits_by_cycle = {} # Stores the latest calculated profit for each arbitrage cycle.


def get_exchange_info_map():
    """Fetches all available trading symbols and maps them to their info."""
    try:
        client = BinanceClient()
        exchange_info = client.get_exchange_info()
        return {s['symbol']: s for s in exchange_info['symbols']}
    except Exception as e:
        logging.error(f"Error fetching exchange info from Binance: {e}")
        return None

def _load_cycles():
    """Loads cycles from the possible cycles file."""
    if not os.path.exists(constants.POSSIBLE_CYCLES_FILE):
        logging.error(f"Error: Cannot find possible cycles file at {constants.POSSIBLE_CYCLES_FILE}")
        return None
    with open(constants.POSSIBLE_CYCLES_FILE, 'r') as f:
        return json.load(f)

def _map_pairs_to_cycles(cycles_coins, symbols_info):
    """Maps trading pairs to the cycles they are a part of."""
    structured_cycles = []
    all_trade_pairs = set()
    all_symbols = symbols_info.keys()

    for coins in cycles_coins:
        from_coin, coin1, coin2, to_coin = coins
        current_cycle_steps = []

        # Step 1: from_coin -> coin1
        pair1_symbol = f'{coin1}{from_coin}' if f'{coin1}{from_coin}' in all_symbols else f'{from_coin}{coin1}'
        if pair1_symbol not in all_symbols: continue
        current_cycle_steps.append({"pair": pair1_symbol, "from": from_coin, "to": coin1})

        # Step 2: coin1 -> coin2
        pair2_symbol = f'{coin2}{coin1}' if f'{coin2}{coin1}' in all_symbols else f'{coin1}{coin2}'
        if pair2_symbol not in all_symbols: continue
        current_cycle_steps.append({"pair": pair2_symbol, "from": coin1, "to": coin2})

        # Step 3: coin2 -> to_coin
        pair3_symbol = f'{to_coin}{coin2}' if f'{to_coin}{coin2}' in all_symbols else f'{coin2}{to_coin}'
        if pair3_symbol not in all_symbols: continue
        current_cycle_steps.append({"pair": pair3_symbol, "from": coin2, "to": to_coin})

        cycle_info = {"coins": coins, "steps": current_cycle_steps}
        structured_cycles.append(cycle_info)
        all_trade_pairs.update([pair1_symbol, pair2_symbol, pair3_symbol])

        for pair in [pair1_symbol, pair2_symbol, pair3_symbol]:
            if pair not in pair_to_cycles:
                pair_to_cycles[pair] = []
            pair_to_cycles[pair].append(cycle_info)

    return structured_cycles, all_trade_pairs

def load_cycles_and_map_pairs(symbols_info):
    """Loads cycles and determines the actual trading pairs and their properties."""
    cycles_coins = _load_cycles()
    if cycles_coins is None:
        return [], set()
    return _map_pairs_to_cycles(cycles_coins, symbols_info)

def _write_profits_to_txt(sorted_cycles, timestamp):
    """Writes the latest profits to a text file."""
    txt_content = f"Last updated: {timestamp}\n\n"
    for cycle_str, profit in sorted_cycles:
        txt_content += f"Cycle: {cycle_str}, Profit: {profit:.4f}%\n"
    try:
        with open(constants.ALL_PROFITS_TXT_FILE, 'w') as f:
            f.write(txt_content)
    except Exception as e:
        logging.error(f"Error writing to all_profits.txt: {e}")

def _write_profits_to_json(sorted_cycles, timestamp):
    """Writes the latest profits to a JSON file."""
    json_data = {
        "last_updated": timestamp,
        "profits": [{"cycle": cycle_str, "profit_pct": f"{profit:.4f}"} for cycle_str, profit in sorted_cycles]
    }
    try:
        with open(constants.ALL_PROFITS_JSON_FILE, 'w') as f:
            json.dump(json_data, f, indent=2)
    except Exception as e:
        logging.error(f"Error writing to all_profits.json: {e}")

async def log_all_profits_periodically():
    """Periodically writes the latest profit for each cycle to txt and json files."""
    while True:
        await asyncio.sleep(2) # Update every 2 seconds
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Sort cycles by profit in descending order
        sorted_cycles = sorted(latest_profits_by_cycle.items(), key=lambda item: item[1], reverse=True)
        
        _write_profits_to_txt(sorted_cycles, timestamp)
        _write_profits_to_json(sorted_cycles, timestamp)

def _log_profitable_opportunity(cycle_str, profit_pct):
    """Logs a profitable opportunity to the console and to files."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # --- TXT Output ---
    txt_log_message = (
        f"[{timestamp}] SUCCESS!\n"
        f"Cycle: {cycle_str}\n"
        f"PROFIT: {profit_pct:.4f}%\n---\n"
    )
    logging.info(txt_log_message)
    with open(constants.PROFITABLE_CYCLES_TXT_FILE, 'a') as f:
        f.write(txt_log_message)

    # --- JSONL Output ---
    json_log_data = {
        "timestamp": timestamp,
        "cycle": cycle_str,
        "profit_pct": f"{profit_pct:.4f}"
    }
    with open(constants.PROFITABLE_CYCLES_JSONL_FILE, 'a') as f:
        json.dump(json_log_data, f)
        f.write('\n')

async def calculate_and_log_profit(cycle_info, symbols_info, trading_fee, min_profit_threshold):
    """Calculates profit for a cycle and updates the global profit dictionary."""
    steps = cycle_info['steps']
    if not all(s['pair'] in latest_prices for s in steps):
        return

    try:
        profit_pct = calculate_profit(steps, latest_prices, symbols_info, trading_fee)
        
        cycle_str = ' -> '.join(cycle_info['coins'])
        latest_profits_by_cycle[cycle_str] = profit_pct

        # Log only profitable opportunities
        if profit_pct > min_profit_threshold:
            _log_profitable_opportunity(cycle_str, profit_pct)

    except (KeyError, ValueError) as e:
        logging.debug(f"Calculation error for cycle {cycle_info['coins']}: {e}")


async def _handle_websocket_message(message, symbols_info, trading_fee, min_profit_threshold):
    """Handles a message from the WebSocket stream."""
    data = json.loads(message)['data']
    
    pair_symbol = data['s']
    latest_prices[pair_symbol] = {'b': data['b'], 'a': data['a']}
    
    if pair_symbol in pair_to_cycles:
        for cycle in pair_to_cycles[pair_symbol]:
            await calculate_and_log_profit(cycle, symbols_info, trading_fee, min_profit_threshold)

async def listen_to_chunk(chunk, symbols_info, trading_fee, min_profit_threshold):
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
                    await _handle_websocket_message(message, symbols_info, trading_fee, min_profit_threshold)
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

def _setup():
    """Sets up the profit calculator."""
    logging.info("Starting Profit Calculator...")
    os.makedirs(constants.LOG_DIR, exist_ok=True)
    os.makedirs(constants.OUTPUT_DIR, exist_ok=True)

    with open(constants.CONFIG_FILE, 'r') as f:
        config = json.load(f)
    trading_fee = Decimal(config.get('trading_fee', '0.001'))
    min_profit_threshold = Decimal(config.get('min_profit_threshold', '0.0'))

    symbols_info = get_exchange_info_map()
    if not symbols_info:
        return None, None, None, None

    structured_cycles, all_trade_pairs = load_cycles_and_map_pairs(symbols_info)
    if not structured_cycles:
        logging.warning("No valid cycles found to monitor.")
        return None, None, None, None

    logging.info(f"Monitoring {len(structured_cycles)} cycles involving {len(all_trade_pairs)} pairs.")
    return symbols_info, structured_cycles, all_trade_pairs, trading_fee, min_profit_threshold

async def main():
    """
    Main function to connect to WebSocket and run profit calculation.
    """
    symbols_info, structured_cycles, all_trade_pairs, trading_fee, min_profit_threshold = _setup()
    if not symbols_info:
        return

    # Chunk the pairs to avoid overly long URLs
    pair_chunks = [list(all_trade_pairs)[i:i + constants.CHUNK_SIZE] for i in range(0, len(all_trade_pairs), constants.CHUNK_SIZE)]

    # Start a listener task for each chunk
    listener_tasks = [asyncio.create_task(listen_to_chunk(chunk, symbols_info, trading_fee, min_profit_threshold)) for chunk in pair_chunks]
    
    # Also start the logger task
    logger_task = asyncio.create_task(log_all_profits_periodically())

    # Keep the main task alive
    await asyncio.gather(*listener_tasks, logger_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nMonitoring stopped by user.")
