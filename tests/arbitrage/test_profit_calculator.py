import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, mock_open
from decimal import Decimal
from cli_monitor.arbitrage.profit_calculator import (
    get_exchange_info_map,
    load_cycles_and_map_pairs,
    calculate_and_log_profit,
    latest_prices,
    pair_to_cycles,
    latest_profits_by_cycle
)
from cli_monitor.arbitrage import constants

MOCK_SYMBOLS_INFO = {
    'BTCUSDT': {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
    'ETHUSDT': {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT'},
    'ETHBTC': {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC'},
}

MOCK_CYCLES_COINS = [
    ["USDT", "BTC", "ETH", "USDT"]
]

@pytest.fixture(autouse=True)
def clear_globals():
    """Clears global dictionaries before each test."""
    latest_prices.clear()
    pair_to_cycles.clear()
    latest_profits_by_cycle.clear()

@patch('cli_monitor.arbitrage.profit_calculator.BinanceClient')
def test_get_exchange_info_map(MockBinanceClient):
    mock_client = MockBinanceClient.return_value
    mock_client.get_exchange_info.return_value = {'symbols': [{'symbol': 'BTCUSDT'}]}
    
    result = get_exchange_info_map()
    
    assert 'BTCUSDT' in result
    assert result['BTCUSDT']['symbol'] == 'BTCUSDT'

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data=json.dumps(MOCK_CYCLES_COINS))
def test_load_cycles_and_map_pairs(mock_file, mock_exists):
    structured_cycles, all_trade_pairs = load_cycles_and_map_pairs(MOCK_SYMBOLS_INFO)
    
    assert len(structured_cycles) == 1
    assert "USDT -> BTC -> ETH -> USDT" in [ ' -> '.join(c['coins']) for c in structured_cycles]
    assert all_trade_pairs == {'BTCUSDT', 'ETHBTC', 'ETHUSDT'}
    assert 'BTCUSDT' in pair_to_cycles
    assert 'ETHBTC' in pair_to_cycles
    assert 'ETHUSDT' in pair_to_cycles

@pytest.mark.asyncio
@patch('builtins.open', new_callable=mock_open)
async def test_calculate_and_log_profit(mock_file):
    cycle_info = {
        "coins": ["USDT", "BTC", "ETH", "USDT"],
        "steps": [
            {"pair": "BTCUSDT", "from": "USDT", "to": "BTC"},
            {"pair": "ETHBTC", "from": "BTC", "to": "ETH"},
            {"pair": "ETHUSDT", "from": "ETH", "to": "USDT"}
        ]
    }
    
    latest_prices['BTCUSDT'] = {'b': '50000', 'a': '50001'}
    latest_prices['ETHBTC'] = {'b': '0.05', 'a': '0.0505'}
    latest_prices['ETHUSDT'] = {'b': '2550', 'a': '2551'}
    
    trading_fee = Decimal('0.001')
    min_profit_threshold = Decimal('0.0')
    
    await calculate_and_log_profit(cycle_info, MOCK_SYMBOLS_INFO, trading_fee, min_profit_threshold)
    
    cycle_str = ' -> '.join(cycle_info['coins'])
    assert cycle_str in latest_profits_by_cycle
    assert latest_profits_by_cycle[cycle_str] > 0
