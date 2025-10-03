
import os
import glob
import pandas as pd
from decimal import Decimal
from tabulate import tabulate

def analyze_trades(start_date=None, end_date=None, output_file=None):
    """
    Аналізує файли з угодами та виводить зведений звіт.
    """
    trades_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'trades'))
    all_csv_files = glob.glob(os.path.join(trades_dir, '**', '*.csv'), recursive=True)

    if not all_csv_files:
        print("Не знайдено файлів з угодами в папці output/trades.")
        return

    # Фільтрація файлів за датою
    if start_date:
        all_csv_files = [f for f in all_csv_files if os.path.basename(os.path.dirname(f)) >= start_date]
    if end_date:
        all_csv_files = [f for f in all_csv_files if os.path.basename(os.path.dirname(f)) <= end_date]

    if not all_csv_files:
        print(f"Не знайдено файлів з угодами за вказаний період.")
        return

    df = pd.concat((pd.read_csv(f) for f in all_csv_files), ignore_index=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Фільтрація записів за датою
    if start_date:
        df = df[df['timestamp'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['timestamp'] <= pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)]

    if df.empty:
        print("Не знайдено угод за вказаний період часу.")
        return

    # --- Розрахунки ---
    df['initial_amount'] = df['initial_amount'].apply(Decimal)
    df['final_amount'] = df['final_amount'].apply(Decimal)
    df['profit'] = df['final_amount'] - df['initial_amount']
    df['profit_pct'] = (df['profit'] / df['initial_amount']) * 100

    total_trades = len(df)
    profitable_trades = df[df['profit'] > 0]
    num_profitable = len(profitable_trades)
    win_rate = (num_profitable / total_trades) * 100 if total_trades > 0 else 0
    total_profit = df['profit'].sum()
    average_profit_per_trade = df['profit_pct'].mean()

    # --- Аналіз циклів ---
    cycle_profit = df.groupby('cycle')['profit'].sum().sort_values(ascending=False)
    cycle_frequency = df['cycle'].value_counts()

    # --- Формування звіту ---
    report = []
    report.append("--- Зведений Звіт по Угодах ---")
    report.append(f"Період: {start_date or 'початку'} - {end_date or 'кінця'}")
    report.append(f"Загальна кількість угод: {total_trades}")
    report.append(f"Кількість прибуткових угод: {num_profitable}")
    report.append(f"Відсоток прибуткових угод (Win Rate): {win_rate:.2f}%")
    report.append(f"Загальний прибуток (в {df['initial_asset'].iloc[0]}): {total_profit:.8f}")
    report.append(f"Середній прибуток на угоду: {average_profit_per_trade:.4f}%")
    report.append("\n" + "="*50 + "\n")

    report.append("--- Топ-5 найприбутковіших циклів ---")
    report.append(tabulate(cycle_profit.head(5).reset_index(), headers=['Цикл', 'Загальний прибуток'], tablefmt='grid'))
    report.append("\n" + "="*50 + "\n")

    report.append("--- Топ-5 найчастіших циклів ---")
    report.append(tabulate(cycle_frequency.head(5).reset_index(), headers=['Цикл', 'Кількість угод'], tablefmt='grid'))
    report.append("\n")

    final_report = "\n".join(report)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(final_report)
        print(f"Звіт збережено у файл: {output_file}")
    else:
        print(final_report)

def add_arguments(parser):
    """Додає аргументи для команди аналізу."""
    parser.add_argument('--start_date', type=str, help='Початкова дата для аналізу (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, help='Кінцева дата для аналізу (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='Шлях до файлу для збереження звіту')
    parser.set_defaults(func=run)

def run(args):
    """Запускає аналіз."""    
    analyze_trades(args.start_date, args.end_date, args.output)
