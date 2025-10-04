"""
Модуль для генерації "чорного списку" (blacklist) монет та торгових пар.
"""

import json
from decimal import Decimal
from loguru import logger

from .list_generator_base import BaseListGenerator


class BlacklistGenerator(BaseListGenerator):
    """
    Генерує чорний список активів та пар з найнижчою ліквідністю.
    """

    def _generate_list(self):
        """Реалізує логіку фільтрації та створення чорного списку."""
        logger.info("Початок генерації чорного списку...")

        bottom_n_pairs = self.config.blacklist_bottom_n_pairs
        whitelist_pairs_set = self._load_whitelist()
        if whitelist_pairs_set is None:
            return

        ticker_map = {ticker['symbol']: ticker for ticker in self.tickers}
        candidate_pairs = []

        for symbol_info in self.exchange_info.get('symbols', []):
            pair = symbol_info['symbol']
            if pair in whitelist_pairs_set or symbol_info['status'] != 'TRADING':
                continue

            ticker_data = ticker_map.get(pair)
            if not ticker_data:
                continue

            volume_usd = Decimal(ticker_data.get('quoteVolume', 0))
            if volume_usd > 0:
                candidate_pairs.append({
                    'symbol': pair,
                    'baseAsset': symbol_info['baseAsset'],
                    'quoteAsset': symbol_info['quoteAsset'],
                    'quoteVolume': volume_usd
                })

        sorted_pairs = sorted(candidate_pairs, key=lambda p: p['quoteVolume'])
        bottom_pairs = sorted_pairs[:bottom_n_pairs]

        blacklist_assets = set()
        blacklist_pairs = set()
        for pair_data in bottom_pairs:
            blacklist_pairs.add(pair_data['symbol'])
            blacklist_assets.add(pair_data['baseAsset'])
            blacklist_assets.add(pair_data['quoteAsset'])

        logger.info(f"Чорний список згенеровано: {len(blacklist_assets)} активів та {len(blacklist_pairs)} пар.")

        self._save_list(
            data={
                "blacklist_assets": sorted(list(blacklist_assets)),
                "blacklist_pairs": sorted(list(blacklist_pairs))
            },
            output_path="configs/blacklist.json"
        )

    def _load_whitelist(self):
        """Завантажує пари з білого списку для їх виключення."""
        whitelist_path = "configs/whitelist.json"
        try:
            with open(whitelist_path, 'r') as f:
                whitelist_data = json.load(f)
            whitelist_pairs_set = set(whitelist_data.get('whitelist_pairs', []))
            logger.info(f"Завантажено {len(whitelist_pairs_set)} пар з білого списку для виключення.")
            return whitelist_pairs_set
        except FileNotFoundError:
            logger.warning(f"Файл білого списку не знайдено: {whitelist_path}. Генерація чорного списку продовжиться без нього.")
            return set()
        except json.JSONDecodeError:
            logger.error(f"Помилка декодування JSON з білого списку: {whitelist_path}. Скасування.")
            return None


def generate_blacklist():
    """Точка входу для запуску генератора чорного списку."""
    generator = BlacklistGenerator()
    generator.run()


if __name__ == '__main__':
    generate_blacklist()
