import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from scripts.utils import ensure_dir
import logging

RAW_XML_DIR = "raw_xml"
CSV_OUTPUT_DIR = "processed_csv"

def setup_logging():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_filename = f"convert_latest_xml_to_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(LOGS_DIR, log_filename)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging to {log_path}")
    return log_path

def find_latest_xml(folder):
    xml_files = [f for f in os.listdir(folder) if f.endswith(".xml")]
    if not xml_files:
        raise FileNotFoundError("No XML files found in raw_xml/")
    xml_files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
    return os.path.join(folder, xml_files[0])

def parse_mt5_excel_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    # Find the worksheet with the results
    worksheet = root.find(".//ss:Worksheet[@ss:Name='Tester Optimizator Results']", ns)
    if worksheet is None:
        raise ValueError("Could not find worksheet 'Tester Optimizator Results' in XML.")
    table = worksheet.find("ss:Table", ns)
    if table is None:
        raise ValueError("Could not find Table in worksheet.")
    rows = table.findall("ss:Row", ns)
    if not rows or len(rows) < 2:
        return pd.DataFrame()
    # Extract headers
    headers = [cell.find("ss:Data", ns).text for cell in rows[0].findall("ss:Cell", ns)]
    # Extract data
    data = []
    for row in rows[1:]:
        cells = row.findall("ss:Cell", ns)
        values = [cell.find("ss:Data", ns).text if cell.find("ss:Data", ns) is not None else '' for cell in cells]
        # Pad missing cells
        while len(values) < len(headers):
            values.append('')
        data.append(values)
    df = pd.DataFrame(data, columns=headers)
    return df

def calculate_metrics(df):
    # Lowercase all columns for consistency
    df.columns = [c.lower().replace(' ', '').replace('%','percent') for c in df.columns]
    def safe_num(col):
        return pd.to_numeric(df[col], errors='coerce') if col in df.columns else 0
    # Add/convert columns as needed for downstream scripts
    df["profit"] = safe_num("profit")
    df["maxdrawdown"] = safe_num("equityddpercent")
    df["trades"] = safe_num("trades")
    df["profitfactor"] = safe_num("profitfactor")
    df["sharperatio"] = safe_num("sharperatio")
    df["expectedpayoff"] = safe_num("expectedpayoff")
    df["recoveryfactor"] = safe_num("recoveryfactor")
    # WinRate: if possible, calculate from available columns
    if "winrate" not in df.columns and "forwardresult" in df.columns and "trades" in df.columns:
        df["winrate"] = safe_num("forwardresult")
    return df

def parse_and_format_date(date_str):
    # Accepts 'YYYY-MM-DD', 'YYYY/MM/DD', or with spaces, returns 'YYYY.MM.DD'
    import re
    date_str = date_str.strip().replace('/', '-').replace('.', '-')
    # Remove any non-digit or dash
    date_str = re.sub(r'[^0-9\-]', '', date_str)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y.%m.%d"), dt
    except Exception:
        return None, None

def validate_symbol(symbol):
    """Validate the symbol input."""
    import re
    if re.match(r'^[A-Z]{3,6}$', symbol):
        return True
    return False

def validate_timeframe(timeframe):
    """Validate the timeframe input."""
    valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]
    return timeframe.upper() in valid_timeframes

def prompt_for_metadata():
    while True:
        symbol = input("Enter symbol (e.g. EURUSD): ").strip().upper()
        if validate_symbol(symbol):
            break
        print("Invalid symbol format. Please enter a valid symbol (e.g., EURUSD).")

    while True:
        timeframe = input("Enter timeframe (e.g. M15): ").strip().upper()
        if validate_timeframe(timeframe):
            break
        print("Invalid timeframe. Please enter a valid timeframe (e.g., M15).")

    while True:
        is_start_raw = input("Enter IS (in-sample) start date (YYYY-MM-DD or YYYY/MM/DD): ").strip()
        is_start_mt5, is_start_dt = parse_and_format_date(is_start_raw)
        if is_start_mt5:
            break
        print("Invalid date format. Please try again.")

    while True:
        is_end_raw = input("Enter IS (in-sample) end date (YYYY-MM-DD or YYYY/MM/DD): ").strip()
        is_end_mt5, is_end_dt = parse_and_format_date(is_end_raw)
        if is_end_mt5:
            break
        print("Invalid date format. Please try again.")

    # Calculate OOS start as day after IS end
    oos_start_dt = is_end_dt + timedelta(days=1)
    oos_start_mt5 = oos_start_dt.strftime("%Y.%m.%d")

    while True:
        oos_end_raw = input(f"Enter OOS (out-of-sample) end date (YYYY-MM-DD or YYYY/MM/DD), OOS start is {oos_start_mt5}: ").strip()
        oos_end_mt5, oos_end_dt = parse_and_format_date(oos_end_raw)
        if oos_end_mt5:
            break
        print("Invalid date format. Please try again.")

    return symbol, timeframe, is_start_mt5, is_end_mt5, oos_start_mt5, oos_end_mt5

def cleanup_old_csvs(directory):
    for f in os.listdir(directory):
        if f.endswith('.csv'):
            try:
                os.remove(os.path.join(directory, f))
            except Exception as e:
                logging.warning(f"Could not delete {f}: {e}")

def to_mt5_date(date_str):
    # Accepts 'YYYY-MM-DD' or 'YYYY/MM/DD' and returns 'YYYY.MM.DD'
    return date_str.replace('-', '.').replace('/', '.')

def main():
    log_path = setup_logging()
    ensure_dir(CSV_OUTPUT_DIR)
    cleanup_old_csvs(CSV_OUTPUT_DIR)
    try:
        xml_path = find_latest_xml(RAW_XML_DIR)
        logging.info(f"Converting latest XML: {os.path.basename(xml_path)}")
    except Exception as e:
        logging.error(f"Error finding latest XML: {e}")
        print(f"❌ {e}")
        return
    try:
        symbol, timeframe, is_start_mt5, is_end_mt5, oos_start_mt5, oos_end_mt5 = prompt_for_metadata()
        df = parse_mt5_excel_xml(xml_path)
        if df.empty:
            logging.warning("No data found in XML file.")
            print("❌ No data found in XML file.")
            return
        df = calculate_metrics(df)
        # Add metadata columns in MT5 format
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        df['is_start'] = is_start_mt5
        df['is_end'] = is_end_mt5
        df['oos_start'] = oos_start_mt5
        df['oos_end'] = oos_end_mt5
        # Construct filename using only symbol and timeframe
        basename = f"{symbol}_{timeframe}_optimization.csv"
        csv_path = os.path.join(CSV_OUTPUT_DIR, basename)
        df.to_csv(csv_path, index=False)
        logging.info(f"Saved converted CSV to: {csv_path}")
        print(f"✅ Saved converted CSV to: {csv_path}")
        print(f"Log file: {log_path}")
    except Exception as e:
        logging.error(f"Error during XML to CSV conversion: {e}")
        print(f"❌ {e}")

if __name__ == "__main__":
    main()
