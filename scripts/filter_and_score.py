import os
import re
import sys
from openai_client import score_equity_curve

reports_dir = r"C:\EA_Validation_Project\test_reports"
survivors_dir = r"C:\EA_Validation_Project\survivors"
os.makedirs(survivors_dir, exist_ok=True)

# Check gpt_mode from command line
gpt_mode = "--gpt_mode" in sys.argv and sys.argv[sys.argv.index("--gpt_mode") + 1].lower() == "on"

def extract_metrics(html):
    def grab(label):
        match = re.search(rf"{label}.*?>(.*?)</td>", html)
        return float(match.group(1).replace("$", "").replace(",", "")) if match else None
    return {
        "Net Profit": grab("Net profit"),
        "Sharpe Ratio": grab("Sharpe ratio"),
        "Drawdown": grab("Maximal drawdown")
    }

results = []
for fname in os.listdir(reports_dir):
    if not fname.endswith(".html"): continue
    with open(os.path.join(reports_dir, fname), encoding="utf-8") as f:
        html = f.read()
    metrics = extract_metrics(html)
    if all(metrics.values()):
        if metrics["Net Profit"] > 0 and metrics["Sharpe Ratio"] > 1 and metrics["Drawdown"] < 100:
            results.append((fname, metrics))

if not results:
    print("⚠️ No survivors. Retrying with Drawdown < 150...")
    for fname in os.listdir(reports_dir):
        with open(os.path.join(reports_dir, fname), encoding="utf-8") as f:
            html = f.read()
        metrics = extract_metrics(html)
        if metrics["Net Profit"] > 0 and metrics["Drawdown"] < 150:
            results.append((fname, metrics))

top_5 = sorted(results, key=lambda x: x[1]["Sharpe Ratio"], reverse=True)[:5]
for fname, metrics in top_5:
    src = os.path.join(reports_dir, fname)
    dst = os.path.join(survivors_dir, fname)
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        fdst.write(fsrc.read())
    comment = score_equity_curve(fname) if gpt_mode else "GPT disabled in dry run"
    print(f"📊 {fname} passed — GPT Comment: {comment}")

if not top_5:
    print("❌ No viable survivors. Try different symbol or relax filters.")
else:
    print(f"✅ Saved top {len(top_5)} survivors to /survivors/")