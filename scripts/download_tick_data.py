import MetaTrader5 as mt5
import logging
from datetime import datetime, timedelta
import os

# --- Logging Setup ---
log_dir = "C:/EA_Validation_Project/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"download_tick_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Configuration ---
SYMBOL = "XAUUSD"
DAYS_TO_DOWNLOAD = 365  # Number of days of tick data to download

# Initialize MetaTrader5
if not mt5.initialize():
    logging.error("Failed to initialize MetaTrader5: %s", mt5.last_error())
    print("❌ Failed to initialize MetaTrader5. Check logs for details.")
    exit()

logging.info("MetaTrader5 initialized successfully.")
print("MetaTrader5 initialized successfully.")

# Calculate the date range for tick data
to_date = datetime.now()
from_date = to_date - timedelta(days=DAYS_TO_DOWNLOAD)

# Download tick data
logging.info(f"Downloading tick data for {SYMBOL} from {from_date} to {to_date}.")
print(f"Downloading tick data for {SYMBOL} from {from_date} to {to_date}.")

ticks = mt5.copy_ticks_range(SYMBOL, from_date, to_date, mt5.COPY_TICKS_ALL)
if ticks is None:
    logging.error("Failed to download tick data: %s", mt5.last_error())
    print("❌ Failed to download tick data. Check logs for details.")
    mt5.shutdown()
    exit()

logging.info(f"Successfully downloaded {len(ticks)} ticks for {SYMBOL}.")
print(f"✅ Successfully downloaded {len(ticks)} ticks for {SYMBOL}.")

# Shutdown MetaTrader5
mt5.shutdown()
logging.info("MetaTrader5 shutdown successfully.")
print("MetaTrader5 shutdown successfully.")
