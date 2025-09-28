"""
Тести для модуля `common.binance_client`.

Ці тести перевіряють, що `BinanceClient` правильно викликає методи
бібліотеки `python-binance`, обробляє відповіді та власні винятки.
"""

import pytest
from unittest.mock import patch, MagicMock
from binance.exceptions import BinanceAPIException
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.exceptions import SymbolPriceError
from decimal import Decimal

@patch('cli_monitor.common.binance_client.Client')
def test_binance_client_initialization(MockClient):
    """Тестує, що при ініціалізації клієнта викликається `ping`."""
    # Arrange
    mock_client_instance = MockClient.return_value
    
    # Act
    client = BinanceClient()
    
    # Assert
    MockClient.assert_called_once() # Перевіряємо, що екземпляр `binance.Client` був створений
    client.client.ping.assert_called_once() # Перевіряємо, що був зроблений `ping`

@patch('cli_monitor.common.binance_client.Client')
def test_get_spot_balance(MockClient):
    """Тестує отримання та фільтрацію спотового балансу."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_account.return_value = {
        'balances': [
            {'asset': 'BTC', 'free': '1.0'}, # Повинен залишитись
            {'asset': 'ETH', 'free': '0.0'}  # Повинен бути відфільтрований
        ]
    }
    
    # Act
    client = BinanceClient()
    balances = client.get_spot_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'BTC'

@patch('cli_monitor.common.binance_client.Client')
def test_get_futures_balance(MockClient):
    """Тестує отримання та фільтрацію ф'ючерсного балансу."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.futures_account_balance.return_value = [
        {'asset': 'USDT', 'balance': '1000.0'},
        {'asset': 'BTC', 'balance': '0.0'}
    ]
    
    # Act
    client = BinanceClient()
    balances = client.get_futures_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@patch('cli_monitor.common.binance_client.Client')
def test_get_symbol_price(MockClient):
    """Тестує отримання ціни для символу."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_symbol_ticker.return_value = {'price': '50000.0'}
    
    # Act
    client = BinanceClient()
    price = client.get_symbol_price('BTC')
    
    # Assert
    assert price == 50000.0

@patch('cli_monitor.common.binance_client.Client')
def test_get_symbol_price_exception(MockClient):
    """Тестує, що при помилці API генерується виняток `SymbolPriceError`."""
    # Arrange
    mock_client_instance = MockClient.return_value
    # Імітуємо помилку API
    mock_response = MagicMock()
    mock_response.text = '{"code": -1121, "msg": "Invalid symbol."}'
    mock_client_instance.get_symbol_ticker.side_effect = BinanceAPIException(mock_response, 400, mock_response.text)
    
    # Act & Assert
    client = BinanceClient()
    with pytest.raises(SymbolPriceError):
        client.get_symbol_price('INVALID_SYMBOL')

@patch('cli_monitor.common.binance_client.Client')
def test_get_earn_balance(MockClient):
    """Тестує отримання балансу з гаманця Earn."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_simple_earn_flexible_product_position.return_value = {
        'rows': [{'asset': 'USDT', 'totalAmount': '100.0'}]
    }
    mock_client_instance.get_simple_earn_locked_product_position.return_value = {
        'rows': []
    }
    
    # Act
    client = BinanceClient()
    balances = client.get_earn_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@patch('cli_monitor.common.binance_client.Client')
def test_get_trade_fees(MockClient):
    """Тестує отримання та кешування торгових комісій."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'},
            {'symbol': 'ETHUSDT', 'takerCommission': '0.001'}
        ]
    }
    
    # Act
    client = BinanceClient()
    fees = client.get_trade_fees()
    
    # Assert
    assert len(fees) == 2
    assert fees['BTCUSDT'] == Decimal('0.001')

@patch('cli_monitor.common.binance_client.Client')
def test_get_trade_fee(MockClient):
    """Тестує отримання комісії для однієї пари та її кешування."""
    # Arrange
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'}
        ]
    }
    
    # Act
    client = BinanceClient()
    fee = client.get_trade_fee('BTCUSDT')
    
    # Assert
    assert fee == Decimal('0.001')
    
    # Act again to check caching
    fee = client.get_trade_fee('BTCUSDT')
    
    # Assert: метод `get_trade_fee` з `python-binance` мав бути викликаний лише один раз
    mock_client_instance.get_trade_fee.assert_called_once()