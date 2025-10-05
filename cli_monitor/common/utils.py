"""
Цей модуль містить набір допоміжних функцій (утиліт), що використовуються
в різних частинах проекту.
"""

import json
from loguru import logger
import os
from datetime import datetime, timezone
from dateutil import tz
from logging.handlers import RotatingFileHandler
from .config import config


import aiofiles

async def save_to_json(data, filename="output.json"):
    """
    Зберігає дані у файл формату JSON, додаючи мітку часу.

    Args:
        data: Дані для збереження.
        filename (str, optional): Назва файлу. За замовчуванням "output.json".
    """
    # Переконуємося, що директорія для файлу існує
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)
    
    local_tz = tz.tzlocal()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    output_data = {
        "last_updated": now_local.strftime('%d/%m/%Y %H:%M'),
        "data": data,
    }
    async with aiofiles.open(filename, "w") as f:
        await f.write(json.dumps(output_data, indent=2))

def format_balances(balances):
    """
    Форматує дані про баланси для зручного відображення у текстовому вигляді.

    Args:
        balances (dict): Словник з даними про баланси.

    Returns:
        str: Відформатований рядок з інформацією про баланси.
    """
    local_tz = tz.tzlocal()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    
    spot_balances = balances.get("spot", [])
    futures_balances = balances.get("futures", [])
    earn_balances = balances.get("earn", [])
    total_spot_balance_usd = balances.get("total_spot_balance_usd", 0)
    total_futures_balance_usd = balances.get("total_futures_balance_usd", 0)
    total_earn_balance_usd = balances.get("total_earn_balance_usd", 0)
    total_balance_usd = balances.get("total_balance_usd", 0)

    output = [
        f"--- Останнє оновлення: {now_local.strftime('%d/%m/%Y %H:%M')} ---",
        f"--- Загальний баланс: ${total_balance_usd:.2f} ---",
        "",
        f"--- Загальний спотовий баланс: ${total_spot_balance_usd:.2f} ---",
        "--- Спотові баланси ---"
    ]
    if spot_balances:
        for balance in spot_balances:
            output.append(f"  {balance['asset']}: {balance['total']}")
    else:
        output.append("  Спотових балансів не знайдено.")

    output.extend([
        "",
        f"--- Загальний ф'ючерсний баланс: ${total_futures_balance_usd:.2f} ---",
        "--- Ф'ючерсні баланси ---"
    ])
    if futures_balances:
        for balance in futures_balances:
            output.append(f"  {balance['asset']}: {balance['balance']}")
    else:
        output.append("  Ф'ючерсних балансів не знайдено.")

    output.extend([
        "",
        f"--- Загальний Earn баланс: ${total_earn_balance_usd:.2f} ---",
        "--- Earn баланси ---"
    ])
    if earn_balances:
        for balance in earn_balances:
            output.append(f"  {balance['asset']}: {balance['total']}")
    else:
        output.append("  Earn балансів не знайдено.")

    return "\n".join(output)


def structure_cycles_and_get_pairs(cycles_coins, symbols_info):
    """
    Структурує цикли та повертає список унікальних торгових пар з них.

    Ця функція перетворює список списків монет (циклів) у більш структурований
    формат, визначаючи реальні торгові пари та напрямок торгівлі для кожного кроку.

    Args:
        cycles_coins (list): Список циклів, де кожен цикл - це список монет.
                             (напр., [['USDT', 'BTC', 'USDT'], ...])
        symbols_info (dict): Словник з інформацією про всі символи з біржі.

    Returns:
        tuple: Кортеж, що містить:
               - `structured_cycles` (list): Список структурованих циклів.
               - `all_pairs` (set): Множина всіх унікальних торгових пар, задіяних у циклах.
    """
    structured_cycles = []
    all_pairs = set()
    all_symbols = list(symbols_info)

    for coins in cycles_coins:
        current_cycle_steps = []
        all_pairs_in_cycle = []
        valid_cycle = True
        for i in range(len(coins) - 1):
            # Визначаємо, в якому порядку монети утворюють торгову пару на біржі
            pair_symbol = f'{coins[i+1]}{coins[i]}' if f'{coins[i+1]}{coins[i]}' in all_symbols else f'{coins[i]}{coins[i+1]}'
            
            # Перевіряємо, чи існує така пара взагалі
            if pair_symbol not in all_symbols:
                valid_cycle = False
                break
            
            # Перевіряємо, чи пара активна для торгівлі
            if symbols_info[pair_symbol]['status'] != 'TRADING':
                valid_cycle = False
                break

            current_cycle_steps.append({"pair": pair_symbol, "from": coins[i], "to": coins[i+1]})
            all_pairs_in_cycle.append(pair_symbol)

        if valid_cycle:
            cycle_info = {"coins": coins, "steps": current_cycle_steps}
            structured_cycles.append(cycle_info)
            all_pairs.update(all_pairs_in_cycle)
            
    return structured_cycles, all_pairs