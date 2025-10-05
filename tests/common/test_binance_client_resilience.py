# -*- coding: utf-8 -*-
"""
Тести для перевірки стійкості BinanceClient до помилок API.
"""

from loguru import logger
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from binance.exceptions import BinanceAPIException, BinanceRequestException
from aiohttp.client_exceptions import ClientConnectorError

from tenacity import RetryError

from cli_monitor.common.binance_client import BinanceClient, _log_retry_attempt


@pytest.fixture
def mock_config(mocker):
    """Мок для конфігурації, щоб уникнути реальних ключів API."""
    mocker.patch('cli_monitor.common.binance_client.config.api_key', 'test_key')
    mocker.patch('cli_monitor.common.binance_client.config.api_secret', 'test_secret')

@pytest.mark.asyncio
async def test_get_spot_balance_retry_on_connection_error(mock_config, mocker, caplog):
    """
    Перевіряє, що get_spot_balance робить повторні спроби при ConnectionError
    і врешті-решт повертає успішний результат.
    """
    
    with patch('binance.AsyncClient.create', new_callable=AsyncMock) as mock_create:
        mock_client = AsyncMock()
        mock_client.get_account.side_effect=[
            ClientConnectorError(MagicMock(), MagicMock()),
            ClientConnectorError(MagicMock(), MagicMock()),
            {'balances': [{'asset': 'BTC', 'free': '1.0'}]}
        ]
        mock_client.ping = AsyncMock()
        mock_create.return_value = mock_client

        client = await BinanceClient.create()
        client.get_spot_balance.retry.before_sleep = _log_retry_attempt

        with caplog.at_level(logging.WARNING):
            result = await client.get_spot_balance()

            assert result == [{'asset': 'BTC', 'total': '1.0'}]
            assert mock_client.get_account.call_count == 3
            
            retry_logs = [rec for rec in caplog.records if "Помилка API, повторна спроба" in rec.message]
            assert len(retry_logs) == 2
        await client.close_connection()

@pytest.mark.asyncio
async def test_init_retry_and_fail(mock_config, mocker, caplog):
    """
    Перевіряє, що ініціалізація клієнта робить кілька спроб і 
    врешті-решт видає виняток, якщо з'єднання не вдалося.
    """
    mocker.patch('binance.AsyncClient.create', side_effect=ClientConnectorError(MagicMock(), MagicMock()))

    with caplog.at_level(logging.WARNING):
        with pytest.raises(RetryError):
            await BinanceClient.create()

        retry_logs = [rec for rec in caplog.records if "Помилка API, повторна спроба" in rec.message]
        assert len(retry_logs) == 4