# CycleHunter

**CycleHunter** - це CLI-інструмент, розроблений для моніторингу балансів на біржі Binance та виявлення можливостей для арбітражу.

## Основні можливості

- **Моніторинг балансу:** Відстежуйте баланси Spot, Futures та Earn у реальному часі.
- **Пошук арбітражних циклів:** Знаходьте потенційні арбітражні цикли на основі ваших налаштувань.
- **Моніторинг прибутковості:** Розраховуйте та відстежуйте прибутковість знайдених циклів у реальному часі.
- **Бектестінг:** Тестуйте свої арбітражні стратегії на історичних даних.

## Початок роботи

### 1. Клонування репозиторію

```bash
git clone https://github.com/your-username/CycleHunter.git
cd CycleHunter
```

### 2. Створення та активація віртуального середовища

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Налаштування API ключів Binance

Створіть файл `.env` у кореневому каталозі проекту та додайте ваші API ключі:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

**Важливо:** Для безпеки рекомендується використовувати ключі з правами "тільки для читання".

## Використання

Основна команда для взаємодії з інструментом - `python3 -m cli_monitor`.

### Моніторинг балансу

- **Отримати поточний баланс:**
  ```bash
  python3 -m cli_monitor balance get
  ```
- **Запустити моніторинг балансу:**
  ```bash
  python3 -m cli_monitor balance monitor
  ```

### Арбітраж

- **Запустити пошук арбітражних циклів:**
  ```bash
  # За замовчуванням використовує стратегію ліквідності (з whitelist.json)
  python3 -m cli_monitor arbitrage find-cycles

  # Можна також вказати стратегію на основі волатильності
  python3 -m cli_monitor arbitrage find-cycles --strategy volatility
  ```
- **Запустити моніторинг прибутковості:**
  ```bash
  python3 -m cli_monitor arbitrage run-monitor
  ```
- **Запустити бектестування стратегії:**
  ```bash
  python3 -m cli_monitor arbitrage backtest <start_date> <end_date>
  ```
  *Приклад:*
  ```bash
  python3 -m cli_monitor arbitrage backtest 2023-01-01 2023-01-31
  ```

### Інструменти та автоматизація

- **Згенерувати "білий список" монет:**
  ```bash
  python3 -m cli_monitor arbitrage generate-whitelist
  ```
- **Згенерувати "чорний список" монет:**
  ```bash
  python3 -m cli_monitor arbitrage generate-blacklist
  ```
- **Запустити автоматичного бота:**
  ```bash
  python3 -m cli_monitor arbitrage start-bot
  ```


## Структура проекту

```
├── cli_monitor/      # Основний пакет з логікою CLI
├── configs/          # Файли конфігурації
├── docs/             # Документація проекту
├── logs/             # Лог-файли
├── output/           # Файли з результатами роботи
├── tests/            # Тести
├── .gitignore        # Файли та папки, які ігноруються Git
├── pytest.ini        # Конфігурація Pytest
├── README.md         # Цей файл
└── requirements.txt  # Залежності проекту
```

## Конфігурація

Основний файл конфігурації - `configs/config.json`. У ньому ви можете налаштувати:

- `base_currency`: Основна валюта для пошуку циклів.
- `trading_fee`: Комісія за торгівлю.
- `min_profit_threshold`: Мінімальний відсоток прибутку для запису в лог.
- `max_cycle_length`: Максимальна кількість монет у циклі.
- `monitored_coins`: Список монет для моніторингу.

## Внесок

Будь-який внесок вітається! Будь ласка, створюйте pull request з детальним описом ваших змін.

## Ліцензія

Цей проект ліцензовано на умовах ліцензії MIT.