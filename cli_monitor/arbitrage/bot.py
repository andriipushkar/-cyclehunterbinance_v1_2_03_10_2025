"""
Цей модуль визначає головний клас `ArbitrageBot`, який відповідає за
оркестрацію всього процесу арбітражу: від аналізу ринку до симуляції угод.
"""

import asyncio
from loguru import logger
import csv
import os
from datetime import datetime
from decimal import Decimal
import aiofiles

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config

from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .cycle_finder import CycleFinder
from .profit_calculator import ProfitMonitor


class TradeExecutor:
    """
    Клас, що відповідає за виконання (симуляцію) торгових циклів.
    """

    def __init__(self, client: BinanceClient, exchange_info: dict):
        """
        Ініціалізує екзекутор.
        """
        self.client = client
        self.exchange_info = exchange_info
        self.initial_investment = Decimal(config.initial_investment_usd)
        self.min_volume_threshold = Decimal(config.min_trade_volume_usd)
        self.max_slippage_pct = Decimal(config.max_slippage_pct)

    @classmethod
    async def create(cls, client: BinanceClient):
        exchange_info = {s['symbol']: s for s in (await client.get_exchange_info())['symbols']}
        return cls(client, exchange_info)

    async def _log_to_csv(self, cycle_str, profit_pct, initial_amount, final_amount, initial_asset, final_asset):
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        hour_str = now.strftime('%H')
        
        dir_path = os.path.join('output', 'trades', date_str)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{hour_str}.csv")
        
        file_exists = os.path.isfile(file_path)
        
        fieldnames = [
            'timestamp', 'cycle', 'profit_pct', 
            'initial_asset', 'initial_amount',
            'final_asset', 'final_amount'
        ]
        
        row_data = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'cycle': cycle_str,
            'profit_pct': f"{profit_pct:.4f}",
            'initial_asset': initial_asset,
            'initial_amount': f"{initial_amount:.8f}",
            'final_asset': final_asset,
            'final_amount': f"{final_amount:.8f}"
        }

        try:
            async with aiofiles.open(file_path, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    await writer.writeheader()
                await writer.writerow(row_data)
        except IOError as e:
            logger.error(f"[CSV LOG] Помилка запису у файл {file_path}: {e}")

    async def _find_optimal_investment_amount(self, order_book, side):
        total_amount = Decimal('0')
        total_cost = Decimal('0')
        first_price = None

        if side == 'BUY':
            levels = order_book['asks']
            if not levels: return Decimal('0')
            first_price = Decimal(levels[0][0])

            for price_str, qty_str in levels:
                price = Decimal(price_str)
                qty = Decimal(qty_str)
                
                slippage = (price - first_price) / first_price * 100
                if slippage > self.max_slippage_pct:
                    break
                
                total_amount += qty
                total_cost += qty * price

        elif side == 'SELL':
            levels = order_book['bids']
            if not levels: return Decimal('0')
            first_price = Decimal(levels[0][0])

            for price_str, qty_str in levels:
                price = Decimal(price_str)
                qty = Decimal(qty_str)

                slippage = (first_price - price) / first_price * 100
                if slippage > self.max_slippage_pct:
                    break
                
                total_amount += qty
                total_cost += qty * price
        
        return total_cost if side == 'BUY' else total_amount

    async def _calculate_execution_price(self, order_book, side, amount_to_trade):
        total_spent = Decimal('0')
        total_filled = Decimal('0')
        remaining_amount = amount_to_trade

        if side == 'BUY':
            for price_str, qty_str in order_book['asks']:
                price = Decimal(price_str)
                qty = Decimal(qty_str)
                
                cost_of_level = price * qty

                if remaining_amount >= cost_of_level:
                    total_spent += cost_of_level
                    total_filled += qty
                    remaining_amount -= cost_of_level
                else:
                    filled_qty = remaining_amount / price
                    total_spent += remaining_amount
                    total_filled += filled_qty
                    remaining_amount = Decimal('0')
                    break
            if total_filled == 0:
                return None, None
            avg_price = total_spent / total_filled
            return avg_price, total_filled

        elif side == 'SELL':
            for price_str, qty_str in order_book['bids']:
                price = Decimal(price_str)
                qty = Decimal(qty_str)

                if remaining_amount >= qty:
                    total_spent += qty
                    total_filled += qty * price
                    remaining_amount -= qty
                else:
                    total_spent += remaining_amount
                    total_filled += remaining_amount * price
                    remaining_amount = Decimal('0')
                    break
            if total_spent == 0:
                return None, None
            avg_price = total_filled / total_spent
            return avg_price, total_filled

        return None, None

    async def execute_cycle(self, profitable_cycle: dict):
        cycle = profitable_cycle['cycle']
        profit_pct = profitable_cycle['profit_pct']

        pairs_in_cycle = [step['pair'] for step in cycle.steps]
        tickers = await self.client.get_tickers_for_symbols(pairs_in_cycle)

        if not tickers or len(tickers) != len(pairs_in_cycle):
            logger.warning(f"[LIQUIDITY CHECK] Не вдалося отримати дані тікера для циклу {cycle}. Цикл пропущено.")
            return

        for ticker in tickers:
            volume = Decimal(ticker.get('quoteVolume', '0'))
            if volume < self.min_volume_threshold:
                logger.warning(f"[LIQUIDITY CHECK] Пара {ticker['symbol']} має недостатній обсяг торгів (${volume:,.2f}). Поріг: ${self.min_volume_threshold:,.2f}. Цикл {cycle} пропущено.")
                return
        
        logger.info(f"[LIQUIDITY CHECK] Усі пари в циклі {cycle} пройшли перевірку на ліквідність.")
        
        first_step = cycle.steps[0]
        first_pair_order_book = await self.client.get_order_book(first_step['pair'])
        if not first_pair_order_book:
            logger.error(f"[DRY RUN] Не вдалося отримати стакан ордерів для першого кроку: {first_step['pair']}")
            return

        first_side = "BUY" if first_step['from'] == self.exchange_info[first_step['pair']]['quoteAsset'] else "SELL"
        optimal_investment = await self._find_optimal_investment_amount(first_pair_order_book, first_side)
        current_amount = min(self.initial_investment, optimal_investment)
        
        logger.info("="*50)
        logger.info(f"[DRY RUN] ОТРИМАНО ПРИБУТКОВИЙ ЦИКЛ: {cycle} | Прибуток: {profit_pct:.4f}%")
        logger.info(f"[DRY RUN] Початкова інвестиція (скоригована): {current_amount:.8f} {cycle.steps[0]['from']}")

        current_asset = cycle.steps[0]['from']

        for i, step in enumerate(cycle.steps):
            pair = step['pair']
            from_asset = step['from']
            to_asset = step['to']
            
            if current_asset != from_asset:
                logger.error(f"[DRY RUN] Помилка логіки: поточний актив {current_asset} не співпадає з очікуваним {from_asset}")
                return

            order_book = await self.client.get_order_book(pair)
            if not order_book:
                logger.error(f"[DRY RUN] Не вдалося отримати стакан ордерів для пари {pair}")
                return

            pair_info = self.exchange_info.get(pair)
            if not pair_info:
                logger.error(f"[DRY RUN] Не вдалося знайти інформацію про пару {pair}")
                return

            base_asset = pair_info['baseAsset']
            quote_asset = pair_info['quoteAsset']

            side = None
            if from_asset == quote_asset and to_asset == base_asset:
                side = "BUY"
            elif from_asset == base_asset and to_asset == quote_asset:
                side = "SELL"
            
            if side is None:
                logger.error(f"[DRY RUN] Не вдалося визначити напрямок торгівлі для кроку {step}")
                return

            avg_price, filled_amount = await self._calculate_execution_price(order_book, side, current_amount)

            if avg_price is None or filled_amount is None:
                logger.error(f"[DRY RUN] Не вдалося розрахувати ціну виконання для {pair} з обсягом {current_amount}")
                return

            if side == "BUY":
                logger.info(f"[DRY RUN] Крок {i+1}: {side} {filled_amount:.8f} {to_asset} за середньою ціною {avg_price:.8f} (пара {pair})")
                current_amount = filled_amount
                current_asset = to_asset
            else: # SELL
                logger.info(f"[DRY RUN] Крок {i+1}: {side} {current_amount:.8f} {from_asset} за середньою ціною {avg_price:.8f} (пара {pair})")
                current_amount = filled_amount
                current_asset = to_asset
        
        final_amount = current_amount
        final_asset = current_asset

        logger.info(f"[DRY RUN] Очікуваний кінцевий баланс: {final_amount:.8f} {final_asset}")
        logger.info("="*50)

        await self._log_to_csv(
            cycle_str=str(cycle),
            profit_pct=profit_pct,
            initial_amount=self.initial_investment,
            final_amount=final_amount,
            initial_asset=cycle.steps[0]['from'],
            final_asset=final_asset
        )


class ArbitrageBot:
    """
    Головний клас бота, що керує всім процесом арбітражу.
    """

    def __init__(self, client: BinanceClient, trade_executor: TradeExecutor):
        """Ініціалізує бота."""
        self.profit_monitor = None
        self.client = client
        self.trade_executor = trade_executor

    @classmethod
    async def create(cls):
        client = await BinanceClient.create()
        trade_executor = await TradeExecutor.create(client)
        return cls(client, trade_executor)

    async def _perform_setup(self):
        """
        Виконує початкові кроки налаштування, необхідні для роботи бота.
        """
        logger.info("Початок налаштування...")
        
        logger.info("Генерація білого списку...")
        await generate_whitelist()
        
        logger.info("Генерація чорного списку...")
        await generate_blacklist()

        finder = None
        try:
            finder = await CycleFinder.create()
            logger.info("Отримання списку монет для моніторингу...")
            allowed_coins = await finder.get_allowed_coins(strategy='liquidity')
            if allowed_coins:
                try:
                    async with aiofiles.open("output/monitored_coins.txt", "w") as f:
                        await f.write("\n".join(sorted(list(allowed_coins))))
                    logger.info(f"Список з {len(allowed_coins)} монет, що моніторяться, збережено у output/monitored_coins.txt")
                except IOError as e:
                    logger.error(f"Помилка збереження списку монет: {e}")
            
            logger.info("Пошук арбітражних циклів на основі білого списку...")
            await finder.run(strategy='liquidity')
        finally:
            if finder and finder.client:
                await finder.client.close_connection()
        
        logger.info("Налаштування завершено.")

    async def start(self):
        """
        Запускає головний нескінченний цикл роботи бота.
        """
        try:
            await self._perform_setup()

            profitable_cycles_queue = asyncio.Queue()
            self.profit_monitor = ProfitMonitor(profitable_cycles_queue=profitable_cycles_queue)
            monitor_task = asyncio.create_task(self.profit_monitor.start())
            logger.info("Монітор прибутковості запущено. Очікування на вигідні цикли...")

            while True:
                profitable_cycle = await profitable_cycles_queue.get()
                await self.trade_executor.execute_cycle(profitable_cycle)
                profitable_cycles_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Роботу бота зупинено.")
        except Exception as e:
            logger.error(f"В головному циклі бота сталася неочікувана помилка: {e}", exc_info=True)
        finally:
            if self.profit_monitor:
                await self.profit_monitor.stop()
            if self.client:
                await self.client.close_connection()


async def main():
    """Асинхронна точка входу для запуску бота з командного рядка."""
    bot = None
    try:
        bot = await ArbitrageBot.create()
        await bot.start()
    except asyncio.CancelledError:
        logger.info("Роботу бота було скасовано.")
    finally:
        if bot and bot.client:
            await bot.client.close_connection()