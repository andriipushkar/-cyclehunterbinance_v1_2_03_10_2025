import json
import os

# Define the paths for the configuration files
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
MONITORED_COINS_FILE = os.path.join(CONFIG_DIR, 'monitored_coins.json')

# Default configuration
DEFAULT_CONFIG = {
    "base_currency": "USDT",
    "min_profit_threshold": 0.1
}

DEFAULT_MONITORED_COINS = {
    "coins_to_monitor": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA"]
}

def create_default_config_files():
    """
    Creates the default configuration files for the arbitrage bot
    if they don't already exist.
    """
    # Create the directory if it doesn't exist
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Create config.json if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"Created default config file at: {CONFIG_FILE}")
    else:
        print(f"Config file already exists at: {CONFIG_FILE}")

    # Create monitored_coins.json if it doesn't exist
    if not os.path.exists(MONITORED_COINS_FILE):
        with open(MONITORED_COINS_FILE, 'w') as f:
            json.dump(DEFAULT_MONITORED_COINS, f, indent=2)
        print(f"Created default monitored coins file at: {MONITORED_COINS_FILE}")
    else:
        print(f"Monitored coins file already exists at: {MONITORED_COINS_FILE}")

if __name__ == '__main__':
    create_default_config_files()
