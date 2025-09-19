import argparse
import asyncio
from .cycle_finder import find_triangular_arbitrage_cycles
from .profit_calculator import main as profit_calculator_main
from .backtester import run_backtest

def add_arguments(parser):
    subparsers = parser.add_subparsers(dest="arbitrage_command", required=True)

    find_cycles_parser = subparsers.add_parser("find-cycles", help="Find triangular arbitrage cycles.")
    
    run_monitor_parser = subparsers.add_parser("run-monitor", help="Run the profit calculator monitor.")

    backtest_parser = subparsers.add_parser("backtest", help="Backtest an arbitrage strategy.")
    backtest_parser.add_argument("start_date", help="Start date for backtesting (YYYY-MM-DD).")
    backtest_parser.add_argument("end_date", help="End date for backtesting (YYYY-MM-DD).")

def run(args):
    if args.arbitrage_command == "find-cycles":
        find_triangular_arbitrage_cycles()
    elif args.arbitrage_command == "run-monitor":
        asyncio.run(profit_calculator_main())
    elif args.arbitrage_command == "backtest":
        asyncio.run(run_backtest(args.start_date, args.end_date))
