"""
Тести для модуля `balance.commands`.

Ці тести перевіряють основні функції моніторингу балансу, такі як
отримання, форматування та збереження даних про баланси.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from cli_monitor.balance.commands import BalanceMonitor
from cli_monitor.common import utils

# Використовуємо декоратор `patch` для мокування залежностей на рівні всього класу або функції
@patch('cli_monitor.balance.commands.BinanceClient')
@patch('cli_monitor.balance.commands.save_to_json')
@patch('cli_monitor.balance.commands.format_balances')
@patch('builtins.open')
def test_get_balances(mock_open, mock_format_balances, mock_save_to_json, mock_binance_client_class):
    """Тестує функцію `get_balances`, перевіряючи виклики всіх залежностей."""
    # Arrange
    # Налаштовуємо мок-об'єкти, щоб вони повертали тестові дані
    mock_instance = mock_binance_client_class.return_value
    mock_instance.get_spot_balance.return_value = [{'asset': 'BTC', 'total': '1.0'}]
    mock_instance.get_futures_balance.return_value = [{'asset': 'ETH', 'balance': '10.0'}]
    mock_instance.get_earn_balance.return_value = [{'asset': 'BNB', 'total': '100.0'}]
    mock_instance.get_symbol_price.return_value = 50000.0

    # Act
    monitor = BalanceMonitor()
    monitor.get_balances()

    # Assert
    # Перевіряємо, що методи для отримання балансів були викликані
    mock_instance.get_spot_balance.assert_called_once()
    mock_instance.get_futures_balance.assert_called_once()
    mock_instance.get_earn_balance.assert_called_once()
    
    # Перевіряємо, що функція збереження в JSON була викликана з правильними аргументами
    mock_save_to_json.assert_called_once()
    args, kwargs = mock_save_to_json.call_args
    assert 'balances' in args[0]
    assert args[1] == 'output/balance_output.json'

    # Перевіряємо, що функція форматування була викликана
    mock_format_balances.assert_called_once()
    args, kwargs = mock_format_balances.call_args
    assert 'spot' in args[0]

    # Перевіряємо, що був відкритий файл для запису текстового звіту
    mock_open.assert_called_with('output/balance_output.txt', 'w')

@patch('cli_monitor.balance.commands.BalanceMonitor._get_and_save_balances')
@patch('time.sleep')
def test_monitor_balances(mock_sleep, mock_get_and_save):
    """Тестує функцію `monitor_balances`, зокрема її коректну зупинку."""
    # Arrange
    # Імітуємо, що при першому ж виклику `_get_and_save_balances` користувач натискає Ctrl+C
    mock_get_and_save.side_effect = KeyboardInterrupt
    
    # Act
    monitor = BalanceMonitor()
    monitor.monitor_balances()
    
    # Assert
    # Переконуємось, що функція отримання балансів була викликана хоча б один раз
    mock_get_and_save.assert_called_once()

def test_format_balances():
    """Тестує допоміжну функцію `format_balances`."""
    # Arrange
    balances_data = {
        "spot": [{'asset': 'BTC', 'total': '1.0'}],
        "futures": [{'asset': 'ETH', 'balance': '10.0'}],
        "earn": [{'asset': 'BNB', 'total': '100.0'}],
        "total_spot_balance_usd": 50000.0,
        "total_futures_balance_usd": 500000.0,
        "total_earn_balance_usd": 5000000.0,
        "total_balance_usd": 5550000.0
    }
    
    # Act
    formatted_string = utils.format_balances(balances_data)
    
    # Assert
    # Перевіряємо, що ключові дані присутні у відформатованому рядку
    assert "Загальний баланс: $5550000.00" in formatted_string
    assert "BTC: 1.0" in formatted_string
    assert "ETH: 10.0" in formatted_string
    assert "BNB: 100.0" in formatted_string