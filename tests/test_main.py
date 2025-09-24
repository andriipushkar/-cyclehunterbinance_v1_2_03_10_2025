
import pytest
from unittest.mock import patch, MagicMock
from cli_monitor import main

@patch('cli_monitor.common.config.config.load_config')
@patch('sys.argv', ['cli_monitor', 'balance', 'get'])
@patch('cli_monitor.main.argparse.ArgumentParser')
def test_main(MockArgumentParser, mock_load_config):
    mock_parser = MockArgumentParser.return_value
    mock_parser.parse_args.return_value = MagicMock(command='balance', balance_command='get')
    
    with patch('cli_monitor.balance.main.run') as mock_balance_run:
        main.main()
        mock_balance_run.assert_called_once()

@patch('cli_monitor.common.config.config.load_config')
@patch('sys.argv', ['cli_monitor', 'arbitrage', 'find-cycles'])
@patch('cli_monitor.main.argparse.ArgumentParser')
def test_main_arbitrage(MockArgumentParser, mock_load_config):
    mock_parser = MockArgumentParser.return_value
    mock_parser.parse_args.return_value = MagicMock(command='arbitrage', arbitrage_command='find-cycles')
    
    with patch('cli_monitor.arbitrage.main.run') as mock_arbitrage_run:
        main.main()
        mock_arbitrage_run.assert_called_once()
