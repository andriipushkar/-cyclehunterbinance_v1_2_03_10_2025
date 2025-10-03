  Основна команда для запуску: python3 -m cli_monitor

  Робота з балансом (balance):
   * python3 -m cli_monitor balance get - Отримати поточні баланси всіх гаманців.
   * python3 -m cli_monitor balance monitor - Запустити безперервний моніторинг балансів.

  Арбітраж (arbitrage):
   * python3 -m cli_monitor arbitrage generate-whitelist - Створити "білий список" найліквідніших монет.
   * python3 -m cli_monitor arbitrage generate-blacklist - Створити "чорний список" найменш ліквідніших монет.
   * python3 -m cli_monitor arbitrage find-cycles - Знайти всі можливі арбітражні цикли.
   * python3 -m cli_monitor arbitrage run-monitor - Запустити моніторинг прибутковості знайдених циклів.
   * python3 -m cli_monitor arbitrage start-bot - Запустити автоматичного бота для моніторингу та симуляції угод.
   * python3 -m cli_monitor arbitrage backtest <start_date> <end_date> - Провести тестування стратегії на історичних даних.
