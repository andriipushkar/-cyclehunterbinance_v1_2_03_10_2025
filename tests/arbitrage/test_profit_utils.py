"""
Тести для логіки розрахунку прибутковості в класі `Cycle`.

Хоча назва файлу `test_profit_utils.py`, він фактично тестує метод
`calculate_profit` з класу `Cycle`, перевіряючи різні сценарії:
- Прибутковий цикл
- Збитковий цикл
- Цикл з нульовою ціною
- Розрахунок з відсутньою торговою комісією (використання значення за замовчуванням)
"""

import pytest
from decimal import Decimal
from cli_monitor.arbitrage.cycle import Cycle

# Мок даних про торгові пари
MOCK_SYMBOLS_INFO = {
    'BTCUSDT': {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'status': 'TRADING'},
    'ETHUSDT': {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT', 'status': 'TRADING'},
    'ETHBTC': {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC', 'status': 'TRADING'},
}

@pytest.fixture
def trade_fees():
    """Фікстура, що надає словник з торговими комісіями."""
    return {
        'BTCUSDT': Decimal('0.001'),
        'ETHBTC': Decimal('0.001'),
        'ETHUSDT': Decimal('0.001'),
    }

def test_profitable_cycle(trade_fees):
    """Тестує розрахунок для завідомо прибуткового циклу."""
    # Arrange
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
        'ETHUSDT': {'a': '2501', 'b': '2550'}, # Ціна продажу ETH вища, що створює прибуток
    }
    
    # Act
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    
    # Assert
    assert profit > 0

def test_unprofitable_cycle(trade_fees):
    """Тестує розрахунок для збиткового циклу."""
    # Arrange
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
        'ETHUSDT': {'a': '2501', 'b': '2500'}, # Ціни близькі, що зі спредом та комісіями дасть збиток
    }
    
    # Act
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    
    # Assert
    assert profit < 0

def test_zero_price_cycle(trade_fees):
    """Тестує випадок, коли одна з цін дорівнює нулю, що має переривати розрахунок."""
    # Arrange
    cycle = Cycle(
        coins=["USDT", "BTC", "ETH", "USDT"],
        steps=[
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    )
    prices = {
        'BTCUSDT': {'a': '0', 'b': '49999'}, # Нульова ціна покупки
        'ETHBTC': {'a': '0.05', 'b': '0.0499'},
        'ETHUSDT': {'a': '2501', 'b': '2500'},
    }
    
    # Act
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    
    # Assert
    assert profit == 0

def test_missing_trade_fee(trade_fees):
    """Тестує, що використовується комісія за замовчуванням, якщо для пари немає комісії."""
    # Arrange
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
        'ETHUSDT': {'a': '2501', 'b': '2550'}, # Прибутковий сценарій
    }
    # Видаляємо комісію для однієї з пар
    del trade_fees['ETHUSDT']
    
    # Act
    profit = cycle.calculate_profit(prices, MOCK_SYMBOLS_INFO, trade_fees)
    
    # Assert
    # Прибуток все ще має бути, оскільки має використовуватись комісія за замовчуванням
    assert profit > 0