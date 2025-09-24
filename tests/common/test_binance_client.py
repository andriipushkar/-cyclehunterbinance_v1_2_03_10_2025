
import pytest
from unittest.mock import patch, MagicMock
from binance.exceptions import BinanceAPIException
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.exceptions import SymbolPriceError
from decimal import Decimal

@patch('cli_monitor.common.binance_client.Client')
def test_binance_client_initialization(MockClient):
    mock_client_instance = MockClient.return_value
    client = BinanceClient()
    MockClient.assert_called_once()
    client.client.ping.assert_called_once()

@patch('cli_monitor.common.binance_client.Client')
def test_get_spot_balance(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_account.return_value = {
        'balances': [
            {'asset': 'BTC', 'free': '1.0'},
            {'asset': 'ETH', 'free': '0.0'}
        ]
    }
    client = BinanceClient()
    balances = client.get_spot_balance()
    assert len(balances) == 1
    assert balances[0]['asset'] == 'BTC'

@patch('cli_monitor.common.binance_client.Client')
def test_get_futures_balance(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.futures_account_balance.return_value = [
        {'asset': 'USDT', 'balance': '1000.0'},
        {'asset': 'BTC', 'balance': '0.0'}
    ]
    client = BinanceClient()
    balances = client.get_futures_balance()
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@patch('cli_monitor.common.binance_client.Client')
def test_get_symbol_price(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_symbol_ticker.return_value = {'price': '50000.0'}
    client = BinanceClient()
    price = client.get_symbol_price('BTC')
    assert price == 50000.0

@patch('cli_monitor.common.binance_client.Client')
def test_get_symbol_price_exception(MockClient):
    mock_client_instance = MockClient.return_value
    mock_response = MagicMock()
    mock_response.text = '{"code": -1121, "msg": "Invalid symbol."}'
    mock_client_instance.get_symbol_ticker.side_effect = BinanceAPIException(mock_response, 400, mock_response.text)
    client = BinanceClient()
    with pytest.raises(SymbolPriceError):
        client.get_symbol_price('BTC')

@patch('cli_monitor.common.binance_client.Client')
def test_get_earn_balance(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_simple_earn_flexible_product_position.return_value = {
        'rows': [{'asset': 'USDT', 'totalAmount': '100.0'}]
    }
    mock_client_instance.get_simple_earn_locked_product_position.return_value = {
        'rows': []
    }
    client = BinanceClient()
    balances = client.get_earn_balance()
    assert len(balances) == 1
    assert balances[0]['asset'] == 'USDT'

@patch('cli_monitor.common.binance_client.Client')
def test_get_trade_fees(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'},
            {'symbol': 'ETHUSDT', 'takerCommission': '0.001'}
        ]
    }
    client = BinanceClient()
    fees = client.get_trade_fees()
    assert len(fees) == 2
    assert fees['BTCUSDT'] == Decimal('0.001')

@patch('cli_monitor.common.binance_client.Client')
def test_get_trade_fee(MockClient):
    mock_client_instance = MockClient.return_value
    mock_client_instance.get_trade_fee.return_value = {
        'tradeFee': [
            {'symbol': 'BTCUSDT', 'takerCommission': '0.001'}
        ]
    }
    client = BinanceClient()
    fee = client.get_trade_fee('BTCUSDT')
    assert fee == Decimal('0.001')
    # Should be cached
    fee = client.get_trade_fee('BTCUSDT')
    mock_client_instance.get_trade_fee.assert_called_once()
