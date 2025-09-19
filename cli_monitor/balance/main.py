import argparse
from .commands import get_balances, monitor_balances

def add_arguments(parser):
    subparsers = parser.add_subparsers(dest="balance_command", required=True)

    get_parser = subparsers.add_parser("get", help="Get current balances.")
    monitor_parser = subparsers.add_parser("monitor", help="Monitor balances continuously.")

def run(args):
    if args.balance_command == "get":
        get_balances()
    elif args.balance_command == "monitor":
        monitor_balances()
