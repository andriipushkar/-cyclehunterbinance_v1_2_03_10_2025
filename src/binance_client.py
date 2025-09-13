from binance.client import Client
from config import API_KEY, API_SECRET

class BinanceClient:
    def __init__(self):
        self.client = Client(API_KEY, API_SECRET)

    def get_spot_balance(self):
        account = self.client.get_account()
        balances = account.get('balances', [])
        return [
            {"asset": b["asset"], "total": b["free"]}
            for b in balances
            if float(b["free"]) > 0
        ]

    def get_futures_balance(self):
        account = self.client.futures_account_balance()
        return [
            {"asset": b["asset"], "balance": b["balance"]}
            for b in account
            if float(b["balance"]) > 0
        ]

    def get_symbol_price(self, asset):
        if asset in ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'PAX', 'HUSD']:
            return 1.0
        try:
            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
            return float(ticker['price'])
        except Exception:
            return None

    def get_earn_balance(self):
        earn_balances = []
        try:
            flexible_positions = self.client.get_simple_earn_flexible_product_position()
            if flexible_positions and 'rows' in flexible_positions:
                for position in flexible_positions['rows']:
                    earn_balances.append({"asset": position['asset'], "total": position['totalAmount']})

            locked_positions = self.client.get_simple_earn_locked_product_position()
            if locked_positions and 'rows' in locked_positions:
                for position in locked_positions['rows']:
                    # Check if the asset already exists in earn_balances to sum them up
                    found = False
                    for balance in earn_balances:
                        if balance['asset'] == position['asset']:
                            balance['total'] = str(float(balance['total']) + float(position['amount']))
                            found = True
                            break
                    if not found:
                        earn_balances.append({"asset": position['asset'], "total": position['amount']})
        except Exception as e:
            print(f"Could not retrieve earn balance: {e}")

        return earn_balances
