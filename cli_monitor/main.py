"""
Це головний модуль і точка входу для всього CLI-додатку.

Він відповідає за:
- Ініціалізацію конфігурації.
- Створення головного парсера аргументів командного рядка.
- Додавання підкоманд (`balance`, `arbitrage`) та їхніх аргументів.
- Визначення, яку підкоманду запустити на основі вводу користувача.
"""

import argparse
import sys
from .balance import main as balance_main
from .arbitrage import main as arbitrage_main
from .common.config import config
from .common.utils import setup_logging

def main():
    """
    Головна функція, що виконується при запуску `python3 -m cli_monitor`.
    """
    # Завантажуємо конфігурацію з файлів .env та config.json
    config.load_config()
    
    # Налаштовуємо логування
    setup_logging()
    
    # Створюємо головний парсер
    parser = argparse.ArgumentParser(description="CLI-інструмент для моніторингу та арбітражу на Binance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Додаємо підкоманду "balance" та її аргументи з модуля balance.main
    balance_parser = subparsers.add_parser("balance", help="Команди для моніторингу балансу")
    balance_main.add_arguments(balance_parser)

    # Додаємо підкоманду "arbitrage" та її аргументи з модуля arbitrage.main
    arbitrage_parser = subparsers.add_parser("arbitrage", help="Команди для інструментів арбітражу")
    arbitrage_main.add_arguments(arbitrage_parser)

    # Якщо програма запущена без аргументів, виводимо допомогу
    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    # Парсимо аргументи, передані користувачем
    args = parser.parse_args()

    # Викликаємо відповідний обробник для вибраної команди
    if args.command == "balance":
        balance_main.run(args)
    elif args.command == "arbitrage":
        arbitrage_main.run(args)

if __name__ == "__main__":
    main()