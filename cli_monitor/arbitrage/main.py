"""
Цей модуль є точкою входу для підкоманд, пов'язаних з арбітражем.

Він визначає, які функції викликати на основі аргументів командного рядка,
переданих користувачем (наприклад, `find-cycles`, `run-monitor`).
"""

import argparse
import asyncio
import logging
from .cycle_finder import CycleFinder
from .profit_calculator import main as profit_calculator_main
from .backtester import Backtester
from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .bot import main as start_bot_main

def add_arguments(parser):
    """
    Додає специфічні для арбітражу підкоманди до парсера аргументів.

    Args:
        parser: Об'єкт `ArgumentParser` або `_SubParsersAction`.
    """
    subparsers = parser.add_subparsers(dest="arbitrage_command", required=True)

    # Команда для пошуку циклів
    find_cycles_parser = subparsers.add_parser("find-cycles", help="Знайти трикутні арбітражні цикли.")
    
    # Команда для запуску моніторингу прибутковості
    run_monitor_parser = subparsers.add_parser("run-monitor", help="Запустити монітор розрахунку прибутку.")

    # Команда для бектестування
    backtest_parser = subparsers.add_parser("backtest", help="Провести бектестування арбітражної стратегії.")
    backtest_parser.add_argument("start_date", help="Початкова дата для бектестування (YYYY-MM-DD).")
    backtest_parser.add_argument("end_date", help="Кінцева дата для бектестування (YYYY-MM-DD).")

    # Команди для генерації списків
    whitelist_parser = subparsers.add_parser("generate-whitelist", help="Згенерувати білий список монет.")
    blacklist_parser = subparsers.add_parser("generate-blacklist", help="Згенерувати чорний список монет.")
    
    # Команда для запуску повноцінного бота
    start_bot_parser = subparsers.add_parser("start-bot", help="Запустити довготривалого арбітражного бота.")

def run(args):
    """
    Виконує відповідну функцію на основі переданих аргументів.

    Args:
        args: Аргументи, розпарсені з командного рядка.
    """
    if args.arbitrage_command == "find-cycles":
        finder = CycleFinder()
        finder.run()
    elif args.arbitrage_command == "run-monitor":
        asyncio.run(profit_calculator_main())
    elif args.arbitrage_command == "backtest":
        backtester = Backtester(args.start_date, args.end_date)
        asyncio.run(backtester.run())
    elif args.arbitrage_command == "generate-whitelist":
        generate_whitelist()
    elif args.arbitrage_command == "generate-blacklist":
        generate_blacklist()
    elif args.arbitrage_command == "start-bot":
        try:
            asyncio.run(start_bot_main())
        except KeyboardInterrupt:
            logging.info("Роботу бота зупинено користувачем.")
