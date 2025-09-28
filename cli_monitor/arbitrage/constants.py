"""
Цей модуль визначає глобальні константи, що використовуються в усьому проекті.

Це допомагає уникнути "магічних" значень у коді та полегшує конфігурацію
та підтримку, оскільки всі важливі шляхи та налаштування зібрані в одному місці.
"""

import os
from decimal import getcontext

# --- Точність для розрахунків --- 
# Встановлює кількість значущих цифр для об'єктів Decimal
getcontext().prec = 15

# --- Директорії --- 
# Визначення абсолютних шляхів до основних папок проекту.
# os.path.dirname(__file__) -> поточна папка (arbitrage)
# os.path.join(..., '..') -> перехід на рівень вище

# Папка з файлами конфігурації
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))

# Папка для лог-файлів
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))

# Папка для вихідних файлів (результати роботи, звіти)
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'output'))

# --- Шляхи до файлів --- 
# Повні шляхи до конкретних файлів, що використовуються в додатку.

# Головний конфігураційний файл
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

# Файл зі знайденими арбітражними циклами
POSSIBLE_CYCLES_FILE = os.path.join(CONFIG_DIR, 'possible_cycles.json')

# Файл з "білим списком" монет та пар
WHITELIST_FILE = os.path.join(CONFIG_DIR, 'whitelist.json')

# Файл для звіту про прибутковість всіх циклів у форматі TXT
ALL_PROFITS_TXT_FILE = os.path.join(OUTPUT_DIR, 'all_profits.txt')

# Файл для звіту про прибутковість всіх циклів у форматі JSON
ALL_PROFITS_JSON_FILE = os.path.join(OUTPUT_DIR, 'all_profits.json')

# Файл для збереження останніх отриманих цін
LATEST_PRICES_FILE = os.path.join(OUTPUT_DIR, 'latest_prices.json')

# --- WebSocket --- 
# Розмір "чанка" - кількість стрімів, що об'єднуються в одне WebSocket з'єднання.
# Це потрібно, щоб не перевищувати ліміт на довжину URL для стріму.
CHUNK_SIZE = 100