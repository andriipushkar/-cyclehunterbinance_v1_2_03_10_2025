"""
Цей модуль відповідає за генерацію "чорного списку" (blacklist) монет та торгових пар.

Blacklist - це список найменш ліквідних активів. Активи з цього списку
виключаються з подальшого аналізу, щоб зменшити кількість "шуму" та
помилкових розрахунків, пов'язаних з низьколіквідними парами.
"""

import logging
import json
from decimal import Decimal
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config

def generate_blacklist():
    """
    Генерує чорний список активів та пар з найнижчою ліквідністю.

    Процес генерації:
    1. Завантажує `whitelist.json`, щоб виключити ліквідні пари з розгляду.
    2. Отримує з Binance інформацію про всі пари та їх 24-годинну статистику.
    3. Відбирає пари, які не входять до білого списку і мають обсяг торгів більше нуля.
    4. Сортує кандидатів за зростанням обсягу торгів і вибирає топ-N найгірших.
    5. Зберігає активи та пари з цього списку у файл `configs/blacklist.json`.
    """
    logging.info("Початок генерації чорного списку...")

    client = BinanceClient()

    # Завантажуємо налаштування з конфігурації
    bottom_n_pairs = config.blacklist_bottom_n_pairs

    # Завантажуємо білий список, щоб його пари не потрапили до чорного списку
    whitelist_path = "configs/whitelist.json"
    try:
        with open(whitelist_path, 'r') as f:
            whitelist_data = json.load(f)
        whitelist_pairs_set = set(whitelist_data.get('whitelist_pairs', []))
        logging.info(f"Завантажено {len(whitelist_pairs_set)} пар з білого списку.")
    except FileNotFoundError:
        logging.warning(f"Файл білого списку не знайдено: {whitelist_path}. Чорний список може містити ліквідні пари.")
        whitelist_pairs_set = set()
    except json.JSONDecodeError:
        logging.error(f"Помилка декодування JSON з білого списку: {whitelist_path}. Скасування.")
        return

    # Отримуємо дані з біржі
    exchange_info = client.get_exchange_info()
    tickers = client.get_24h_ticker()

    if not exchange_info or not tickers:
        logging.error("Не вдалося отримати інформацію про біржу або тікери. Скасування.")
        return

    logging.info(f"Отримано {len(exchange_info.get('symbols', []))} символів та {len(tickers)} тікерів.")

    ticker_map = {ticker['symbol']: ticker for ticker in tickers}
    
    candidate_pairs = []

    for symbol_info in exchange_info.get('symbols', []):
        pair = symbol_info['symbol']

        # Ігноруємо пари, які вже є в білому списку
        if pair in whitelist_pairs_set:
            continue

        # Розглядаємо тільки активні торгові пари
        if symbol_info['status'] != 'TRADING':
            continue

        ticker_data = ticker_map.get(pair)
        if not ticker_data:
            continue

        # Відбираємо пари з хоч якимось обсягом торгів
        volume_usd = Decimal(ticker_data.get('quoteVolume', 0))
        if volume_usd <= 0:
            continue

        candidate_pairs.append({
            'symbol': pair,
            'baseAsset': symbol_info['baseAsset'],
            'quoteAsset': symbol_info['quoteAsset'],
            'quoteVolume': volume_usd
        })

    # Сортуємо пари за обсягом (за зростанням) і беремо N найгірших
    sorted_pairs = sorted(candidate_pairs, key=lambda p: p['quoteVolume'])
    bottom_pairs = sorted_pairs[:bottom_n_pairs]

    # Формуємо кінцевий чорний список з активів та пар
    blacklist_assets = set()
    blacklist_pairs = set()
    for pair_data in bottom_pairs:
        blacklist_pairs.add(pair_data['symbol'])
        blacklist_assets.add(pair_data['baseAsset'])
        blacklist_assets.add(pair_data['quoteAsset'])

    logging.info(f"Чорний список згенеровано: {len(blacklist_assets)} активів та {len(blacklist_pairs)} пар.")

    # Зберігаємо результат у файл
    output_path = "configs/blacklist.json"
    try:
        with open(output_path, 'w') as f:
            json.dump({
                "blacklist_assets": sorted(list(blacklist_assets)),
                "blacklist_pairs": sorted(list(blacklist_pairs))
            }, f, indent=2)
        logging.info(f"Чорний список збережено у {output_path}")
    except IOError as e:
        logging.error(f"Помилка збереження чорного списку у {output_path}: {e}")

if __name__ == '__main__':
    # Для тестування та ручної генерації
    config.load_config()
    logging.basicConfig(level=logging.INFO)
    generate_blacklist()