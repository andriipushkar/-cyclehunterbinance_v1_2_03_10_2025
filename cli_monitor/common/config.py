"""
Цей модуль надає централізований клас `Config` для управління конфігурацією додатку.

Він завантажує секретні ключі з `.env` файлу та параметри з `configs/config.json`,
надаючи єдину точку доступу до всіх налаштувань.
"""

import os
import json
from dotenv import load_dotenv
from decimal import Decimal

class Config:
    """Централізований клас для зберігання конфігурації."""

    def __init__(self):
        """
        Ініціалізує об'єкт конфігурації.

        Завантажує змінні середовища (API ключі) з файлу .env та встановлює
        значення за замовчуванням для інших параметрів.

        Raises:
            ValueError: Якщо API ключі не знайдено у файлі .env.
        """
        # Завантажуємо змінні з файлу .env у середовище ОС
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("API ключі Binance не знайдено у файлі .env. Будь ласка, встановіть BINANCE_API_KEY та BINANCE_API_SECRET.")

        # Ініціалізація значень за замовчуванням
        self.base_currency = 'USDT'
        self.initial_investment_usd = Decimal('15.0')
        self.trading_fee = Decimal('0.001')
        self.min_profit_threshold = Decimal('0.0')
        self.min_trade_volume_usd = 100000
        self.max_cycle_length = 3
        self.log_level = 'INFO'
        self.monitored_coins = []
        self.whitelist_base_coins = []
        self.whitelist_min_volume_usd = 100000
        self.whitelist_top_n_pairs = 100
        self.blacklist_bottom_n_pairs = 100
        self.max_slippage_pct = Decimal('0.1')

        # Balance monitor settings
        self.balance_monitor_ignored_assets = []
        self.balance_monitor_min_value_to_display = 1
        self.balance_monitor_output_json_path = "output/balance_output.json"
        self.balance_monitor_output_txt_path = "output/balance_output.txt"
        self.balance_monitor_monitoring_interval_seconds = 60

    def _load_config_file(self, filename):
        """
        Завантажує один конфігураційний файл.
        """
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
        config_file = os.path.join(config_dir, filename)
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Файл конфігурації не знайдено за шляхом: {config_file}")

        with open(config_file, 'r') as f:
            return json.load(f)

    def load_configs(self):
        """
        Завантажує конфігураційні файли `strategy.json` та `monitor.json`.

        Перезаписує значення за замовчуванням налаштуваннями з файлів.
        """
        strategy_config = self._load_config_file('strategy.json')
        monitor_config = self._load_config_file('monitor.json')

        # Оновлюємо атрибути класу значеннями з файлу strategy.json
        self.base_currency = strategy_config.get('base_currency', self.base_currency)
        self.initial_investment_usd = Decimal(strategy_config.get('initial_investment_usd', self.initial_investment_usd))
        self.trading_fee = Decimal(strategy_config.get('trading_fee', self.trading_fee))
        self.min_profit_threshold = Decimal(strategy_config.get('min_profit_threshold', self.min_profit_threshold))
        self.min_trade_volume_usd = strategy_config.get('min_trade_volume_usd', self.min_trade_volume_usd)
        self.max_cycle_length = strategy_config.get('max_cycle_length', self.max_cycle_length)
        self.monitored_coins = strategy_config.get('monitored_coins', self.monitored_coins)
        self.whitelist_base_coins = strategy_config.get('whitelist_base_coins', self.whitelist_base_coins)
        self.whitelist_min_volume_usd = strategy_config.get('whitelist_min_volume_usd', self.whitelist_min_volume_usd)
        self.whitelist_top_n_pairs = strategy_config.get('whitelist_top_n_pairs', self.whitelist_top_n_pairs)
        self.blacklist_bottom_n_pairs = strategy_config.get('blacklist_bottom_n_pairs', self.blacklist_bottom_n_pairs)
        self.max_slippage_pct = Decimal(strategy_config.get('max_slippage_pct', self.max_slippage_pct))

        # Оновлюємо атрибути класу значеннями з файлу monitor.json
        self.log_level = monitor_config.get('log_level', self.log_level)
        self.balance_monitor_ignored_assets = monitor_config.get('ignored_assets', self.balance_monitor_ignored_assets)
        self.balance_monitor_min_value_to_display = monitor_config.get('min_value_to_display', self.balance_monitor_min_value_to_display)
        self.balance_monitor_output_json_path = monitor_config.get('output_json_path', self.balance_monitor_output_json_path)
        self.balance_monitor_output_txt_path = monitor_config.get('output_txt_path', self.balance_monitor_output_txt_path)
        self.balance_monitor_monitoring_interval_seconds = monitor_config.get('monitoring_interval_seconds', self.balance_monitor_monitoring_interval_seconds)

# Створюємо єдиний екземпляр класу Config, який буде імпортуватися в інші модулі.
# Це реалізує патерн Singleton, забезпечуючи, що всі частини програми
# працюють з однаковою конфігурацією.
config = Config()