"""Build samples/SAMPLE_weekly_habit_fills.csv: SAMPLE DATA ONLY (synthetic, not a real trader).
This week (Thu 2026-10-15) = the TapeLog roast #1 sample DAS day. Three earlier synthetic weeks are calmer
(steady size, quick loss exits) but with a late-morning slump and afternoon overtrading bursts that fade by this week."""
import csv, random
from datetime import date, timedelta
from pathlib import Path
random.seed(11)
HERE = Path(__file__).parent
rows = []
for wk in range(3, 0, -1):
    monday = date(2026, 10, 12) - timedelta(weeks=wk)
    for dd in range(5):
        d = monday + timedelta(days=dd)
        slots = [(9, 40), (10, 25), (11, 15), (11, 45)]
        if wk > 1 and dd in (0, 3): slots += [(14, 2), (14, 8), (14, 14)]  # overtrading burst, earlier weeks only
        for h, m in slots:
            px = round(random.uniform(45, 55), 2)
            late = h in (11, 14) and wk > 1  # slump in earlier weeks, gone in the most recent prior week
            win = random.random() < (0.3 if late else 0.65)
            move = px * (0.006 if win else -0.004); hold = 6 if win else 4
            rows.append([d.isoformat(), f"{h:02d}:{m:02d}:00", "SMPL", "B", 100, px, 0.5])
            rows.append([d.isoformat(), f"{h:02d}:{m+hold:02d}:00", "SMPL", "S", 100, round(px + move, 2), 0.5])
for r in csv.DictReader(open(HERE / "SAMPLE_roast01_das_fills.csv")):
    rows.append(["2026-10-15", r["Time"], r["Symb"], r["Side"], r["Qty"], r["Price"], r["EcnFees"]])
with open(HERE / "SAMPLE_weekly_habit_fills.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "time", "symbol", "side", "qty", "price", "fees"]); w.writerows(rows)
