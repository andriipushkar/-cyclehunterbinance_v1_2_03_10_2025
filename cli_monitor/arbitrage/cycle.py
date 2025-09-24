from decimal import Decimal

class Cycle:
    """Represents an arbitrage cycle."""

    def __init__(self, coins, steps):
        self.coins = coins
        self.steps = steps

    def __str__(self):
        return ' -> '.join(self.coins)

    def calculate_profit(self, prices, symbols_info, trade_fees):
        """
        Calculates the profit for the cycle.

        Args:
            prices (dict): A dictionary containing the prices of the pairs.
            symbols_info (dict): A dictionary containing the information about the symbols.
            trade_fees (dict): A dictionary containing the trade fees for each pair.

        Returns:
            Decimal: The profit percentage.
        """
        amount = Decimal('1.0')
        for step in self.steps:
            pair_symbol = step['pair']
            from_coin = step['from']
            
            if pair_symbol not in symbols_info:
                raise KeyError(f"Missing key '{pair_symbol}' in symbols_info")
            pair_info = symbols_info[pair_symbol]

            if pair_symbol not in prices:
                raise KeyError(f"Missing key '{pair_symbol}' in prices")
            price_info = prices[pair_symbol]

            trading_fee = trade_fees.get(pair_symbol, Decimal('0.001'))

            if from_coin == pair_info['quoteAsset']: # Buying the base asset
                price = Decimal(price_info['a']) # Use ask price
                if price == 0: return Decimal('0.0')
                amount = amount / price
            else: # Selling the base asset
                price = Decimal(price_info['b']) # Use bid price
                amount = amount * price
            
            amount *= (Decimal('1') - trading_fee)

        profit_pct = ((amount - Decimal('1.0')) / Decimal('1.0')) * Decimal('100')
        return profit_pct
