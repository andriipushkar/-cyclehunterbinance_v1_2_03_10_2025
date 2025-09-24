import json
import logging
import os
from datetime import datetime, timezone
from dateutil import tz

def setup_logging():
    """Sets up logging to a file in a date-stamped directory."""
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'bot.log')

    # Remove all handlers associated with the root logger object.
    # This is to avoid adding handlers multiple times in case of reloads.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def save_to_json(data, filename="output.json"):
    """
    Saves data to a JSON file with a timestamp.

    Args:
        data: The data to save.
        filename (str, optional): The name of the output file. Defaults to "output.json".
    """
    local_tz = tz.tzlocal()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    output_data = {
        "last_updated": now_local.strftime('%d/%m/%Y %H:%M'),
        "data": data,
    }
    with open(filename, "w") as f:
        json.dump(output_data, f, indent=2)

def format_balances(balances):
    """
    Formats the balances for display.

    Args:
        balances (dict): A dictionary containing the balances.

    Returns:
        str: A formatted string representing the balances.
    """
    local_tz = tz.tzlocal()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    # This can be improved with the 'rich' library later
    spot_balances = balances.get("spot", [])
    futures_balances = balances.get("futures", [])
    earn_balances = balances.get("earn", [])
    total_spot_balance_usd = balances.get("total_spot_balance_usd", 0)
    total_futures_balance_usd = balances.get("total_futures_balance_usd", 0)
    total_earn_balance_usd = balances.get("total_earn_balance_usd", 0)
    total_balance_usd = balances.get("total_balance_usd", 0)

    output = [
        f"--- Last Updated: {now_local.strftime('%d/%m/%Y %H:%M')} ---",
        f"--- Total Balance: ${total_balance_usd:.2f} ---",
        "",
        f"--- Total Spot Balance: ${total_spot_balance_usd:.2f} ---",
        "--- Spot Balances ---"
    ]
    if spot_balances:
        for balance in spot_balances:
            output.append(f"  {balance['asset']}: {balance['total']}")
    else:
        output.append("  No spot balances found.")

    output.extend([
        "",
        f"--- Total Futures Balance: ${total_futures_balance_usd:.2f} ---",
        "--- Futures Balances ---"
    ])
    if futures_balances:
        for balance in futures_balances:
            output.append(f"  {balance['asset']}: {balance['balance']}")
    else:
        output.append("  No futures balances found.")

    output.extend([
        "",
        f"--- Total Earn Balance: ${total_earn_balance_usd:.2f} ---",
        "--- Earn Balances ---"
    ])
    if earn_balances:
        for balance in earn_balances:
            output.append(f"  {balance['asset']}: {balance['total']}")
    else:
        output.append("  No earn balances found.")

    return "\n".join(output)


def structure_cycles_and_get_pairs(cycles_coins, symbols_info):
    """Structures cycles and gets all unique pairs."""
    structured_cycles = []
    all_pairs = set()
    all_symbols = list(symbols_info)

    for coins in cycles_coins:
        current_cycle_steps = []
        all_pairs_in_cycle = []
        valid_cycle = True
        for i in range(len(coins) - 1):
            pair_symbol = f'{coins[i+1]}{coins[i]}' if f'{coins[i+1]}{coins[i]}' in all_symbols else f'{coins[i]}{coins[i+1]}'
            if pair_symbol not in all_symbols:
                valid_cycle = False
                break
            
            # Check if the symbol is trading
            if symbols_info[pair_symbol]['status'] != 'TRADING':
                valid_cycle = False
                break

            current_cycle_steps.append({"pair": pair_symbol, "from": coins[i], "to": coins[i+1]})
            all_pairs_in_cycle.append(pair_symbol)

        if valid_cycle:
            cycle_info = {"coins": coins, "steps": current_cycle_steps}
            structured_cycles.append(cycle_info)
            all_pairs.update(all_pairs_in_cycle)
            
    return structured_cycles, all_pairs
