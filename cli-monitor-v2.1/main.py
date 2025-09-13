import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from commands import get_balances, monitor_balances

def main():
    parser = argparse.ArgumentParser(description="Binance Balance Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    balance_parser = subparsers.add_parser("balance", help="Get current balances.")
    monitor_parser = subparsers.add_parser("monitor", help="Monitor balances continuously.")

    args = parser.parse_args()

    if args.command == "balance":
        get_balances()
    elif args.command == "monitor":
        monitor_balances()

if __name__ == "__main__":
    main()
