# -*- coding: utf-8 -*-
"""
Тести для перевірки стійкості BinanceClient до помилок API.
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from binance.exceptions import BinanceAPIException, BinanceRequestException
from requests.exceptions import ConnectionError

from tenacity import RetryError

from cli_monitor.common.binance_client import BinanceClient


@pytest.fixture
def mock_config(mocker):
    """Мок для конфігурації, щоб уникнути реальних ключів API."""
    mocker.patch('cli_monitor.common.binance_client.config.api_key', 'test_key')
    mocker.patch('cli_monitor.common.binance_client.config.api_secret', 'test_secret')


def test_get_spot_balance_retry_on_connection_error(mock_config, mocker, caplog):
    """
    Перевіряє, що get_spot_balance робить повторні спроби при ConnectionError
    і врешті-решт повертає успішний результат.
    """
    # Налаштовуємо мок клієнта, щоб він спочатку видавав помилку, а потім успішний результат
    mock_api_call = MagicMock(
        side_effect=[
            ConnectionError("Test connection error"),
            ConnectionError("Test connection error"),
            {'balances': [{'asset': 'BTC', 'free': '1.0'}]}
        ]
    )
    
    # Патчимо реальний клієнт python-binance всередині нашого BinanceClient
    mocker.patch('binance.client.Client.ping') # Мокаємо ping при ініціалізації
    mocker.patch('binance.client.Client.get_account', mock_api_call)

    # Встановлюємо рівень логування, щоб бачити повідомлення про повтори
    caplog.set_level(logging.WARNING)

    # Створюємо екземпляр нашого клієнта
    client = BinanceClient()
    
    # Викликаємо метод, який ми тестуємо
    result = client.get_spot_balance()

    # Перевіряємо результат
    assert result == [{'asset': 'BTC', 'total': '1.0'}]
    
    # Перевіряємо, що було зроблено 3 спроби (2 невдалі + 1 успішна)
    assert mock_api_call.call_count == 3
    
    # Перевіряємо, що в логах є 2 повідомлення про повторні спроби
    retry_logs = [rec for rec in caplog.records if "Помилка API, повторна спроба" in rec.message]
    assert len(retry_logs) == 2
    assert "Причина: Test connection error" in retry_logs[0].message


def test_init_retry_and_fail(mock_config, mocker, caplog):
    """
    Перевіряє, що ініціалізація клієнта робить кілька спроб і 
    врешті-решт видає виняток, якщо з'єднання не вдалося.
    """
    # Налаштовуємо мок ping, щоб він завжди видавав помилку
    mocker.patch('binance.client.Client.ping', side_effect=ConnectionError("Failed to connect"))

    caplog.set_level(logging.WARNING)

    # Перевіряємо, що після всіх спроб буде піднято виняток tenacity.RetryError
    with pytest.raises(RetryError):
        BinanceClient()

    # Перевіряємо, що в логах є повідомлення про повторні спроби
    retry_logs = [rec for rec in caplog.records if "Помилка API, повторна спроба" in rec.message]
    # Очікуємо 4 повідомлення, оскільки остання, 5-та спроба, піднімає виняток
    assert len(retry_logs) == 4
