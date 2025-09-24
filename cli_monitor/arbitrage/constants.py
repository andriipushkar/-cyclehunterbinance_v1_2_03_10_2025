import os
from decimal import getcontext

# --- Precision ---
getcontext().prec = 15

# --- Directories ---
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'output'))

# --- File Paths ---
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
POSSIBLE_CYCLES_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.json')
ALL_PROFITS_TXT_FILE = os.path.join(OUTPUT_DIR, 'all_profits.txt')
ALL_PROFITS_JSON_FILE = os.path.join(OUTPUT_DIR, 'all_profits.json')
LATEST_PRICES_FILE = os.path.join(OUTPUT_DIR, 'latest_prices.json')

# --- WebSocket ---
CHUNK_SIZE = 100
