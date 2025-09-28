"""
Цей модуль є точкою входу для підкоманд, пов'язаних з моніторингом балансу.

Він додає до головного парсера CLI команди `get` та `monitor` і викликає
відповідні методи з класу `BalanceMonitor`.
"""

import argparse
from .commands import BalanceMonitor

def add_arguments(parser):
    """
    Додає специфічні для балансу підкоманди до парсера аргументів.

    Args:
        parser: Об'єкт `ArgumentParser` або `_SubParsersAction`.
    """
    subparsers = parser.add_subparsers(dest="balance_command", required=True)

    # Команда для одноразового отримання балансу
    get_parser = subparsers.add_parser("get", help="Отримати поточні баланси.")
    
    # Команда для запуску безперервного моніторингу балансу
    monitor_parser = subparsers.add_parser("monitor", help="Відстежувати баланси безперервно.")

def run(args):
    """
    Виконує відповідну функцію на основі переданих аргументів.

    Args:
        args: Аргументи, розпарсені з командного рядка.
    """
    monitor = BalanceMonitor()
    if args.balance_command == "get":
        monitor.get_balances()
    elif args.balance_command == "monitor":
        monitor.monitor_balances()
