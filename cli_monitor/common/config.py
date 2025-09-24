import os
import json
from dotenv import load_dotenv
from decimal import Decimal

class Config:
    """A centralized configuration class."""

    def __init__(self):
        """Initializes the Config class."""
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API keys not found in .env file. Please set BINANCE_API_KEY and BINANCE_API_SECRET.")

        # Initialize default values
        self.base_currency = 'USDT'
        self.trading_fee = Decimal('0.001')
        self.min_profit_threshold = Decimal('0.0')
        self.max_cycle_length = 3
        self.monitored_coins = []

    def load_config(self):
        """Loads the main configuration file."""
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
        config_file = os.path.join(config_dir, 'config.json')
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found at {config_file}")

        with open(config_file, 'r') as f:
            config = json.load(f)

        self.base_currency = config.get('base_currency', self.base_currency)
        self.trading_fee = Decimal(config.get('trading_fee', self.trading_fee))
        self.min_profit_threshold = Decimal(config.get('min_profit_threshold', self.min_profit_threshold))
        self.max_cycle_length = config.get('max_cycle_length', self.max_cycle_length)
        self.monitored_coins = config.get('monitored_coins', self.monitored_coins)

# Create a single instance of the Config class
config = Config()
