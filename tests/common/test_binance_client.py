"""
Тести для модуля `common.binance_client`.

Ці тести перевіряють, що `BinanceClient` правильно викликає методи
бібліотеки `python-binance`, обробляє відповіді та власні винятки.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from binance.exceptions import BinanceAPIException
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.exceptions import SymbolPriceError
from decimal import Decimal

@pytest_asyncio.fixture
async def client(mocker):
    mocker.patch('binance.AsyncClient.create', return_value=AsyncMock())
    client = await BinanceClient.create()
    yield client
    await client.close_connection()

@pytest.mark.asyncio
async def test_binance_client_initialization(client):
    """Тестує, що при ініціалізації клієнта викликається `ping`."""
    client.client.ping.assert_called_once()

@pytest.mark.asyncio
async def test_get_spot_balance(client):
    """Тестує отримання та фільтрацію спотового балансу."""
    # Arrange
    client.client.get_account.return_value = {
        'balances': [
            {'asset': 'BTC', 'free': '1.0'},
            {'asset': 'ETH', 'free': '0.0'}
        ]
    }
    
    # Act
    balances = await client.get_spot_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'BTC'

@pytest.mark.asyncio
async def test_get_futures_balance(client):
    """Тестує отримання та фільтрацію ф'ючерсного балансу."""
    # Arrange
    client.client.futures_account_balance.return_value = [
        {'asset': 'USDT', 'balance': '1000.0'},
        {'asset': 'BTC', 'balance': '0.0'}
    ]
    
    # Act
    balances = await client.get_futures_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@pytest.mark.asyncio
async def test_get_symbol_price(client):
    """Тестує отримання ціни для символу."""
    # Arrange
    client.client.get_symbol_ticker.return_value = {'price': '50000.0'}
    
    # Act
    price = await client.get_symbol_price('BTC')
    
    # Assert
    assert price == 50000.0

@pytest.mark.asyncio
async def test_get_symbol_price_exception(client):
    """Тестує, що при помилці API генерується виняток `SymbolPriceError`."""
    # Arrange
    mock_response = AsyncMock()
    mock_response.text = '{"code": -1121, "msg": "Invalid symbol."}'
    client.client.get_symbol_ticker.side_effect = BinanceAPIException(mock_response, 400, mock_response.text)
    
    # Act & Assert
    with pytest.raises(SymbolPriceError):
        await client.get_symbol_price('INVALID_SYMBOL')

@pytest.mark.asyncio
async def test_get_earn_balance(client):
    """Тестує отримання балансу з гаманця Earn."""
    # Arrange
    client.client.get_simple_earn_flexible_product_position.return_value = {
        'rows': [{'asset': 'USDT', 'totalAmount': '100.0'}]
    }
    client.client.get_simple_earn_locked_product_position.return_value = {
        'rows': []
    }
    
    # Act
    balances = await client.get_earn_balance()
    
    # Assert
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@pytest.mark.asyncio
async def test_get_trade_fees(client):
    """Тестує отримання та кешування торгових комісій."""
    # Arrange
    client.client.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'},
            {'symbol': 'ETHUSDT', 'takerCommission': '0.001'}
        ]
    }
    
    # Act
    fees = await client.get_trade_fees()
    
    # Assert
    assert len(fees) == 2
    assert fees['BTCUSDT'] == Decimal('0.001')

@pytest.mark.asyncio
async def test_get_trade_fee(client):
    """Тестує отримання комісії для однієї пари та її кешування."""
    # Arrange
    client.client.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'}
        ]
    }
    
    # Act
    fee = await client.get_trade_fee('BTCUSDT')
    
    # Assert
    assert fee == Decimal('0.001')
    
    # Act again to check caching
    fee = await client.get_trade_fee('BTCUSDT')
    
    # Assert: метод `get_trade_fee` з `python-binance` мав бути викликаний лише один раз
    client.client.get_trade_fee.assert_called_once()