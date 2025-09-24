import pytest
from unittest.mock import patch, MagicMock
from cli_monitor.arbitrage.cycle_finder import CycleFinder

@pytest.fixture
def mock_binance_client():
    with patch('cli_monitor.common.binance_client.BinanceClient') as mock_client:
        yield mock_client

@pytest.fixture
def mock_config():
    with patch('cli_monitor.common.config.config') as mock_config:
        mock_config.base_currency = 'USDT'
        mock_config.monitored_coins = ['BTC', 'ETH', 'BNB']
        mock_config.max_cycle_length = 4
        yield mock_config

def test_get_trading_pairs(mock_config, mock_binance_client):
    finder = CycleFinder()
    finder.exchange_info = {
        'symbols': [
            {'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
            {'baseAsset': 'ETH', 'quoteAsset': 'BTC'},
            {'baseAsset': 'BNB', 'quoteAsset': 'USDT'},
        ]
    }
    pairs = finder._get_trading_pairs()
    assert 'USDT' in pairs
    assert 'BTC' in pairs
    assert 'ETH' in pairs
    assert 'BNB' in pairs
    assert 'BTC' in pairs['USDT']
    assert 'USDT' in pairs['BTC']
    assert 'ETH' in pairs['BTC']

def test_find_cycles_dfs(mock_config, mock_binance_client):
    finder = CycleFinder()
    graph = {
        'USDT': ['BTC', 'BNB'],
        'BTC': ['USDT', 'ETH'],
        'ETH': ['BTC'],
        'BNB': ['USDT']
    }
    cycles = finder._find_cycles_dfs(graph, 'USDT', 3)
    assert len(cycles) == 1
    assert cycles[0] == ['USDT', 'BTC', 'ETH', 'USDT']

@patch('builtins.open', new_callable=MagicMock)
def test_save_cycles(mock_open, mock_config, mock_binance_client):
    finder = CycleFinder()
    cycles = [['USDT', 'BTC', 'ETH', 'USDT']]
    finder._save_cycles(cycles)
    mock_open.assert_any_call('configs/possible_cycles.json', 'w')
    mock_open.assert_any_call('configs/possible_cycles.txt', 'w')

@patch('cli_monitor.arbitrage.cycle_finder.CycleFinder._save_cycles')
def test_run(mock_save_cycles, mock_config, mock_binance_client):
    finder = CycleFinder()
    finder.client.get_exchange_info.return_value = {
        'symbols': [
            {'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
            {'baseAsset': 'ETH', 'quoteAsset': 'BTC'},
            {'baseAsset': 'BNB', 'quoteAsset': 'USDT'},
        ]
    }
    finder.run()
    mock_save_cycles.assert_called_once()