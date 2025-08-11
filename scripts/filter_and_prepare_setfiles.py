import sys
import os
import argparse
import pandas as pd
import logging
from datetime import datetime
import tqdm
# Ensure parent directory is in sys.path before any local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.setfile_generator import save_setfile

# --- Logging setup ---
def setup_logging():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_filename = f"filter_and_prepare_setfiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

# --- Command-line arguments ---
def parse_args():
    parser = argparse.ArgumentParser(description="Filter and prepare MT5 setfiles from optimization results.")
    parser.add_argument('--template', type=str, default='gold_template.set', help='Path to the setfile template')
    parser.add_argument('--csvdir', type=str, default='processed_csv', help='Directory containing optimization CSVs')
    parser.add_argument('--setfiledir', type=str, default='setfiles', help='Directory to save setfiles')
    parser.add_argument('--mt5dir', type=str, default='C:/MT5_Backtest/MQL5/Profiles/Tester', help='MT5 setfile directory')
    parser.add_argument('--resultsdir', type=str, default='results', help='Directory to save survivor log')
    # Relaxed filter thresholds for first filtering
    parser.add_argument('--recoveryfactor', type=float, default=2, help='Minimum recovery factor (first filter)')
    parser.add_argument('--profitfactor', type=float, default=1.2, help='Minimum profit factor (first filter)')
    parser.add_argument('--expectedpayoff', type=float, default=0, help='Minimum expected payoff (first filter)')
    parser.add_argument('--sharperatio', type=float, default=0.5, help='Minimum Sharpe ratio (first filter)')
    parser.add_argument('--winrate', type=float, default=50, help='Minimum winrate percent (first filter)')
    parser.add_argument('--maxdrawdown', type=float, default=50, help='Maximum allowed drawdown (percent, first filter)')
    parser.add_argument('--trades', type=int, default=50, help='Minimum number of trades (first filter)')
    return parser.parse_args()

# --- Template loader ---
def load_template_setfile(template_path):
    # Returns a list of (key, value) pairs in order, and a lowercase key map
    params = []
    key_map = {}
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(template_path, 'r', encoding='utf-16') as f:
            lines = f.readlines()
    for line in lines:
        if '=' in line and not line.strip().startswith(';'):
            k, v = line.split('=', 1)
            k_clean = k.strip()
            v_clean = v.strip().split('||')[0]
            params.append((k_clean, v_clean))
            key_map[k_clean.lower()] = k_clean
    return params, key_map

# --- CSV loader ---
def get_latest_csv(folder):
    files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {folder}")
    latest = max(files, key=lambda x: os.path.getmtime(os.path.join(folder, x)))
    return os.path.join(folder, latest)

# --- Filtering ---
def apply_filters(df, args):
    filters = pd.Series([True] * len(df))
    filter_map = [
        ('recoveryfactor', 'recoveryfactor', '>=', args.recoveryfactor),
        ('profitfactor', 'profitfactor', '>=', args.profitfactor),
        ('expectedpayoff', 'expectedpayoff', '>', args.expectedpayoff),
        ('sharperatio', 'sharperatio', '>', args.sharperatio),
        ('winrate', 'winrate', '>=', args.winrate),
        # maxdrawdown is in percent
        ('maxdrawdown', 'maxdrawdown', '<=', args.maxdrawdown),
        ('trades', 'trades', '>=', args.trades),
    ]
    for col, name, op, val in filter_map:
        if col in df.columns:
            if op == '>=':
                filters &= (df[col] >= val)
            elif op == '>':
                filters &= (df[col] > val)
            elif op == '<=':
                filters &= (df[col] <= val)
            elif op == '<':
                filters &= (df[col] < val)
        else:
            logging.warning(f"Column '{col}' not found in CSV. Skipping this filter.")
    return df[filters].reset_index(drop=True)

def cleanup_old_setfiles(directory):
    for f in os.listdir(directory):
        if f.endswith('.set'):
            file_path = os.path.join(directory, f)
            try:
                os.remove(file_path)
                logging.info(f"Deleted old setfile: {file_path}")
            except Exception as e:
                logging.warning(f"Could not delete {f} in {directory}: {e}")

def validate_setfiles(setfile_dir):
    import os
    print("Validating setfiles...")
    for setfile in os.listdir(setfile_dir):
        if not setfile.endswith(".set"):
            print(f"Invalid setfile: {setfile}")
            continue
        print(f"Valid setfile: {setfile}")

# --- Main logic ---
def main():
    log_path = setup_logging()
    args = parse_args()
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    CSV_INPUT = os.path.join(BASE_DIR, args.csvdir)
    SETFILE_OUTPUT = os.path.join(BASE_DIR, args.setfiledir)
    MT5_SETFILE_PATH = args.mt5dir
    RESULTS_FOLDER = os.path.join(BASE_DIR, args.resultsdir)
    SURVIVOR_LOG = os.path.join(RESULTS_FOLDER, 'survivors_list.csv')
    TEMPLATE_PATH = os.path.join(BASE_DIR, args.template)

    # Ensure all output folders exist
    for folder in [RESULTS_FOLDER, SETFILE_OUTPUT, MT5_SETFILE_PATH]:
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            logging.error(f"Could not create folder {folder}: {e}")

    # Clean up old setfiles before generating new ones
    cleanup_old_setfiles(SETFILE_OUTPUT)
    cleanup_old_setfiles(MT5_SETFILE_PATH)

    try:
        csv_path = get_latest_csv(CSV_INPUT)
        logging.info(f"Using optimization CSV: {os.path.basename(csv_path)}")
    except Exception as e:
        logging.error(e)
        return

    try:
        df = pd.read_csv(csv_path)
        # --- Column normalization ---
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        logging.error(f"Could not read CSV: {e}")
        return

    df_filtered = apply_filters(df, args)

    if df_filtered.empty:
        logging.warning("No setfiles passed Phase 1 filtering.")
        return

    template_params, template_key_map = load_template_setfile(TEMPLATE_PATH)
    survivors = []
    setfile_count = 0
    error_count = 0
    for i, row in tqdm.tqdm(list(df_filtered.iterrows()), desc="Generating setfiles", unit="setfile"):
        symbol = row.get('symbol', f'no_symbol_{i}')
        timeframe = row.get('timeframe', 'M15')
        filename = f"{symbol}_{timeframe}_set_{i+1:03}.set"

        # Build a dict of updated values (lowercase for matching)
        row_dict = {str(k).lower(): v for k, v in row.items()}
        # Prepare ordered param list for output
        output_params = []
        for k, v in template_params:
            v_out = row_dict.get(k.lower(), v)
            output_params.append((k, v_out))
        # Save setfile using ordered param list
        for out_path in [SETFILE_OUTPUT, MT5_SETFILE_PATH]:
            try:
                save_setfile(os.path.join(out_path, filename), dict(output_params))
                setfile_count += 1
                logging.info(f"Saved setfile: {os.path.join(out_path, filename)} | Updated: {', '.join([k for k, v in output_params if row_dict.get(k.lower(), None) is not None and row_dict.get(k.lower()) != v])}")
            except Exception as e:
                logging.error(f"Could not save setfile to {out_path}: {e}")
                error_count += 1

        survivors.append({
            "filename": filename,
            **row.to_dict()
        })

    try:
        pd.DataFrame(survivors).to_csv(SURVIVOR_LOG, index=False)
        logging.info(f"Done. Saved {setfile_count} .set files to:\n- {SETFILE_OUTPUT}\n- {MT5_SETFILE_PATH}")
        logging.info(f"Survivor log saved to: {SURVIVOR_LOG}")
        logging.info(f"Summary: {len(survivors)} survivors, {setfile_count} setfiles created, {error_count} errors.")
        print(f"✅ Done. Saved {setfile_count} .set files to:\n- {SETFILE_OUTPUT}\n- {MT5_SETFILE_PATH}")
        print(f"📝 Survivor log saved to: {SURVIVOR_LOG}")
        print(f"Summary: {len(survivors)} survivors, {setfile_count} setfiles created, {error_count} errors.")
        print(f"Log file: {log_path}")
    except Exception as e:
        logging.error(f"Could not save survivor log: {e}")

if __name__ == "__main__":
    main()
    validate_setfiles("C:\\EA_Validation_Project\\setfiles\\")
