import argparse
import sys
from .balance import main as balance_main
from .arbitrage import main as arbitrage_main
from .common.config import config

def main():
    config.load_config()
    parser = argparse.ArgumentParser(description="SignalSeeker CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    balance_parser = subparsers.add_parser("balance", help="Balance monitor commands")
    balance_main.add_arguments(balance_parser)

    arbitrage_parser = subparsers.add_parser("arbitrage", help="Arbitrage tools commands")
    arbitrage_main.add_arguments(arbitrage_parser)

    # We need to handle the case where no arguments are provided
    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()

    if args.command == "balance":
        balance_main.run(args)
    elif args.command == "arbitrage":
        arbitrage_main.run(args)

if __name__ == "__main__":
    main()
