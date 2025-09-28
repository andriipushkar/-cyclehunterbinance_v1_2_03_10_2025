"""
Тести для головного модуля `main`.

Ці тести перевіряють, що головна функція `main` правильно розбирає
аргументи командного рядка та викликає відповідні обробники
для кожної підкоманди (`balance` та `arbitrage`).
"""

import pytest
from unittest.mock import patch, MagicMock
from cli_monitor import main

# Мокуємо завантаження конфігурації, щоб уникнути залежності від реальних файлів
@patch('cli_monitor.common.config.config.load_config')
# Мокуємо `sys.argv`, щоб імітувати запуск з командного рядка
@patch('sys.argv', ['cli_monitor', 'balance', 'get'])
# Мокуємо парсер аргументів
@patch('cli_monitor.main.argparse.ArgumentParser')
def test_main_balance_command(MockArgumentParser, mock_load_config):
    """Тестує, що команда `balance get` викликає правильний обробник."""
    # Arrange
    mock_parser = MockArgumentParser.return_value
    # Імітуємо, що парсер повернув аргументи для команди balance -> get
    mock_parser.parse_args.return_value = MagicMock(command='balance', balance_command='get')
    
    # Мокуємо функцію `run` в модулі `balance.main`
    with patch('cli_monitor.balance.main.run') as mock_balance_run:
        # Act
        main.main()
        # Assert
        # Перевіряємо, що обробник для команди balance був викликаний
        mock_balance_run.assert_called_once()

@patch('cli_monitor.common.config.config.load_config')
@patch('sys.argv', ['cli_monitor', 'arbitrage', 'find-cycles'])
@patch('cli_monitor.main.argparse.ArgumentParser')
def test_main_arbitrage_command(MockArgumentParser, mock_load_config):
    """Тестує, що команда `arbitrage find-cycles` викликає правильний обробник."""
    # Arrange
    mock_parser = MockArgumentParser.return_value
    mock_parser.parse_args.return_value = MagicMock(command='arbitrage', arbitrage_command='find-cycles')
    
    with patch('cli_monitor.arbitrage.main.run') as mock_arbitrage_run:
        # Act
        main.main()
        # Assert
        # Перевіряємо, що обробник для команди arbitrage був викликаний
        mock_arbitrage_run.assert_called_once()