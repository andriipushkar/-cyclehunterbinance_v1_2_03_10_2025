import os
import json
import unittest
from unittest.mock import patch, MagicMock
from cli_monitor.arbitrage.cycle_finder import find_arbitrage_cycles, CONFIG_DIR, POSSIBLE_CYCLES_JSON_FILE, POSSIBLE_CYCLES_TXT_FILE

# Mock data similar to Binance API response
MOCK_EXCHANGE_INFO = {
    'symbols': [
        {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
        {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT'},
        {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC'}, # Cycle: USDT -> BTC -> ETH -> USDT
    ]
}

MOCK_EXCHANGE_INFO_NO_CYCLES = {
    'symbols': [
        {'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
        {'symbol': 'ETHUSDT', 'baseAsset': 'ETH', 'quoteAsset': 'USDT'},
    ]
}

class TestCycleFinder(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        # Create dummy config files
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(os.path.join(CONFIG_DIR, 'config.json'), 'w') as f:
            json.dump({
                "base_currency": "USDT",
                "monitored_coins": ["BTC", "ETH"],
                "max_cycle_length": 3
            }, f)
        
        self._cleanup_output_files()

    def tearDown(self):
        """Clean up after tests."""
        self._cleanup_output_files()
        os.remove(os.path.join(CONFIG_DIR, 'config.json'))
        if not os.listdir(CONFIG_DIR):
            os.rmdir(CONFIG_DIR)

    def _cleanup_output_files(self):
        if os.path.exists(POSSIBLE_CYCLES_JSON_FILE):
            os.remove(POSSIBLE_CYCLES_JSON_FILE)
        if os.path.exists(POSSIBLE_CYCLES_TXT_FILE):
            os.remove(POSSIBLE_CYCLES_TXT_FILE)

    @patch('cli_monitor.arbitrage.cycle_finder.BinanceClient')
    def test_find_arbitrage_cycles(self, MockBinanceClient):
        """Test that cycles are found and files are created correctly."""
        # Mock the Binance client and its method
        mock_client_instance = MockBinanceClient.return_value
        mock_client_instance.get_exchange_info.return_value = MOCK_EXCHANGE_INFO

        # Run the function
        find_arbitrage_cycles()

        # 1. Check if JSON file was created and has correct content
        self.assertTrue(os.path.exists(POSSIBLE_CYCLES_JSON_FILE))
        with open(POSSIBLE_CYCLES_JSON_FILE, 'r') as f:
            cycles_data = json.load(f)
        
        expected_cycles = [
            ["USDT", "BTC", "ETH", "USDT"],
            ["USDT", "ETH", "BTC", "USDT"],
        ]
        
        # Convert to tuple of tuples for unordered comparison
        self.assertEqual(set(map(tuple, cycles_data)), set(map(tuple, expected_cycles)))

        # 2. Check if TXT file was created and has correct content
        self.assertTrue(os.path.exists(POSSIBLE_CYCLES_TXT_FILE))
        with open(POSSIBLE_CYCLES_TXT_FILE, 'r') as f:
            txt_content = f.read().strip().split('\n')
        
        expected_txt_lines = [
            "USDT -> BTC -> ETH -> USDT",
            "USDT -> ETH -> BTC -> USDT",
        ]
        self.assertEqual(set(txt_content), set(expected_txt_lines))

    @patch('cli_monitor.arbitrage.cycle_finder.BinanceClient')
    def test_no_cycles_found(self, MockBinanceClient):
        """Test that no cycles are found when no valid pairs exist."""
        # Mock the Binance client and its method
        mock_client_instance = MockBinanceClient.return_value
        mock_client_instance.get_exchange_info.return_value = MOCK_EXCHANGE_INFO_NO_CYCLES

        # Run the function
        find_arbitrage_cycles()

        # Check that the output files are created but are empty
        self.assertTrue(os.path.exists(POSSIBLE_CYCLES_JSON_FILE))
        with open(POSSIBLE_CYCLES_JSON_FILE, 'r') as f:
            cycles_data = json.load(f)
        self.assertEqual(cycles_data, [])

        self.assertTrue(os.path.exists(POSSIBLE_CYCLES_TXT_FILE))
        with open(POSSIBLE_CYCLES_TXT_FILE, 'r') as f:
            txt_content = f.read()
        self.assertEqual(txt_content, "")

if __name__ == '__main__':
    unittest.main()