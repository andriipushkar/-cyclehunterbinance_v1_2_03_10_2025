"""
Цей модуль визначає головний клас `ArbitrageBot`, який оркеструє весь процес арбітражу.

Бот працює в нескінченному циклі, виконуючи щоденні налаштування та запускаючи
моніторинг прибутковості.
"""

import asyncio
import logging
from .whitelist_generator import generate_whitelist
from .blacklist_generator import generate_blacklist
from .cycle_finder import CycleFinder
from .profit_calculator import ProfitMonitor

class ArbitrageBot:
    """Головний клас бота, що керує процесом арбітражу."""

    def __init__(self):
        """Ініціалізує бота."""
        self.profit_monitor = None

    async def _perform_setup(self):
        """
        Виконує початкові кроки налаштування, які повторюються щодня.
        
        Ці кроки включають:
        1. Генерація "білого списку" (whitelist) монет.
        2. Генерація "чорного списку" (blacklist) монет.
        3. Пошук нових арбітражних циклів на основі "білого списку".
        """
        logging.info("Початок щоденного налаштування...")
        
        logging.info("Генерація білого списку...")
        generate_whitelist()
        
        logging.info("Генерація чорного списку...")
        generate_blacklist()
        
        logging.info("Пошук арбітражних циклів...")
        finder = CycleFinder()
        # Запускаємо пошук циклів, використовуючи тільки монети з білого списку
        finder.run(use_whitelist=True)
        
        logging.info("Щоденне налаштування завершено.")

    async def start(self):
        """
        Запускає головний цикл роботи бота.
        
        Бот виконує наступні дії:
        1. Проводить щоденне налаштування (списки монет, пошук циклів).
        2. Запускає моніторинг прибутковості знайдених циклів.
        3. Чекає 24 години.
        4. Зупиняє моніторинг і повторює цикл для оновлення даних.
        """
        while True:
            try:
                # 1. Виконання налаштувань
                await self._perform_setup()

                # 2. Запуск моніторингу прибутковості
                logging.info("Запуск монітора прибутковості...")
                self.profit_monitor = ProfitMonitor()
                monitor_task = asyncio.create_task(self.profit_monitor.start())

                # 3. Очікування протягом 24 годин
                logging.info("Бот працює. Оновлення через 24 години.")
                await asyncio.sleep(24 * 60 * 60)

                # 4. Зупинка моніторингу перед початком нового циклу
                logging.info("Минуло 24 години. Зупинка монітора для щоденного оновлення.")
                if self.profit_monitor:
                    await self.profit_monitor.stop()
                monitor_task.cancel()
                # Очікуємо завершення завдання моніторингу
                await asyncio.gather(monitor_task, return_exceptions=True)

            except asyncio.CancelledError:
                logging.info("Роботу бота зупинено.")
                if self.profit_monitor:
                    await self.profit_monitor.stop()
                break
            except Exception as e:
                logging.error(f"В головному циклі бота сталася неочікувана помилка: {e}")
                logging.info("Перезапуск циклу через 60 секунд...")
                await asyncio.sleep(60)

async def main():
    """Асинхронна функція для запуску бота."""
    bot = ArbitrageBot()
    await bot.start()