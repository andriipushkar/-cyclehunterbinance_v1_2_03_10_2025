import os
import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from decimal import Decimal
from cli_monitor.arbitrage.backtester import (
    load_config_and_cycles,
    get_historical_klines,
    run_backtest,
    BACKTEST_LOG_FILE
)


@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open)
def test_load_config_and_cycles(mock_file, mock_exists):
    mock_file.side_effect = [
        mock_open(read_data=json.dumps({'trading_fee': '0.001', 'min_profit_threshold': '0.0'})).return_value,
        mock_open(read_data=json.dumps([["USDT", "BTC", "ETH", "USDT"]])).return_value
    ]
    config, cycles, trading_fee, min_profit_threshold = load_config_and_cycles()
    assert config['trading_fee'] == '0.001'
    assert cycles[0][0] == "USDT"
    assert trading_fee == Decimal('0.001')
    assert min_profit_threshold == Decimal('0.0')


@patch('cli_monitor.arbitrage.backtester.BinanceClient')
def test_get_historical_klines(MockBinanceClient):
    mock_client = MockBinanceClient.return_value
    mock_client.client.get_historical_klines.return_value = [1, 2, 3]
    klines = get_historical_klines(mock_client, 'BTCUSDT', '2023-01-01', '2023-01-02')
    assert klines == [1, 2, 3]


@pytest.mark.asyncio
@patch('cli_monitor.arbitrage.backtester.load_config_and_cycles')
@patch('cli_monitor.arbitrage.backtester.BinanceClient')
@patch('cli_monitor.arbitrage.backtester.get_historical_klines')
@patch('builtins.open', new_callable=mock_open)
async def test_run_backtest(mock_open, mock_get_historical_klines, MockBinanceClient, mock_load_config_and_cycles):
    mock_load_config_and_cycles.return_value = (
        {'trading_fee': '0.001', 'min_profit_threshold': '0.0'}, 
        [["USDT", "BTC", "ETH", "USDT"]], 
        Decimal('0.001'), 
        Decimal('0.0')
    )
    mock_client = MockBinanceClient.return_value
    mock_client.get_exchange_info.return_value = {
        'symbols': [
            {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
            {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT'},
            {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC'}
        ]
    }
    mock_get_historical_klines.return_value = [
        [1672531200000, '50000', '50000', '50000', '50000'],
    ]
    
    await run_backtest('2023-01-01', '2023-01-02')
    called_path = mock_open.call_args[0][0]
    assert os.path.basename(called_path) == os.path.basename(BACKTEST_LOG_FILE)
    assert os.path.dirname(os.path.abspath(called_path)) == os.path.dirname(os.path.abspath(BACKTEST_LOG_FILE))
