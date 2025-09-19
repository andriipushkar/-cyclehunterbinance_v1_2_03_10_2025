from decimal import Decimal

def calculate_profit(steps, prices, symbols_info, trading_fee):
    """
    Calculates the profit for a given cycle.

    Args:
        steps (list): A list of dictionaries representing the steps of the cycle.
        prices (dict): A dictionary containing the prices of the pairs.
        symbols_info (dict): A dictionary containing the information about the symbols.
        trading_fee (Decimal): The trading fee.

    Returns:
        Decimal: The profit percentage.
    """
    amount = Decimal('1.0')
    for step in steps:
        pair_symbol = step['pair']
        from_coin = step['from']
        
        pair_info = symbols_info[pair_symbol]
        price_info = prices[pair_symbol]

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
