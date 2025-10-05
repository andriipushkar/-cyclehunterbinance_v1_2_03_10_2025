"""
Цей модуль відповідає за створення конфігураційних файлів за замовчуванням.

Якщо файли `config.json` або `monitored_coins.json` відсутні в папці `configs`,
цей скрипт створить їх із базовими налаштуваннями. Це спрощує перший запуск
додатку для нового користувача.
"""

import json
import os
import aiofiles
import asyncio

# Визначення шляхів до конфігураційних файлів
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
MONITORED_COINS_FILE = os.path.join(CONFIG_DIR, 'monitored_coins.json')

# Конфігурація за замовчуванням
DEFAULT_CONFIG = {
    "base_currency": "USDT",
    "min_profit_threshold": 0.1
}

# Список монет для моніторингу за замовчуванням
DEFAULT_MONITORED_COINS = {
    "coins_to_monitor": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA"]
}

async def create_default_config_files():
    """
    Створює конфігураційні файли за замовчуванням, якщо вони не існують.
    """
    # Створюємо папку `configs`, якщо її немає
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Створюємо `config.json`, якщо він не існує
    if not os.path.exists(CONFIG_FILE):
        async with aiofiles.open(CONFIG_FILE, 'w') as f:
            await f.write(json.dumps(DEFAULT_CONFIG, indent=2))
        print(f"Створено файл конфігурації за замовчуванням: {CONFIG_FILE}")
    else:
        print(f"Файл конфігурації вже існує: {CONFIG_FILE}")

    # Створюємо `monitored_coins.json`, якщо він не існує
    if not os.path.exists(MONITORED_COINS_FILE):
        async with aiofiles.open(MONITORED_COINS_FILE, 'w') as f:
            await f.write(json.dumps(DEFAULT_MONITORED_COINS, indent=2))
        print(f"Створено файл з монетами для моніторингу: {MONITORED_COINS_FILE}")
    else:
        print(f"Файл з монетами для моніторингу вже існує: {MONITORED_COINS_FILE}")

if __name__ == '__main__':
    """
    Точка входу для запуску скрипта напряму.
    """
    asyncio.run(create_default_config_files())