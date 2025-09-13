import os
from dotenv import load_dotenv
from binance.client import Client

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'src', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Get API keys from environment
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# Check if keys are loaded
if not api_key or not api_secret:
    print("Error: BINANCE_API_KEY or BINANCE_API_SECRET not found in .env file.")
else:
    print("API keys loaded successfully.")

    # Initialize Binance client
    client = Client(api_key, api_secret)

    try:
        # Make a simple API call to get account status
        account_status = client.get_account_status()
        print("Successfully connected to Binance API.")
        print("Account status:", account_status)

        # Try to get account info
        account_info = client.get_account()
        print("Successfully fetched account information.")
        print("Account balances:")
        for balance in account_info['balances']:
            if float(balance['free']) > 0:
                print(f"- {balance['asset']}: {balance['free']}")

    except Exception as e:
        print(f"An error occurred: {e}")