
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from cli_monitor.arbitrage.profit_calculator import ProfitCalculator
from cli_monitor.arbitrage.cycle import Cycle

@pytest.fixture
def mock_binance_client():
    with patch('cli_monitor.common.binance_client.BinanceClient') as mock_client:
        yield mock_client

@pytest.fixture
def mock_config():
    with patch('cli_monitor.common.config.config') as mock_config:
        mock_config.min_profit_threshold = '0.1'
        yield mock_config

@pytest.fixture
def profit_calculator(mock_config, mock_binance_client):
    return ProfitCalculator()

@pytest.mark.asyncio
async def test_calculate_and_log_profit_positive(profit_calculator):
    cycle = Cycle(['USDT', 'BTC', 'USDT'], [{'pair': 'BTCUSDT', 'from': 'USDT', 'to': 'BTC'}, {'pair': 'BTCUSDT', 'from': 'BTC', 'to': 'USDT'}])
    symbols_info = {'BTCUSDT': {'symbol': 'BTCUSDT'}}
    trade_fees = {'BTCUSDT': Decimal('0.001')}
    min_profit_threshold = Decimal('0.1')
    profit_calculator.latest_prices = {'BTCUSDT': {'b': '10000', 'a': '10001'}}
    
    with patch.object(cycle, 'calculate_profit', return_value=Decimal('0.2')) as mock_calculate_profit,
         patch.object(profit_calculator, '_log_profitable_opportunity') as mock_log_profitable_opportunity:
        
        await profit_calculator.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)
        
        mock_calculate_profit.assert_called_once_with(profit_calculator.latest_prices, symbols_info, trade_fees)
        mock_log_profitable_opportunity.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_and_log_profit_negative(profit_calculator):
    cycle = Cycle(['USDT', 'BTC', 'USDT'], [{'pair': 'BTCUSDT', 'from': 'USDT', 'to': 'BTC'}, {'pair': 'BTCUSDT', 'from': 'BTC', 'to': 'USDT'}])
    symbols_info = {'BTCUSDT': {'symbol': 'BTCUSDT'}}
    trade_fees = {'BTCUSDT': Decimal('0.001')}
    min_profit_threshold = Decimal('0.1')
    profit_calculator.latest_prices = {'BTCUSDT': {'b': '10000', 'a': '10001'}}
    
    with patch.object(cycle, 'calculate_profit', return_value=Decimal('-0.1')) as mock_calculate_profit,
         patch.object(profit_calculator, '_log_profitable_opportunity') as mock_log_profitable_opportunity:
        
        await profit_calculator.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)
        
        mock_calculate_profit.assert_called_once_with(profit_calculator.latest_prices, symbols_info, trade_fees)
        mock_log_profitable_opportunity.assert_not_called()

@pytest.mark.asyncio
async def test_handle_websocket_message(profit_calculator):
    message = '{"data": {"s": "BTCUSDT", "b": "10000", "a": "10001"}}'
    symbols_info = {}
    trade_fees = {}
    min_profit_threshold = Decimal('0.1')
    profit_calculator.pair_to_cycles = {'BTCUSDT': [MagicMock()]}
    
    with patch.object(profit_calculator, 'calculate_and_log_profit', new_callable=AsyncMock) as mock_calculate_and_log_profit:
        await profit_calculator._handle_websocket_message(message, symbols_info, trade_fees, min_profit_threshold)
        
        assert 'BTCUSDT' in profit_calculator.latest_prices
        mock_calculate_and_log_profit.assert_called_once()
