import os
import csv
import re
from bs4 import BeautifulSoup

# Paths
REPORTS_FOLDER = r'C:\EA_Validation_Project\test_reports'
OUTPUT_CSV = r'C:\EA_Validation_Project\results\forward_test_results.csv'

# HTML tag patterns
METRICS_TO_EXTRACT = {
    "Setfile": lambda file: os.path.basename(file).replace(".html", ""),
    "Net Profit": r'Net profit.*?\$([\d,]+(?:\.\d+)?)',
    "Gross Profit": r'Gross profit.*?\$([\d,]+(?:\.\d+)?)',
    "Gross Loss": r'Gross loss.*?\$([\d,]+(?:\.\d+)?)',
    "Max Drawdown": r'Maximal drawdown.*?\$([\d,]+(?:\.\d+)?)',
    "Relative Drawdown": r'Relative drawdown.*?([\d.]+%)',
    "Expected Payoff": r'Expected payoff.*?\$([\d,]+(?:\.\d+)?)',
    "Profit Factor": r'Profit factor.*?([\d.]+)',
    "Recovery Factor": r'Recovery factor.*?([\d.]+)',
    "Sharpe Ratio": r'Sharpe ratio.*?([\d.]+)',
    "Win Rate": r'Profit trades.*?(\d+%)',
    "Trades": r'Total trades.*?([\d,]+)',
    "Consecutive Losses": r'Max consecutive losses.*?([\d]+)',
}

def clean_html_value(value):
    value = value.replace('\xa0', '').replace('%', '').replace(',', '')
    try:
        return float(value)
    except:
        return 0.0

def extract_metrics_from_html(html_file):
    metrics = {}
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        for key, pattern in METRICS_TO_EXTRACT.items():
            if callable(pattern):
                metrics[key] = pattern(html_file)
            else:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                metrics[key] = clean_html_value(match.group(1)) if match else 0.0
    return metrics

def extract_all_reports():
    results = []
    for file in os.listdir(REPORTS_FOLDER):
        if file.endswith('.html'):
            full_path = os.path.join(REPORTS_FOLDER, file)
            metrics = extract_metrics_from_html(full_path)
            results.append(metrics)
    if not results:
        print("⚠️ No HTML reports found.")
        return
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"✅ Extracted {len(results)} reports → {OUTPUT_CSV}")

if __name__ == "__main__":
    extract_all_reports()