"""
Цей модуль реалізує клієнт для роботи з WebSocket стрімами Binance.
"""

import asyncio
import json
import websockets
from loguru import logger

class WebSocketClient:
    """Клас для підключення до WebSocket стрімів Binance."""

    def __init__(self, queue):
        """Ініціалізує WebSocket клієнт.

        Args:
            queue (asyncio.Queue): Черга для передачі отриманих повідомлень.
        """
        self.queue = queue

    async def listen(self, pairs):
        """Підключається до WebSocket для списку пар і слухає повідомлення.

        Args:
            pairs (list): Список торгових пар для підписки.
        """
        streams = [f'{pair.lower()}@bookTicker' for pair in pairs]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        while True:
            try:
                async with websockets.connect(ws_url, ping_timeout=60) as ws:
                    logger.info(f"Підключено до стріму для {len(pairs)} пар.")
                    while True:
                        message = await ws.recv()
                        await self.queue.put(message)
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidStatusCode) as e:
                logger.warning(f"Помилка з'єднання WebSocket: {e}. Перепідключення...")
                await asyncio.sleep(5) # Пауза перед перепідключенням
            except Exception as e:
                logger.error(f"Неочікувана помилка WebSocket: {e}")
                break
