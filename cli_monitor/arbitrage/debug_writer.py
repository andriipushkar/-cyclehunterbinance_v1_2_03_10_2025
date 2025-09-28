"""
Цей модуль є простим асинхронним скриптом для відладки (дебагу).

Він періодично записує деяку інформацію (лічильник та поточний час) у лог-файл.
Це може бути корисним для перевірки роботи асинхронних завдань, доступності
файлової системи або для симуляції запису логів.
"""

import asyncio
import os
import time

# Визначення шляху до лог-файлу
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
DEBUG_LOG_FILE = os.path.join(LOG_DIR, 'debug_log.log')

async def write_to_log():
    """
    Асинхронна функція, яка в нескінченному циклі пише у лог-файл кожні 2 секунди.
    """
    counter = 0
    while True:
        counter += 1
        log_content = f"Рядок 1: {counter}\nРядок 2: {time.time()}\n"
        
        try:
            # Відкриваємо файл для запису (перезаписуючи його кожен раз)
            with open(DEBUG_LOG_FILE, 'w') as f:
                f.write(log_content)
        except Exception as e:
            print(f"Помилка запису в лог: {e}")
            
        # Асинхронна пауза на 2 секунди
        await asyncio.sleep(2)

if __name__ == "__main__":
    """
    Точка входу для запуску скрипта.
    """
    # Створюємо папку для логів, якщо вона не існує
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        # Запускаємо асинхронну функцію
        asyncio.run(write_to_log())
    except KeyboardInterrupt:
        # Обробка зупинки скрипта користувачем (Ctrl+C)
        print("Зупинено.")