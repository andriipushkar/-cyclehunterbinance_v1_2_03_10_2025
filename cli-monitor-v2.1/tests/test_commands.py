import sys
import os
from unittest.mock import patch, MagicMock, call
import time

# Add the src and cli-monitor-v2.1 directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from commands import get_balances, monitor_balances

@patch('commands.BinanceClient')
def test_get_balances(mock_binance_client):
    """
    Tests the get_balances function with mocked BinanceClient.
    """
    # Create a mock instance of the BinanceClient
    mock_client_instance = MagicMock()
    mock_binance_client.return_value = mock_client_instance

    # Mock the return values of the BinanceClient methods
    mock_client_instance.get_spot_balance.return_value = [
        {'asset': 'BTC', 'total': '0.5'},
        {'asset': 'ETH', 'total': '10'},
    ]
    mock_client_instance.get_futures_balance.return_value = [
        {'asset': 'USDT', 'balance': '1000'},
    ]
    mock_client_instance.get_earn_balance.return_value = [
        {'asset': 'BNB', 'total': '5'},
    ]
    mock_client_instance.get_symbol_price.side_effect = lambda asset: {
        'BTC': 50000,
        'ETH': 3000,
        'USDT': 1,
        'BNB': 400,
    }.get(asset)

    # Call the function to be tested
    get_balances()

    # Assert that the output is as expected
    # For now, we will just check if the function runs without errors
    # and if the mocked methods were called.
    mock_client_instance.get_spot_balance.assert_called_once()
    mock_client_instance.get_futures_balance.assert_called_once()
    mock_client_instance.get_earn_balance.assert_called_once()

class StopTest(Exception):
    pass

@patch('commands.time.sleep')
@patch('commands._get_and_save_balances')
def test_monitor_balances(mock_get_and_save, mock_sleep):
    """
    Tests the monitor_balances function.
    """
    mock_get_and_save.side_effect = [None, StopTest]
    try:
        monitor_balances()
    except StopTest:
        pass

    assert mock_get_and_save.call_count == 2
    mock_sleep.assert_called_once_with(60)

@patch('commands.BinanceClient')
def test_get_balances_with_none_price(mock_binance_client):
    """
    Tests the get_balances function when get_symbol_price returns None.
    """
    mock_client_instance = MagicMock()
    mock_binance_client.return_value = mock_client_instance

    mock_client_instance.get_spot_balance.return_value = [
        {'asset': 'UNKNOWN', 'total': '100'},
    ]
    mock_client_instance.get_futures_balance.return_value = []
    mock_client_instance.get_earn_balance.return_value = []
    mock_client_instance.get_symbol_price.return_value = None

    get_balances()

    mock_client_instance.get_spot_balance.assert_called_once()
    mock_client_instance.get_futures_balance.assert_called_once()
    mock_client_instance.get_earn_balance.assert_called_once()
