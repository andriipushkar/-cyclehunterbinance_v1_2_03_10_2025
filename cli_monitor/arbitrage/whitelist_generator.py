import asyncio
from decimal import Decimal
from loguru import logger

from .list_generator_base import BaseListGenerator


class WhitelistGenerator(BaseListGenerator):
    """
    Генерує білий список активів та пар на основі критеріїв ліквідності.
    """

    async def _generate_list(self):
        """Реалізує логіку фільтрації та створення білого списку."""
        logger.info("Початок генерації білого списку...")

        base_coins = self.config.whitelist_base_coins
        min_volume_usd = Decimal(self.config.whitelist_min_volume_usd)
        top_n_pairs = self.config.whitelist_top_n_pairs

        if not base_coins:
            logger.error("Базові монети для білого списку не налаштовані. Скасування.")
            return

        ticker_map = {ticker['symbol']: ticker for ticker in self.tickers}
        valid_pairs = []

        for symbol_info in self.exchange_info.get('symbols', []):
            if self._is_valid_pair(symbol_info, ticker_map, base_coins, min_volume_usd):
                valid_pairs.append({
                    'symbol': symbol_info['symbol'],
                    'baseAsset': symbol_info['baseAsset'],
                    'quoteAsset': symbol_info['quoteAsset'],
                    'quoteVolume': Decimal(ticker_map[symbol_info['symbol']].get('quoteVolume', 0))
                })

        sorted_pairs = sorted(valid_pairs, key=lambda p: p['quoteVolume'], reverse=True)
        top_pairs = sorted_pairs[:top_n_pairs]

        whitelist_assets = set(base_coins)
        whitelist_pairs = set()
        for pair_data in top_pairs:
            whitelist_pairs.add(pair_data['symbol'])
            whitelist_assets.add(pair_data['baseAsset'])
            whitelist_assets.add(pair_data['quoteAsset'])

        logger.info(f"Білий список згенеровано: {len(whitelist_assets)} активів та {len(whitelist_pairs)} пар.")

        await self._save_list(
            data={
                "whitelist_assets": sorted(list(whitelist_assets)),
                "whitelist_pairs": sorted(list(whitelist_pairs))
            },
            output_path="configs/whitelist.json"
        )

    def _is_valid_pair(self, symbol_info, ticker_map, base_coins, min_volume_usd):
        """Перевіряє, чи відповідає торгова пара критеріям білого списку."""
        pair = symbol_info['symbol']
        base_asset = symbol_info['baseAsset']
        quote_asset = symbol_info['quoteAsset']

        if symbol_info['status'] != 'TRADING':
            return False

        if not (base_asset in base_coins or quote_asset in base_coins):
            return False

        ticker_data = ticker_map.get(pair)
        if not ticker_data:
            return False

        volume_usd = Decimal(ticker_data.get('quoteVolume', 0))
        if volume_usd < min_volume_usd:
            return False

        for f in symbol_info['filters']:
            if f['filterType'] in ('MIN_NOTIONAL', 'NOTIONAL'):
                min_notional = Decimal(f.get('minNotional', '0'))
                if min_notional > 0 and volume_usd < min_notional:
                    return False
                break
        
        return True


async def generate_whitelist():
    """Точка входу для запуску генератора білого списку."""
    generator = await WhitelistGenerator.create()
    await generator.run()


if __name__ == '__main__':
    asyncio.run(generate_whitelist())