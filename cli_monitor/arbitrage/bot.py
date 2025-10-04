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

from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config

from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .cycle_finder import CycleFinder
from .profit_calculator import ProfitMonitor


class TradeExecutor:
    """
    Клас, що відповідає за виконання (симуляцію) торгових циклів.

    Основні завдання:
    - Перевірка ліквідності циклу.
    - Динамічний розрахунок оптимального обсягу інвестиції.
    - Симуляція угод по стакану ордерів для розрахунку реального прибутку.
    - Логування результатів симуляції.
    
    В поточному стані працює в режимі "dry run" (сухий запуск), імітуючи угоди
    без реального розміщення ордерів.
    """

    def __init__(self, client: BinanceClient):
        """
        Ініціалізує екзекутор.

        Args:
            client (BinanceClient): Клієнт для взаємодії з API Binance.
        """
        self.client = client
        # Завантаження параметрів з конфігурації
        self.initial_investment = Decimal(config.initial_investment_usd)
        self.min_volume_threshold = Decimal(config.min_trade_volume_usd)
        self.max_slippage_pct = Decimal(config.max_slippage_pct)
        # Отримання та кешування інформації про всі торгові пари
        self.exchange_info = {s['symbol']: s for s in self.client.get_exchange_info()['symbols']}

    async def _log_to_csv(self, cycle_str, profit_pct, initial_amount, final_amount, initial_asset, final_asset):
        """
        Логує результат симуляції торгового циклу у CSV-файл.

        Файли створюються погодинно в папці `output/trades/РІК-МІСЯЦЬ-ДЕНЬ/ГОДИНА.csv`.
        """
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        hour_str = now.strftime('%H')
        
        # Створення директорії, якщо вона не існує
        dir_path = os.path.join('output', 'trades', date_str)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{hour_str}.csv")
        
        # Перевірка, чи файл вже існує (щоб не дублювати заголовки)
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
            with open(file_path, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader() # Додаємо заголовок, якщо файл новий
                writer.writerow(row_data)
        except IOError as e:
            logger.error(f"[CSV LOG] Помилка запису у файл {file_path}: {e}")

    def _find_optimal_investment_amount(self, order_book, side):
        """
        Знаходить оптимальний обсяг інвестиції на основі аналізу глибини стакану
        та максимально допустимого прослизання.

        Це дозволяє визначити, яку суму можна "влити" в ринок, щоб не сильно
        змінити ціну і не втратити потенційний прибуток.

        Args:
            order_book (dict): Стакан ордерів для торгової пари.
            side (str): Напрямок торгівлі ('BUY' або 'SELL').

        Returns:
            Decimal: Оптимальна сума для інвестиції.
        """
        total_amount = Decimal('0')
        total_cost = Decimal('0')
        first_price = None

        if side == 'BUY':
            levels = order_book['asks'] # Ордери на продаж
            if not levels: return Decimal('0')
            first_price = Decimal(levels[0][0]) # Найкраща (найнижча) ціна продажу

            # Ітеруємо по рівнях стакану, поки прослизання не перевищить поріг
            for price_str, qty_str in levels:
                price = Decimal(price_str)
                qty = Decimal(qty_str)
                
                slippage = (price - first_price) / first_price * 100
                if slippage > self.max_slippage_pct:
                    break # Зупиняємось, якщо прослизання занадто велике
                
                total_amount += qty
                total_cost += qty * price

        elif side == 'SELL':
            levels = order_book['bids'] # Ордери на купівлю
            if not levels: return Decimal('0')
            first_price = Decimal(levels[0][0]) # Найкраща (найвища) ціна купівлі

            for price_str, qty_str in levels:
                price = Decimal(price_str)
                qty = Decimal(qty_str)

                slippage = (first_price - price) / first_price * 100
                if slippage > self.max_slippage_pct:
                    break
                
                total_amount += qty
                total_cost += qty * price
        
        # Для 'BUY' повертаємо загальну вартість (в quote asset), 
        # для 'SELL' - загальну кількість (в base asset).
        return total_cost if side == 'BUY' else total_amount

    def _calculate_execution_price(self, order_book, side, amount_to_trade):
        """
        Розраховує середню ціну виконання та отриману кількість, симулюючи угоду по стакану.

        Цей метод "проходить" по стакану ордерів, "викуповуючи" або "продаючи"
        активи на задану суму, і розраховує, якою буде середня ціна угоди
        та скільки активу буде отримано в результаті.

        Args:
            order_book (dict): Стакан ордерів (bids, asks).
            side (str): 'BUY' або 'SELL'.
            amount_to_trade (Decimal): Кількість активу для торгівлі.

        Returns:
            tuple: (середня_ціна, отримана_кількість) або (None, None) у разі помилки.
        """
        total_spent = Decimal('0')
        total_filled = Decimal('0')
        remaining_amount = amount_to_trade

        if side == 'BUY':
            # Ми хочемо купити базовий актив, витрачаючи котирувальний (amount_to_trade).
            # Ітеруємо по asks (ордери на продаж), починаючи з найдешевшого.
            for price_str, qty_str in order_book['asks']:
                price = Decimal(price_str)
                qty = Decimal(qty_str)
                
                cost_of_level = price * qty

                if remaining_amount >= cost_of_level:
                    # Ми можемо викупити весь рівень
                    total_spent += cost_of_level
                    total_filled += qty
                    remaining_amount -= cost_of_level
                else:
                    # Ми викуповуємо лише частину рівня
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
            # Ми хочемо продати базовий актив (amount_to_trade), отримуючи котирувальний.
            # Ітеруємо по bids (ордери на купівлю), починаючи з найдорожчого.
            for price_str, qty_str in order_book['bids']:
                price = Decimal(price_str)
                qty = Decimal(qty_str)

                if remaining_amount >= qty:
                    # Ми можемо задовольнити весь цей ордер на купівлю
                    total_spent += qty
                    total_filled += qty * price
                    remaining_amount -= qty
                else:
                    # Ми задовольняємо лише частину ордера
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
        """
        Виконує повний цикл симуляції для знайденого прибуткового циклу.

        Args:
            profitable_cycle (dict): Словник з інформацією про прибутковий цикл 
                                     (сам цикл, прибуток, ціни).
        """
        cycle = profitable_cycle['cycle']
        profit_pct = profitable_cycle['profit_pct']
        prices = profitable_cycle['prices']

        # --- Крок 1: Перевірка ліквідності ---
        # Переконуємось, що 24-годинний обсяг торгів для кожної пари в циклі
        # перевищує мінімальний поріг з конфігурації.
        pairs_in_cycle = [step['pair'] for step in cycle.steps]
        tickers = await asyncio.to_thread(self.client.get_tickers_for_symbols, pairs_in_cycle)

        if not tickers or len(tickers) != len(pairs_in_cycle):
            logger.warning(f"[LIQUIDITY CHECK] Не вдалося отримати дані тікера для циклу {cycle}. Цикл пропущено.")
            return

        for ticker in tickers:
            volume = Decimal(ticker.get('quoteVolume', '0'))
            if volume < self.min_volume_threshold:
                logger.warning(f"[LIQUIDITY CHECK] Пара {ticker['symbol']} має недостатній обсяг торгів (${volume:,.2f}). Поріг: ${self.min_volume_threshold:,.2f}. Цикл {cycle} пропущено.")
                return
        
        logger.info(f"[LIQUIDITY CHECK] Усі пари в циклі {cycle} пройшли перевірку на ліквідність.")
        
        # --- Крок 2: Динамічний розрахунок обсягу інвестиції ---
        # Визначаємо оптимальний обсяг для першої угоди в циклі, щоб мінімізувати прослизання.
        first_step = cycle.steps[0]
        first_pair_order_book = self.client.get_order_book(first_step['pair'])
        if not first_pair_order_book:
            logger.error(f"[DRY RUN] Не вдалося отримати стакан ордерів для першого кроку: {first_step['pair']}")
            return

        first_side = "BUY" if first_step['from'] == self.exchange_info[first_step['pair']]['quoteAsset'] else "SELL"
        optimal_investment = self._find_optimal_investment_amount(first_pair_order_book, first_side)
        # Використовуємо менше з двох значень: налаштованої початкової інвестиції або розрахованої оптимальної.
        current_amount = min(self.initial_investment, optimal_investment)
        
        logger.info("="*50)
        logger.info(f"[DRY RUN] ОТРИМАНО ПРИБУТКОВИЙ ЦИКЛ: {cycle} | Прибуток: {profit_pct:.4f}%")
        logger.info(f"[DRY RUN] Початкова інвестиція (скоригована): {current_amount:.8f} {cycle.steps[0]['from']}")

        current_asset = cycle.steps[0]['from']

        # --- Крок 3: Покрокова симуляція угоди ---
        for i, step in enumerate(cycle.steps):
            pair = step['pair']
            from_asset = step['from']
            to_asset = step['to']
            
            if current_asset != from_asset:
                logger.error(f"[DRY RUN] Помилка логіки: поточний актив {current_asset} не співпадає з очікуваним {from_asset}")
                return

            # Отримуємо актуальний стакан ордерів для поточної пари
            order_book = self.client.get_order_book(pair)
            if not order_book:
                logger.error(f"[DRY RUN] Не вдалося отримати стакан ордерів для пари {pair}")
                return

            pair_info = self.exchange_info.get(pair)
            if not pair_info:
                logger.error(f"[DRY RUN] Не вдалося знайти інформацію про пару {pair}")
                return

            base_asset = pair_info['baseAsset']
            quote_asset = pair_info['quoteAsset']

            # Визначаємо напрямок торгівлі (BUY або SELL)
            side = None
            if from_asset == quote_asset and to_asset == base_asset:
                side = "BUY"
            elif from_asset == base_asset and to_asset == quote_asset:
                side = "SELL"
            
            if side is None:
                logger.error(f"[DRY RUN] Не вдалося визначити напрямок торгівлі для кроку {step}")
                return

            # Розраховуємо результат угоди на основі стакану
            avg_price, filled_amount = self._calculate_execution_price(order_book, side, current_amount)

            if avg_price is None or filled_amount is None:
                logger.error(f"[DRY RUN] Не вдалося розрахувати ціну виконання для {pair} з обсягом {current_amount}")
                return

            # Оновлюємо поточний актив та його кількість для наступного кроку
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

        # --- Крок 4: Логування результату ---
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
    Це оркестратор, який запускає та координує всі інші компоненти.
    """

    def __init__(self):
        """Ініціалізує бота, створюючи екземпляри клієнта та екзекутора."""
        self.profit_monitor = None
        self.client = BinanceClient()
        self.trade_executor = TradeExecutor(self.client)

    async def _perform_setup(self):
        """
        Виконує початкові кроки налаштування, необхідні для роботи бота.
        Цей метод запускається один раз при старті.
        """
        logger.info("Початок налаштування...")
        
        # 1. Генерація білого списку найліквідніших активів
        logger.info("Генерація білого списку...")
        generate_whitelist()
        
        # 2. Генерація чорного списку найменш ліквідних активів
        logger.info("Генерація чорного списку...")
        generate_blacklist()

        finder = CycleFinder()

        # 3. Отримання та збереження списку монет, що будуть моніторитись
        logger.info("Отримання списку монет для моніторингу...")
        allowed_coins = finder.get_allowed_coins(strategy='liquidity')
        if allowed_coins:
            try:
                with open("output/monitored_coins.txt", "w") as f:
                    f.write("\n".join(sorted(list(allowed_coins))))
                logger.info(f"Список з {len(allowed_coins)} монет, що моніторяться, збережено у output/monitored_coins.txt")
            except IOError as e:
                logger.error(f"Помилка збереження списку монет: {e}")
        
        # 4. Пошук всіх можливих арбітражних циклів на основі білого списку
        logger.info("Пошук арбітражних циклів на основі білого списку...")
        finder.run(strategy='liquidity')
        
        logger.info("Налаштування завершено.")

    async def start(self):
        """
        Запускає головний нескінченний цикл роботи бота.
        """
        try:
            # Крок 1: Виконання початкових налаштувань
            await self._perform_setup()

            # Крок 2: Створення черги та запуск моніторингу прибутковості
            # ProfitMonitor буде знаходити вигідні цикли і додавати їх у чергу.
            profitable_cycles_queue = asyncio.Queue()
            self.profit_monitor = ProfitMonitor(profitable_cycles_queue=profitable_cycles_queue)
            monitor_task = asyncio.create_task(self.profit_monitor.start())
            logger.info("Монітор прибутковості запущено. Очікування на вигідні цикли...")

            # Крок 3: Обробка циклів з черги
            # Цей цикл безкінечно чекає на нові елементи в черзі.
            while True:
                # Отримуємо прибутковий цикл з черги
                profitable_cycle = await profitable_cycles_queue.get()
                # Передаємо його на симуляцію виконання
                await self.trade_executor.execute_cycle(profitable_cycle)
                # Повідомляємо чергу, що завдання виконано
                profitable_cycles_queue.task_done()

        except asyncio.CancelledError:
            # Обробка зупинки бота (наприклад, через Ctrl+C)
            logger.info("Роботу бота зупинено.")
            if self.profit_monitor:
                await self.profit_monitor.stop()
        except Exception as e:
            logger.error(f"В головному циклі бота сталася неочікувана помилка: {e}", exc_info=True)
            if self.profit_monitor:
                await self.profit_monitor.stop()


async def main():
    """Асинхронна точка входу для запуску бота з командного рядка."""
    bot = ArbitrageBot()
    await bot.start()
