"""
Цей модуль відповідає за генерацію "білого списку" (whitelist) монет та торгових пар.

Whitelist - це список активів, які вважаються достатньо ліквідними та надійними
для включення в пошук арбітражних циклів. Критерії відбору (базові монети,
мінімальний обсяг торгів) задаються в конфігураційному файлі.
"""

from loguru import logger
import json
from decimal import Decimal
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config

def generate_whitelist():
    """
    Генерує білий список активів та пар на основі критеріїв з конфігурації.

    Процес генерації:
    1. Завантажує налаштування з `config.json`.
    2. Отримує з Binance актуальну інформацію про всі пари та їх 24-годинну статистику.
    3. Фільтрує пари за статусом, приналежністю до базових монет та обсягом торгів.
    4. Сортує відфільтровані пари за обсягом і вибирає топ-N.
    5. Зберігає активи та пари з топ-N у файл `configs/whitelist.json`.
    """
    logger.info("Початок генерації білого списку...")
    
    client = BinanceClient()
    
    # Завантаження налаштувань з конфігурації
    base_coins = config.whitelist_base_coins
    min_volume_usd = Decimal(config.whitelist_min_volume_usd)
    top_n_pairs = config.whitelist_top_n_pairs

    if not base_coins:
        logger.error("Базові монети для білого списку не налаштовані. Скасування.")
        return

    # Отримання даних з біржі
    exchange_info = client.get_exchange_info()
    tickers = client.get_24h_ticker()

    if not exchange_info or not tickers:
        logger.error("Не вдалося отримати інформацію про біржу або тікери. Скасування.")
        return

    logger.info(f"Отримано {len(exchange_info.get('symbols', []))} символів та {len(tickers)} тікерів.")

    # Створюємо словник для швидкого доступу до даних тікера за назвою пари
    ticker_map = {ticker['symbol']: ticker for ticker in tickers}
    
    valid_pairs = []

    for symbol_info in exchange_info.get('symbols', []):
        pair = symbol_info['symbol']
        base_asset = symbol_info['baseAsset']
        quote_asset = symbol_info['quoteAsset']

        # --- Крок 1: Фільтрація за статусом --- 
        if symbol_info['status'] != 'TRADING':
            continue

        # --- Крок 2: Фільтрація за базовими монетами --- 
        # Пара проходить, якщо хоча б одна з її монет є в списку базових
        if not (base_asset in base_coins or quote_asset in base_coins):
            continue

        # --- Крок 3: Фільтрація за обсягом торгів --- 
        ticker_data = ticker_map.get(pair)
        if not ticker_data:
            continue

        volume_usd = Decimal(ticker_data.get('quoteVolume', 0))
        if volume_usd < min_volume_usd:
            continue

        # --- Крок 4: Фільтрація за мінімальною номінальною вартістю (Notional Value) --- 
        min_notional = Decimal(0)
        for f in symbol_info['filters']:
            if f['filterType'] == 'MIN_NOTIONAL' or f['filterType'] == 'NOTIONAL':
                min_notional = Decimal(f.get('minNotional', '0'))
                break
        # Цей фільтр відсіює пари, де навіть мінімальний ордер занадто великий
        if min_notional > 0 and volume_usd < min_notional:
            continue

        # Якщо всі перевірки пройдено, додаємо пару до списку кандидатів
        valid_pairs.append({
            'symbol': pair,
            'baseAsset': base_asset,
            'quoteAsset': quote_asset,
            'quoteVolume': volume_usd
        })

    # Сортуємо пари за обсягом у спадаючому порядку і беремо N найкращих
    sorted_pairs = sorted(valid_pairs, key=lambda p: p['quoteVolume'], reverse=True)
    top_pairs = sorted_pairs[:top_n_pairs]

    # Формуємо кінцевий білий список з активів та пар
    whitelist_assets = set(base_coins)
    whitelist_pairs = set()
    for pair_data in top_pairs:
        whitelist_pairs.add(pair_data['symbol'])
        whitelist_assets.add(pair_data['baseAsset'])
        whitelist_assets.add(pair_data['quoteAsset'])

    logger.info(f"Білий список згенеровано: {len(whitelist_assets)} активів та {len(whitelist_pairs)} пар.")

    # Зберігаємо результат у файл
    output_path = "configs/whitelist.json"
    try:
        with open(output_path, 'w') as f:
            json.dump({
                "whitelist_assets": sorted(list(whitelist_assets)),
                "whitelist_pairs": sorted(list(whitelist_pairs))
            }, f, indent=2)
        logger.info(f"Білий список збережено у {output_path}")
    except IOError as e:
        logger.error(f"Помилка збереження білого списку у {output_path}: {e}")

if __name__ == '__main__':
    # Цей блок виконується, якщо скрипт запускається напряму
    # Використовується для тестування та ручної генерації.
    config.load_config()
    logging.basicConfig(level=logging.INFO)
    generate_whitelist()