"""
Тести для модуля `profit_calculator`.

Ці тести перевіряють логіку розрахунку прибутковості та обробки
повідомлень з WebSocket.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from cli_monitor.arbitrage.profit_calculator import ProfitMonitor
from cli_monitor.arbitrage.cycle import Cycle

@pytest.fixture
def mock_binance_client():
    """Фікстура для мокування `BinanceClient`."""
    with patch('cli_monitor.common.binance_client.BinanceClient') as mock_client:
        yield mock_client

@pytest.fixture
def mock_config():
    """Фікстура для мокування об'єкта конфігурації."""
    with patch('cli_monitor.common.config.config') as mock_config:
        mock_config.min_profit_threshold = '0.1'
        yield mock_config

@pytest.fixture
def profit_monitor(mock_config, mock_binance_client):
    """Фікстура, що створює екземпляр `ProfitMonitor` з моками."""
    # Мокуємо завантаження цін з файлу, щоб ізолювати тест
    with patch('cli_monitor.arbitrage.profit_calculator.ProfitMonitor._load_latest_prices') as mock_load_prices:
        pm = ProfitMonitor()
        mock_load_prices.assert_called_once() # Переконуємось, що метод викликався
        yield pm

@pytest.mark.asyncio
async def test_calculate_and_log_profit_positive(profit_monitor):
    """Тестує випадок, коли знайдено прибутковий цикл."""
    # Arrange
    cycle = Cycle(['USDT', 'BTC', 'USDT'], [{'pair': 'BTCUSDT', 'from': 'USDT', 'to': 'BTC'}, {'pair': 'BTCUSDT', 'from': 'BTC', 'to': 'USDT'}])
    symbols_info = {'BTCUSDT': {'symbol': 'BTCUSDT'}}
    trade_fees = {'BTCUSDT': Decimal('0.001')}
    min_profit_threshold = Decimal('0.1')
    profit_monitor.latest_prices = {'BTCUSDT': {'b': '10000', 'a': '10001'}}
    
    # Мокуємо метод розрахунку прибутку, щоб повернути позитивне значення
    with patch.object(cycle, 'calculate_profit', return_value=Decimal('0.2')) as mock_calculate_profit, \
         patch.object(profit_monitor, '_log_profitable_opportunity') as mock_log_profitable_opportunity:
        
        # Act
        await profit_monitor.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)
        
        # Assert
        mock_calculate_profit.assert_called_once_with(profit_monitor.latest_prices, symbols_info, trade_fees)
        # Перевіряємо, що функція логування була викликана, оскільки прибуток > порогу
        mock_log_profitable_opportunity.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_and_log_profit_negative(profit_monitor):
    """Тестує випадок, коли цикл є збитковим."""
    # Arrange
    cycle = Cycle(['USDT', 'BTC', 'USDT'], [{'pair': 'BTCUSDT', 'from': 'USDT', 'to': 'BTC'}, {'pair': 'BTCUSDT', 'from': 'BTC', 'to': 'USDT'}])
    symbols_info = {'BTCUSDT': {'symbol': 'BTCUSDT'}}
    trade_fees = {'BTCUSDT': Decimal('0.001')}
    min_profit_threshold = Decimal('0.1')
    profit_monitor.latest_prices = {'BTCUSDT': {'b': '10000', 'a': '10001'}}
    
    # Мокуємо метод розрахунку прибутку, щоб повернути негативне значення
    with patch.object(cycle, 'calculate_profit', return_value=Decimal('-0.1')) as mock_calculate_profit, \
         patch.object(profit_monitor, '_log_profitable_opportunity') as mock_log_profitable_opportunity:
        
        # Act
        await profit_monitor.calculate_and_log_profit(cycle, symbols_info, trade_fees, min_profit_threshold)
        
        # Assert
        mock_calculate_profit.assert_called_once_with(profit_monitor.latest_prices, symbols_info, trade_fees)
        # Перевіряємо, що функція логування НЕ була викликана
        mock_log_profitable_opportunity.assert_not_called()

@pytest.mark.asyncio
async def test_handle_websocket_message(profit_monitor):
    """Тестує обробник повідомлень WebSocket."""
    # Arrange
    message = '{"data": {"s": "BTCUSDT", "b": "10000", "a": "10001"}}'
    symbols_info = {}
    trade_fees = {}
    min_profit_threshold = Decimal('0.1')
    # Мокуємо цикли, що залежать від цієї пари
    profit_monitor.pair_to_cycles = {'BTCUSDT': [MagicMock()]}
    
    # Мокуємо асинхронний метод `calculate_and_log_profit`
    with patch.object(profit_monitor, 'calculate_and_log_profit', new_callable=AsyncMock) as mock_calculate_and_log_profit:
        # Act
        await profit_monitor._handle_websocket_message(message, symbols_info, trade_fees, min_profit_threshold)
        
        # Assert
        # Перевіряємо, що ціна оновилася
        assert 'BTCUSDT' in profit_monitor.latest_prices
        # Перевіряємо, що був викликаний розрахунок прибутку для залежного циклу
        mock_calculate_and_log_profit.assert_called_once()