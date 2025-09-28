"""
Тести для модуля `cycle_finder`.

Ці тести перевіряють коректність роботи основних функцій `CycleFinder`,
таких як побудова графа торгових пар, пошук циклів та збереження результатів.
Використовується `pytest` та `unittest.mock` для ізоляції залежностей.
"""

import pytest
from unittest.mock import patch, MagicMock
from cli_monitor.arbitrage.cycle_finder import CycleFinder

@pytest.fixture
def mock_binance_client():
    """Фікстура для мокування `BinanceClient`."""
    # `patch` замінює об'єкт на мок (MagicMock)
    with patch('cli_monitor.common.binance_client.BinanceClient') as mock_client:
        yield mock_client

@pytest.fixture
def mock_config():
    """Фікстура для мокування об'єкта конфігурації."""
    with patch('cli_monitor.common.config.config') as mock_config:
        # Встановлюємо тестові значення для конфігурації
        mock_config.base_currency = 'USDT'
        mock_config.monitored_coins = ['BTC', 'ETH', 'BNB']
        mock_config.max_cycle_length = 4
        yield mock_config

def test_get_trading_pairs(mock_config, mock_binance_client):
    """Тестує правильність побудови графа торгових пар."""
    # Arrange: Створюємо екземпляр та мокуємо вхідні дані
    finder = CycleFinder()
    finder.exchange_info = {
        'symbols': [
            {'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'status': 'TRADING'},
            {'baseAsset': 'ETH', 'quoteAsset': 'BTC', 'status': 'TRADING'},
            {'baseAsset': 'BNB', 'quoteAsset': 'USDT', 'status': 'TRADING'},
        ]
    }
    
    # Act: Викликаємо тестовану функцію
    pairs = finder._get_trading_pairs()
    
    # Assert: Перевіряємо результат
    assert 'USDT' in pairs
    assert 'BTC' in pairs
    assert 'ETH' in pairs
    assert 'BNB' in pairs
    assert 'BTC' in pairs['USDT']
    assert 'USDT' in pairs['BTC']
    assert 'ETH' in pairs['BTC']

def test_find_cycles_dfs(mock_config, mock_binance_client):
    """Тестує алгоритм пошуку циклів (DFS)."""
    # Arrange
    finder = CycleFinder()
    graph = {
        'USDT': ['BTC', 'BNB'],
        'BTC': ['USDT', 'ETH'],
        'ETH': ['BTC'],
        'BNB': ['USDT']
    }
    
    # Act
    cycles = finder._find_cycles_dfs(graph, 'USDT', 3)
    
    # Assert
    assert len(cycles) == 2
    # Перевіряємо, що знайдені цикли відповідають очікуваним
    assert ['USDT', 'BTC', 'USDT'] in cycles
    assert ['USDT', 'BNB', 'USDT'] in cycles

@patch('builtins.open', new_callable=MagicMock)
def test_save_cycles(mock_open, mock_config, mock_binance_client):
    """Тестує функцію збереження циклів у файли."""
    # Arrange
    import os
    finder = CycleFinder()
    cycles = [['USDT', 'BTC', 'ETH', 'USDT']]
    
    # Act
    finder._save_cycles(cycles)
    
    # Assert
    # Перевіряємо, що були зроблені виклики для відкриття JSON та TXT файлів
    json_path = os.path.abspath('configs/possible_cycles.json')
    txt_path = os.path.abspath('configs/possible_cycles.txt')
    mock_open.assert_any_call(json_path, 'w')
    mock_open.assert_any_call(txt_path, 'w')

@patch('cli_monitor.arbitrage.cycle_finder.CycleFinder._save_cycles')
def test_run(mock_save_cycles, mock_config, mock_binance_client):
    """Тестує головний метод `run`."""
    # Arrange
    finder = CycleFinder()
    # Мокуємо відповідь від API
    mock_binance_client.return_value.get_exchange_info.return_value = {
        'symbols': [
            {'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'status': 'TRADING'},
            {'baseAsset': 'ETH', 'quoteAsset': 'BTC', 'status': 'TRADING'},
            {'baseAsset': 'BNB', 'quoteAsset': 'USDT', 'status': 'TRADING'},
        ]
    }
    
    # Act
    finder.run()
    
    # Assert
    # Перевіряємо, що метод збереження циклів був викликаний
    mock_save_cycles.assert_called_once()
