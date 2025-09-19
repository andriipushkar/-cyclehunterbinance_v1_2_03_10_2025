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
        level=logging.INFO,
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
