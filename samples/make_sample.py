"""Generate samples/SAMPLE_generic_60_trades.csv: deterministic synthetic fills with built-in patterns
(weak late-morning trades, larger size after losses). SAMPLE DATA ONLY."""
import random, csv
from datetime import date, timedelta
random.seed(7)
syms = ["AMD", "NVDA", "TSLA", "SOFI", "PLTR"]
rows, d, last_loss = [], date(2026, 9, 14), False
while len(rows) < 120:
    if d.weekday() < 5:
        for (h, m), sym in zip(sorted(random.sample([(9, 35), (9, 50), (10, 15), (11, 10), (11, 40), (14, 5)], 3)), random.sample(syms, 3)):
            px = round(random.uniform(20, 200), 2)
            qty = 200 if last_loss else 100
            edge = -0.004 if h == 11 else 0.003
            if d.weekday() == 4: edge -= 0.003
            move = px * (edge + random.gauss(0, 0.006))
            hold = random.choice([1, 4, 12, 25]) + (15 if move < 0 else 0)
            rows.append([d.isoformat(), f"{h:02d}:{m:02d}:00", sym, "B", qty, px, 1.0])
            rows.append([d.isoformat(), f"{h:02d}:{(m+hold)%60:02d}:00" if m+hold < 60 else f"{h+1:02d}:{(m+hold)-60:02d}:00", sym, "S", qty, round(px+move, 2), 1.0])
            last_loss = move < 0
    d += timedelta(days=1)
with open("samples/SAMPLE_generic_60_trades.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "time", "symbol", "side", "qty", "price", "fees"]); w.writerows(rows)
