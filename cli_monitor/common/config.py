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
        self.trading_fee = Decimal('0.001')
        self.min_profit_threshold = Decimal('0.0')
        self.max_cycle_length = 3
        self.monitored_coins = []
        self.whitelist_base_coins = []
        self.whitelist_min_volume_usd = 100000
        self.whitelist_top_n_pairs = 100
        self.blacklist_bottom_n_pairs = 100

    def load_config(self):
        """
        Завантажує основний конфігураційний файл `config.json`.

        Перезаписує значення за замовчуванням налаштуваннями з файлу.

        Raises:
            FileNotFoundError: Якщо файл `config.json` не знайдено.
        """
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
        config_file = os.path.join(config_dir, 'config.json')
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Файл конфігурації не знайдено за шляхом: {config_file}")

        with open(config_file, 'r') as f:
            config_data = json.load(f)

        # Оновлюємо атрибути класу значеннями з файлу, якщо вони там є
        self.base_currency = config_data.get('base_currency', self.base_currency)
        self.trading_fee = Decimal(config_data.get('trading_fee', self.trading_fee))
        self.min_profit_threshold = Decimal(config_data.get('min_profit_threshold', self.min_profit_threshold))
        self.max_cycle_length = config_data.get('max_cycle_length', self.max_cycle_length)
        self.monitored_coins = config_data.get('monitored_coins', self.monitored_coins)
        self.whitelist_base_coins = config_data.get('whitelist_base_coins', self.whitelist_base_coins)
        self.whitelist_min_volume_usd = config_data.get('whitelist_min_volume_usd', self.whitelist_min_volume_usd)
        self.whitelist_top_n_pairs = config_data.get('whitelist_top_n_pairs', self.whitelist_top_n_pairs)
        self.blacklist_bottom_n_pairs = config_data.get('blacklist_bottom_n_pairs', self.blacklist_bottom_n_pairs)

# Створюємо єдиний екземпляр класу Config, який буде імпортуватися в інші модулі.
# Це реалізує патерн Singleton, забезпечуючи, що всі частини програми
# працюють з однаковою конфігурацією.
config = Config()