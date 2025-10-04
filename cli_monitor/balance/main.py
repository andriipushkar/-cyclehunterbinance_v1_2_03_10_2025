"""
Цей модуль є точкою входу для підкоманд, пов'язаних з моніторингом балансу.

Він додає до головного парсера CLI команди `get` та `monitor` і викликає
відповідні методи з класу `BalanceMonitor`.
"""

import argparse
from .commands import BalanceMonitor

class BalanceApp:
    """Клас, що інкапсулює логіку виконання команд для роботи з балансом."""

    def __init__(self, args):
        """
        Ініціалізує додаток з аргументами командного рядка.

        Args:
            args: Аргументи, розпарсені з argparse.
        """
        self.args = args
        self._command_map = {
            "get": self._run_get,
            "monitor": self._run_monitor,
        }

    def run(self):
        """Запускає відповідний метод на основі команди."""
        command_func = self._command_map.get(self.args.balance_command)
        if command_func:
            command_func()
        else:
            # Цей код не має виконуватись завдяки `required=True` в add_subparsers
            print(f"Невідома команда балансу: {self.args.balance_command}")

    def _run_get(self):
        monitor = BalanceMonitor()
        monitor.get_balances()

    def _run_monitor(self):
        monitor = BalanceMonitor()
        monitor.monitor_balances()

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
    Створює екземпляр BalanceApp та запускає його.

    Args:
        args: Аргументи, розпарсені з командного рядка.
    """
    app = BalanceApp(args)
    app.run()