import pytest
from decimal import Decimal
from cli_monitor.arbitrage.cycle import Cycle

MOCK_SYMBOLS_INFO = {
    'BTCUSDT': {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'status': 'TRADING'},
    'ETHUSDT': {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT', 'status': 'TRADING'},
    'ETHBTC': {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC', 'status': 'TRADING'},
}

@pytest.fixture
def trade_fees():
    return {
        'BTCUSDT': Decimal('0.001'),
        'ETHBTC': Decimal('0.001'),
        'ETHUSDT': Decimal('0.001'),
    }

def test_profitable_cycle(trade_fees):
    cycle = Cycle(
        coins=["USDT", "BTC", "ETH", "USDT"],
        steps=[
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    )
    prices = {
        'BTCUSDT': {'a': '50000', 'b': '49999'},
        'ETHBTC': {'a': '0.05', 'b': '0.0499'},
        'ETHUSDT': {'a': '2501', 'b': '2550'}, # Profitable
    }
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    assert profit > 0

def test_unprofitable_cycle(trade_fees):
    cycle = Cycle(
        coins=["USDT", "BTC", "ETH", "USDT"],
        steps=[
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    )
    prices = {
        'BTCUSDT': {'a': '50000', 'b': '49999'},
        'ETHBTC': {'a': '0.05', 'b': '0.0499'},
        'ETHUSDT': {'a': '2501', 'b': '2500'},
    }
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    assert profit < 0

def test_zero_price_cycle(trade_fees):
    cycle = Cycle(
        coins=["USDT", "BTC", "ETH", "USDT"],
        steps=[
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    )
    prices = {
        'BTCUSDT': {'a': '0', 'b': '49999'},
        'ETHBTC': {'a': '0.05', 'b': '0.0499'},
        'ETHUSDT': {'a': '2501', 'b': '2500'},
    }
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    assert profit == 0

def test_missing_trade_fee(trade_fees):
    """Test that the default trade fee is used when a fee is missing."""
    cycle = Cycle(
        coins=["USDT", "BTC", "ETH", "USDT"],
        steps=[
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    )
    prices = {
        'BTCUSDT': {'a': '50000', 'b': '49999'},
        'ETHBTC': {'a': '0.05', 'b': '0.0499'},
        'ETHUSDT': {'a': '2501', 'b': '2550'}, # Profitable
    }
    # Remove one of the trade fees
    del trade_fees['ETHUSDT']
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    assert profit > 0
