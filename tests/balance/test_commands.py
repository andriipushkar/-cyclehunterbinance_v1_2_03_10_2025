import pytest
from unittest.mock import patch, MagicMock, call
from cli_monitor.balance import commands
from cli_monitor.common import utils

@patch('cli_monitor.balance.commands.BinanceClient')
@patch('cli_monitor.balance.commands.save_to_json')
@patch('cli_monitor.balance.commands.format_balances')
@patch('builtins.open')
def test_get_balances(mock_open, mock_format_balances, mock_save_to_json, mock_binance_client_class):
    """Test get_balances function with more detailed checks."""
    mock_instance = mock_binance_client_class.return_value
    mock_instance.get_spot_balance.return_value = [{'asset': 'BTC', 'total': '1.0'}]
    mock_instance.get_futures_balance.return_value = [{'asset': 'ETH', 'balance': '10.0'}]
    mock_instance.get_earn_balance.return_value = [{'asset': 'BNB', 'total': '100.0'}]
    mock_instance.get_symbol_price.return_value = 50000.0

    commands.get_balances()

    mock_instance.get_spot_balance.assert_called_once()
    mock_instance.get_futures_balance.assert_called_once()
    mock_instance.get_earn_balance.assert_called_once()
    
    # Check the arguments passed to save_to_json
    mock_save_to_json.assert_called_once()
    args, kwargs = mock_save_to_json.call_args
    assert 'balances' in args[0]
    assert args[1] == 'output/balance_output.json'

    # Check the arguments passed to format_balances
    mock_format_balances.assert_called_once()
    args, kwargs = mock_format_balances.call_args
    assert 'spot' in args[0]

    mock_open.assert_called_with('output/balance_output.txt', 'w')

@patch('cli_monitor.balance.commands._get_and_save_balances')
@patch('time.sleep')
def test_monitor_balances(mock_sleep, mock_get_and_save):
    """Test monitor_balances function."""
    mock_get_and_save.side_effect = KeyboardInterrupt
    commands.monitor_balances()
    mock_get_and_save.assert_called_once()

def test_format_balances():
    """Test the format_balances utility function."""
    balances_data = {
        "spot": [{'asset': 'BTC', 'total': '1.0'}],
        "futures": [{'asset': 'ETH', 'balance': '10.0'}],
        "earn": [{'asset': 'BNB', 'total': '100.0'}],
        "total_spot_balance_usd": 50000.0,
        "total_futures_balance_usd": 500000.0,
        "total_earn_balance_usd": 5000000.0,
        "total_balance_usd": 5550000.0
    }
    formatted_string = utils.format_balances(balances_data)
    assert "Total Balance: $5550000.00" in formatted_string
    assert "BTC: 1.0" in formatted_string
    assert "ETH: 10.0" in formatted_string
    assert "BNB: 100.0" in formatted_string