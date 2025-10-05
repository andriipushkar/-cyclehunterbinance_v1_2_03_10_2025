"""
Цей модуль є точкою входу для підкоманд, пов'язаних з арбітражем.

Він визначає, які функції викликати на основі аргументів командного рядка,
переданих користувачем (наприклад, `find-cycles`, `run-monitor`).
"""

import argparse
import asyncio
from loguru import logger

from .cycle_finder import CycleFinder
from .profit_calculator import main as profit_calculator_main
from .backtester import Backtester
from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .bot import main as start_bot_main


class ArbitrageApp:
    """Клас, що інкапсулює логіку виконання арбітражних команд."""

    def __init__(self, args):
        """
        Ініціалізує додаток з аргументами командного рядка.

        Args:
            args: Аргументи, розпарсені з argparse.
        """
        self.args = args
        self._command_map = {
            "find-cycles": self._run_find_cycles,
            "run-monitor": self._run_monitor,
            "backtest": self._run_backtest,
            "generate-whitelist": self._run_generate_whitelist,
            "generate-blacklist": self._run_generate_blacklist,
            "start-bot": self._run_start_bot,
        }

    async def run(self):
        """Запускає відповідний метод на основі команди."""
        command_func = self._command_map.get(self.args.arbitrage_command)
        if command_func:
            await command_func()
        else:
            logger.error(f"Невідома арбітражна команда: {self.args.arbitrage_command}")

    async def _run_find_cycles(self):
        finder = None
        try:
            finder = await CycleFinder.create()
            await finder.run(strategy=self.args.strategy)
        finally:
            if finder and finder.client:
                await finder.client.close_connection()

    async def _run_monitor(self):
        await profit_calculator_main()

    async def _run_backtest(self):
        backtester = await Backtester.create(self.args.start_date, self.args.end_date)
        await backtester.run()

    async def _run_generate_whitelist(self):
        await generate_whitelist()

    async def _run_generate_blacklist(self):
        await generate_blacklist()

    async def _run_start_bot(self):
        try:
            await start_bot_main()
        except KeyboardInterrupt:
            logger.info("Роботу бота зупинено користувачем.")


def add_arguments(parser):
    """
    Додає специфічні для арбітражу підкоманди до парсера аргументів.

    Args:
        parser: Об'єкт `ArgumentParser` або `_SubParsersAction`.
    """
    subparsers = parser.add_subparsers(dest="arbitrage_command", required=True)

    # Команда для пошуку циклів
    find_cycles_parser = subparsers.add_parser("find-cycles", help="Знайти трикутні арбітражні цикли.")
    find_cycles_parser.add_argument('--strategy', type=str, default='liquidity', choices=['liquidity', 'volatility'], help="Стратегія відбору пар для пошуку циклів.")
    
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

async def run(args):
    """
    Створює екземпляр ArbitrageApp та запускає його.

    Args:
        args: Аргументи, розпарсені з командного рядка.
    """
    app = ArbitrageApp(args)
    await app.run()
