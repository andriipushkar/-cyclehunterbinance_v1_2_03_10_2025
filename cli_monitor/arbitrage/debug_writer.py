import asyncio
import os
import time

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
DEBUG_LOG_FILE = os.path.join(LOG_DIR, 'debug_log.log')

async def write_to_log():
    counter = 0
    while True:
        counter += 1
        log_content = f"Line 1: {counter}\nLine 2: {time.time()}\n"
        
        try:
            with open(DEBUG_LOG_FILE, 'w') as f:
                f.write(log_content)
        except Exception as e:
            print(f"Error writing to log: {e}")
            
        await asyncio.sleep(2)

if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        asyncio.run(write_to_log())
    except KeyboardInterrupt:
        print("Stopped.")

