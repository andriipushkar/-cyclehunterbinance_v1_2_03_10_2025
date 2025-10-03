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

    Аналізує доступні торгові пари, будує з них граф та знаходить замкнені 
    ланцюжки обміну (цикли), які можуть бути використані для арбітражу.
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
            # Враховуємо тільки активні торгові пари
            if s['status'] == 'TRADING':
                base = s['baseAsset']
                quote = s['quoteAsset']

                # Додаємо вершини (монети) та ребра (можливість обміну) в граф
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
            start_node (str): Вершина (монета), з якої починається пошук циклів.
            max_length (int): Максимальна довжина циклу (кількість монет).

        Returns:
            list: Список знайдених циклів. Кожен цикл - це список монет.
                  Приклад: [['USDT', 'BTC', 'ETH', 'USDT'], ['USDT', 'BNB', 'USDT']]
        """
        cycles = []
        # Стек для DFS, зберігає кортежі (поточна вершина, поточний шлях)
        stack = [(start_node, [start_node])]

        while stack:
            (vertex, path) = stack.pop()

            # Обмеження глибини пошуку для уникнення занадто довгих і складних циклів
            if len(path) > max_length:
                continue

            # Перебираємо сусідні вершини (монети, з якими можна торгувати)
            for neighbor in graph.get(vertex, []):
                # Якщо сусід - це початкова вершина, і цикл має довжину >= 3, ми знайшли цикл
                if neighbor == start_node and len(path) >= 3:
                    cycles.append(path + [neighbor])
                # Якщо сусіда ще немає в поточному шляху, продовжуємо пошук вглиб
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

        # Збереження в JSON для подальшої машинної обробки
        with open(constants.POSSIBLE_CYCLES_FILE, 'w') as f:
            json.dump(cycles, f, indent=2)
        logging.info(f"Цикли збережено у {constants.POSSIBLE_CYCLES_FILE}")

        # Збереження в TXT для зручного ручного перегляду
        txt_path = constants.POSSIBLE_CYCLES_FILE.replace('.json', '.txt')
        with open(txt_path, 'w') as f:
            for cycle in cycles:
                f.write(f"{ ' -> '.join(cycle)}\n")
        logging.info(f"Цикли збережено у {txt_path}")

    def _get_coins_by_volatility(self):
        """
        Відбирає монети на основі їхньої 24-годинної волатильності.
        Стратегія полягає в тому, щоб зосередитись на монетах, ціна яких сильно коливається,
        оскільки це може створювати більше арбітражних можливостей.
        """
        logging.info("Відбір монет за стратегією волатильності...")
        tickers = self.client.get_24h_ticker()
        if not tickers:
            logging.error("Не вдалося отримати дані тікерів для розрахунку волатильності.")
            return set()

        # Розраховуємо абсолютну волатильність для кожної пари
        for ticker in tickers:
            try:
                price_change_percent = float(ticker.get('priceChangePercent', 0))
                ticker['volatility'] = abs(price_change_percent)
            except (ValueError, TypeError):
                ticker['volatility'] = 0

        # Сортуємо пари за спаданням волатильності
        sorted_tickers = sorted(tickers, key=lambda t: t['volatility'], reverse=True)
        
        # Вибираємо топ-N найбільш волатильних пар згідно конфігурації
        top_n_pairs = config.whitelist_top_n_pairs
        top_volatile_pairs = sorted_tickers[:top_n_pairs]

        # Збираємо унікальні монети з цих пар, додаючи базову валюту
        allowed_coins = set([self.base_currency])
        for ticker in top_volatile_pairs:
            # Знаходимо інформацію про пару, щоб отримати базовий та котирувальний активи
            symbol_info = next((s for s in self.exchange_info['symbols'] if s['symbol'] == ticker['symbol']), None)
            if symbol_info:
                allowed_coins.add(symbol_info['baseAsset'])
                allowed_coins.add(symbol_info['quoteAsset'])
        
        logging.info(f"Відібрано {len(allowed_coins)} монет на основі волатильності.")
        return allowed_coins

    def get_allowed_coins(self, strategy='liquidity'):
        """
        Повертає набір дозволених монет на основі обраної стратегії.
        Це ключовий метод для фільтрації, що визначає, які монети братимуть участь у пошуку циклів.
        """
        # Кешування інформації про біржу, щоб не робити зайвих запитів
        if not self.exchange_info:
            try:
                self.exchange_info = self.client.get_exchange_info()
            except Exception as e:
                logging.error(f"Помилка отримання інформації з біржі Binance: {e}")
                return set()

        allowed_coins = set()
        if strategy == 'liquidity':
            # Стратегія за замовчуванням: використовуємо монети з попередньо згенерованого білого списку
            logging.info("Використання 'білого списку' для фільтрації монет.")
            try:
                with open(constants.WHITELIST_FILE, 'r') as f:
                    whitelist_data = json.load(f)
                allowed_coins = set(whitelist_data.get('whitelist_assets', []))
            except FileNotFoundError:
                logging.warning(f"Файл 'білого списку' {constants.WHITELIST_FILE} не знайдено. Спробуйте згенерувати його спочатку.")
                # Фоллбек: використовуємо базові монети з конфігурації
                allowed_coins = set(config.whitelist_base_coins + [self.base_currency])
            except json.JSONDecodeError:
                logging.error(f"Помилка декодування JSON з {constants.WHITELIST_FILE}.")
                return set()
        elif strategy == 'volatility':
            # Стратегія волатильності: вибираємо найактивніші монети
            allowed_coins = self._get_coins_by_volatility()
        else:
            # Фоллбек: використовуємо список монет, жорстко заданий у конфігурації
            logging.info("Використання 'monitored_coins' з конфігурації для фільтрації.")
            allowed_coins = set(self.monitored_coins + [self.base_currency])
        
        return allowed_coins

    def run(self, strategy='liquidity'):
        """
        Основний метод для запуску процесу пошуку циклів.
        Оркеструє весь процес: від вибору монет до збереження результатів.

        Args:
            strategy (str): Стратегія відбору монет ('liquidity' або 'volatility').
        """
        logging.info(f"-- Запуск Пошуку Циклів (Стратегія: {strategy}) --")
        
        # 1. Отримуємо набір монет для аналізу згідно з обраною стратегією
        allowed_coins = self.get_allowed_coins(strategy)

        if not allowed_coins:
            logging.error("Список дозволених монет порожній. Пошук неможливий.")
            return

        # 2. Будуємо повний граф всіх торгових пар на біржі
        all_trading_pairs = self._get_trading_pairs()

        # 3. Фільтруємо граф, залишаючи тільки ребра між дозволеними монетами
        self.trading_pairs = {}
        for coin, neighbors in all_trading_pairs.items():
            if coin in allowed_coins:
                filtered_neighbors = [n for n in neighbors if n in allowed_coins]
                if filtered_neighbors:
                    self.trading_pairs[coin] = filtered_neighbors

        # 4. Запускаємо пошук циклів на відфільтрованому графі
        found_cycles = self._find_cycles_dfs(self.trading_pairs, self.base_currency, self.max_cycle_length)

        # 5. Зберігаємо знайдені цикли у файли
        self._save_cycles(found_cycles)
        logging.info("-- Пошук Циклів Завершено --")


if __name__ == '__main__':
    """
    Точка входу для запуску скрипта як самостійної програми.
    Дозволяє запустити пошук циклів напряму, минаючи головний CLI-парсер.
    """
    finder = CycleFinder()
    finder.run()