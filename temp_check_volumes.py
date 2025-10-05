import asyncio
from cli_monitor.common.binance_client import BinanceClient

async def main():
    client = None
    try:
        client = await BinanceClient.create()
        tickers = await client.get_24h_ticker()
        for ticker in tickers:
            symbol = ticker['symbol']
            if symbol in ['AAVEUSDT', 'AAVEUSDC', 'FFUSDC']:
                print(f"{symbol}: {ticker['quoteVolume']}")
    finally:
        if client:
            await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
