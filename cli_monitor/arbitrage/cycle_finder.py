"""Цей модуль відповідає за пошук потенційних арбітражних циклів на біржі.

Він завантажує інформацію про торгові пари, будує з них граф і знаходить
всі можливі цикли, що починаються і закінчуються в базовій валюті.
"""

import json
import logging
from cli_monitor.common.binance_client import BinanceClient
from cli_monitor.common.config import config
from . import constants

logging.basicConfig(level=logging.INFO)

class CycleFinder:
    """
    Клас для пошуку потенційних арбітражних циклів на біржі.

    Аналізує доступні торгові пари та знаходить замкнені ланцюжки
    (цикли) обміну, які можуть бути використані для арбітражу.
    """

    def __init__(self):
        """
        Ініціалізує екземпляр CycleFinder.

        Встановлює з'єднання з клієнтом Binance та завантажує базові
        налаштування з конфігурації, такі як базова валюта, список
        монет для моніторингу та максимальна довжина циклу.
        """
        self.client = BinanceClient()
        self.base_currency = config.base_currency
        self.monitored_coins = config.monitored_coins
        self.max_cycle_length = config.max_cycle_length
        self.exchange_info = None
        self.trading_pairs = None

    def _get_trading_pairs(self):
        """
        Створює граф торгових пар на основі інформації з біржі.

        Парсить дані з `exchange_info` і будує словник, де ключ - це
        назва монети, а значення - список монет, з якими вона торгується.
        Цей словник представляє собою список суміжності графа.

        Returns:
            dict: Словник, що представляє граф торгових пар.
                  Приклад: {'BTC': ['USDT', 'ETH'], 'ETH': ['BTC', 'USDT']}
        """
        pairs = {}
        for s in self.exchange_info['symbols']:
            # Перевіряємо, чи пара активна для торгівлі
            if s['status'] == 'TRADING':
                base = s['baseAsset']
                quote = s['quoteAsset']

                # Додаємо вершини та ребра в граф
                if base not in pairs:
                    pairs[base] = []
                if quote not in pairs:
                    pairs[quote] = []
                pairs[base].append(quote)
                pairs[quote].append(base)
        return pairs

    def _find_cycles_dfs(self, graph, start_node, max_length):
        """
        Знаходить усі прості цикли в графі за допомогою алгоритму пошуку в глибину (DFS).

        Простий цикл - це шлях, який починається і закінчується в одній вершині
        і не містить повторюваних вершин, окрім початкової/кінцевої.

        Args:
            graph (dict): Граф торгових пар (список суміжності).
            start_node (str): Вершина, з якої починається пошук циклів.
            max_length (int): Максимальна довжина циклу.

        Returns:
            list: Список знайдених циклів. Кожен цикл - це список монет.
                  Приклад: [['USDT', 'BTC', 'ETH', 'USDT'], ['USDT', 'BNB', 'USDT']]
        """
        cycles = []
        # Стек для DFS, зберігає кортежі (поточна вершина, поточний шлях)
        stack = [(start_node, [start_node])]

        while stack:
            (vertex, path) = stack.pop()

            # Обмеження глибини пошуку для уникнення занадто довгих циклів
            if len(path) > max_length:
                continue

            # Перебираємо сусідні вершини
            for neighbor in graph.get(vertex, []):
                # Якщо сусід - це початкова вершина, і цикл має довжину >= 2, ми знайшли цикл
                if neighbor == start_node and len(path) >= 2:
                    cycles.append(path + [neighbor])
                # Якщо сусіда ще немає в поточному шляху, продовжуємо пошук
                elif neighbor not in path:
                    stack.append((neighbor, path + [neighbor]))
        return cycles

    def _save_cycles(self, cycles):
        """
        Зберігає знайдені цикли у файли формату JSON та TXT.

        Args:
            cycles (list): Список знайдених циклів для збереження.
        """
        logging.info(f"Знайдено {len(cycles)} потенційних арбітражних циклів.")

        # Збереження в JSON
        with open(constants.POSSIBLE_CYCLES_FILE, 'w') as f:
            json.dump(cycles, f, indent=2)
        logging.info(f"Цикли збережено у {constants.POSSIBLE_CYCLES_FILE}")

        # Збереження в TXT для зручного перегляду
        txt_path = constants.POSSIBLE_CYCLES_FILE.replace('.json', '.txt')
        with open(txt_path, 'w') as f:
            for cycle in cycles:
                f.write(f"{ ' -> '.join(cycle)}\n")
        logging.info(f"Цикли збережено у {txt_path}")

    def run(self, use_whitelist=False):
        """
        Основний метод для запуску процесу пошуку циклів.

        Виконує повний цикл роботи: завантажує інформацію з біржі,
        фільтрує монети, будує граф, знаходить цикли та зберігає їх.

        Args:
            use_whitelist (bool): Якщо True, для пошуку будуть використовуватися
                                  тільки монети з "білого списку" (whitelist.json).
                                  Інакше - монети з конфігураційного файлу.
        """
        logging.info("-- Запуск Пошуку Циклів --")
        try:
            self.exchange_info = self.client.get_exchange_info()
        except Exception as e:
            logging.error(f"Помилка отримання інформації з біржі Binance: {e}")
            return

        all_trading_pairs = self._get_trading_pairs()

        # Визначаємо список дозволених монет для пошуку
        allowed_coins = set()
        if use_whitelist:
            logging.info("Використання 'білого списку' для фільтрації монет.")
            try:
                with open(constants.WHITELIST_FILE, 'r') as f:
                    whitelist_data = json.load(f)
                allowed_coins = set(whitelist_data.get('whitelist_assets', []))
            except FileNotFoundError:
                logging.error(f"Файл 'білого списку' {constants.WHITELIST_FILE} не знайдено.")
                return
            except json.JSONDecodeError:
                logging.error(f"Помилка декодування JSON з {constants.WHITELIST_FILE}.")
                return
        else:
            logging.info("Використання 'monitored_coins' з конфігурації для фільтрації.")
            allowed_coins = set(self.monitored_coins + [self.base_currency])

        if not allowed_coins:
            logging.error("Список дозволених монет порожній. Пошук неможливий.")
            return

        # Фільтруємо граф, залишаючи тільки дозволені монети
        self.trading_pairs = {}
        for coin, neighbors in all_trading_pairs.items():
            if coin in allowed_coins:
                filtered_neighbors = [n for n in neighbors if n in allowed_coins]
                if filtered_neighbors:
                    self.trading_pairs[coin] = filtered_neighbors

        # Запускаємо пошук циклів
        found_cycles = self._find_cycles_dfs(self.trading_pairs, self.base_currency, self.max_cycle_length)

        self._save_cycles(found_cycles)
        logging.info("-- Пошук Циклів Завершено --")


if __name__ == '__main__':
    """
    Точка входу для запуску скрипта як самостійної програми.
    Дозволяє запустити пошук циклів напряму.
    """
    finder = CycleFinder()
    finder.run()