import os
import pytest
import json
from unittest.mock import patch, mock_open, call
from decimal import Decimal

from cli_monitor.arbitrage.backtester import Backtester
from cli_monitor.arbitrage import constants

# Mock data for exchange info
MOCK_EXCHANGE_INFO = {
    'symbols': [
        {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'status': 'TRADING'},
        {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC', 'status': 'TRADING'},
        {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT', 'status': 'TRADING'}
    ]
}

@pytest.mark.asyncio
class TestBacktester:

    @patch('cli_monitor.arbitrage.backtester.structure_cycles_and_get_pairs')
    @patch('cli_monitor.arbitrage.backtester.Backtester._fetch_and_align_historical_data')
    @patch('cli_monitor.arbitrage.backtester.Backtester._load_cycles')
    @patch('cli_monitor.arbitrage.backtester.BinanceClient')
    @patch('builtins.open', new_callable=mock_open)
    async def test_run_finds_profitable_cycle(
        self, mock_file, MockBinanceClient, mock_load_cycles, 
        mock_fetch_data, mock_structure_cycles
    ):
        """Test the main run method to ensure it correctly identifies and logs a profitable cycle."""
        # --- Arrange ---
        start_date = '2023-01-01'
        end_date = '2023-01-02'

        # Mock BinanceClient to control its outputs
        mock_client_instance = MockBinanceClient.return_value
        mock_client_instance.get_exchange_info.return_value = MOCK_EXCHANGE_INFO
        mock_client_instance.get_trade_fees.return_value = {
            'BTCUSDT': Decimal('0.001'),
            'ETHBTC': Decimal('0.001'),
            'ETHUSDT': Decimal('0.001')
        }

        # Mock file system and data loading methods
        mock_load_cycles.return_value = [["USDT", "BTC", "ETH", "USDT"]]
        mock_structure_cycles.return_value = (
            [{ # structured_cycles_data
                'coins': ["USDT", "BTC", "ETH", "USDT"],
                'steps': [
                    {'pair': 'BTCUSDT', 'from': 'USDT', 'to': 'BTC'},
                    {'pair': 'ETHBTC', 'from': 'BTC', 'to': 'ETH'},
                    {'pair': 'ETHUSDT', 'from': 'ETH', 'to': 'USDT'}
                ]
            }],
            {'BTCUSDT', 'ETHBTC', 'ETHUSDT'} # all_pairs
        )

        # Mock historical price data to create a profitable scenario
        mock_fetch_data.return_value = {
            27875520: { # Timestamp: 2023-01-01 00:00:00
                'BTCUSDT': '16500',
                'ETHBTC': '0.07',
                'ETHUSDT': '28000' # This price makes the cycle profitable
            }
        }

        # --- Act ---
        # We instantiate the class *after* setting up the mocks for its dependencies
        backtester = Backtester(start_date, end_date)
        backtester.min_profit_threshold = Decimal('0.5') # Set threshold for predictability
        await backtester.run()

        # --- Assert ---
        log_file_path = os.path.join(constants.LOG_DIR, 'backtest_results.log')
        mock_file.assert_called_with(log_file_path, 'w')

        handle = mock_file()
        written_content = "".join(c[0][0] for c in handle.write.call_args_list)

        assert "SUCCESS!" in written_content
        assert "Cycle: USDT -> BTC -> ETH -> USDT" in written_content
        assert "PROFIT:" in written_content
