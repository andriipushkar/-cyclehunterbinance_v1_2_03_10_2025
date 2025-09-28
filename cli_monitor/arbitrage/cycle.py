"""
Цей модуль визначає клас `Cycle`, який представляє один арбітражний цикл.
"""

from decimal import Decimal

class Cycle:
    """Представляє арбітражний цикл.

    Атрибути:
        coins (list): Список монет у циклі (наприклад, ['USDT', 'BTC', 'ETH', 'USDT']).
        steps (list): Список кроків (угод) для виконання циклу.
    """

    def __init__(self, coins, steps):
        """
        Ініціалізує об'єкт циклу.

        Args:
            coins (list): Список назв монет.
            steps (list): Список словників, що описують кроки торгівлі.
        """
        self.coins = coins
        self.steps = steps

    def __str__(self):
        """Повертає рядкове представлення циклу."""
        return ' -> '.join(self.coins)

    def calculate_profit(self, prices, symbols_info, trade_fees):
        """
        Розраховує прибутковість циклу на основі поточних цін.

        Симулює послідовність угод, починаючи з 1 одиниці базової валюти,
        враховуючи ціни купівлі/продажу (ask/bid) та торгові комісії.

        Args:
            prices (dict): Словник з поточними цінами bid/ask для потрібних пар.
            symbols_info (dict): Словник з інформацією про символи (для визначення базового/котирувального активу).
            trade_fees (dict): Словник з торговими комісіями для пар.

        Returns:
            Decimal: Відсоток прибутку (або збитку, якщо значення від'ємне).
        
        Raises:
            KeyError: Якщо для якоїсь пари відсутня необхідна інформація.
        """
        # Починаємо з 1 одиниці для розрахунку відносного прибутку
        amount = Decimal('1.0')
        
        for step in self.steps:
            pair_symbol = step['pair']
            from_coin = step['from']
            
            if pair_symbol not in symbols_info:
                raise KeyError(f"Відсутній ключ '{pair_symbol}' в symbols_info")
            pair_info = symbols_info[pair_symbol]

            if pair_symbol not in prices:
                raise KeyError(f"Відсутній ключ '{pair_symbol}' в prices")
            price_info = prices[pair_symbol]

            # Використовуємо комісію для пари або стандартну, якщо вона не знайдена
            trading_fee = trade_fees.get(pair_symbol, Decimal('0.001'))

            # Визначаємо, купуємо ми чи продаємо базовий актив
            if from_coin == pair_info['quoteAsset']:  # Купуємо базовий актив
                price = Decimal(price_info['a'])  # Використовуємо ціну ask (ціна, за якою продають)
                if price == 0: return Decimal('0.0')
                amount = amount / price
            else:  # Продаємо базовий актив
                price = Decimal(price_info['b'])  # Використовуємо ціну bid (ціна, за якою купують)
                amount = amount * price
            
            # Віднімаємо торгову комісію
            amount *= (Decimal('1') - trading_fee)

        # Розраховуємо кінцевий відсоток прибутку
        profit_pct = ((amount - Decimal('1.0')) / Decimal('1.0')) * Decimal('100')
        return profit_pct