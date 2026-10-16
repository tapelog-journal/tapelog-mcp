"""Parse broker CSV exports, rebuild round trips, compute stats and behavioral patterns.
Descriptive analysis of the user's own past trades only. No market data, no signals, no advice."""
from __future__ import annotations
import csv, io, json, os, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timedelta
from collections import defaultdict
from statistics import mean
from . import DISCLAIMER

@dataclass
class Fill:
    dt: datetime
    symbol: str
    side: str      # "B" buy or "S" sell
    qty: float
    price: float
    fees: float = 0.0

@dataclass
class Trip:
    symbol: str
    direction: str  # long/short
    open_dt: datetime
    close_dt: datetime
    qty: float      # max position size (shares)
    entry_value: float  # max $ exposure
    pnl: float
    fees: float
    @property
    def hold_minutes(self): return (self.close_dt - self.open_dt).total_seconds() / 60
    def to_dict(self):
        d = asdict(self); d["open_dt"] = self.open_dt.isoformat(); d["close_dt"] = self.close_dt.isoformat()
        d["pnl"] = round(self.pnl, 2); d["hold_minutes"] = round(self.hold_minutes, 1); return d

def _num(s):
    s = (s or "").strip().replace("$", "").replace(",", "")
    if not s: return 0.0
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()")); return -v if neg else v

def detect_format(text: str) -> str:
    head = text.lstrip("\ufeff").splitlines()[0].lower() if text.strip() else ""
    cols = [c.strip().strip('"') for c in head.split(",")]
    if "symb" in cols and "side" in cols: return "das"
    if "trans code" in head and "activity date" in head: return "robinhood"
    if "symbol" in cols and "side" in cols: return "generic"
    raise ValueError("Unrecognized CSV. Supported: DAS Trader Trades window, Robinhood activity report, "
                     "or generic CSV with date,time,symbol,side,qty,price[,fees].")

def parse_csv(text: str, fmt: str = "auto", trade_date: str | None = None) -> list[Fill]:
    text = text.lstrip("\ufeff")
    fmt = detect_format(text) if fmt == "auto" else fmt
    rows = list(csv.DictReader(io.StringIO(text)))
    fills: list[Fill] = []
    if fmt == "das":
        d = date.fromisoformat(trade_date) if trade_date else date.today()
        for r in rows:
            side = r["Side"].strip().upper()
            if side not in ("B", "S", "SS", "BC"): continue
            t = datetime.strptime(r["Time"].strip(), "%H:%M:%S").time()
            fills.append(Fill(datetime.combine(d, t), r["Symb"].strip().upper(),
                              "B" if side in ("B", "BC") else "S", _num(r["Qty"]), _num(r["Price"]), _num(r.get("EcnFees"))))
    elif fmt == "robinhood":
        # newest first, no time of day: reverse and space fills 1 minute apart to keep order
        for i, r in enumerate(reversed(rows)):
            code = r["Trans Code"].strip().lower()
            if code not in ("buy", "sell") or not r["Instrument"].strip(): continue
            d = datetime.strptime(r["Activity Date"].strip(), "%m/%d/%Y")
            qty, px = _num(r["Quantity"]), _num(r["Price"])
            gross = qty * px
            fee = max(0.0, (gross - _num(r["Amount"])) if code == "sell" else (-_num(r["Amount"]) - gross))
            fills.append(Fill(d.replace(hour=9, minute=30) + timedelta(seconds=i), r["Instrument"].strip().upper(),
                              "B" if code == "buy" else "S", qty, px, round(fee, 4)))
    elif fmt == "generic":
        for r in rows:
            r = {k.strip().lower(): v for k, v in r.items()}
            side = r["side"].strip().upper()
            dt = datetime.fromisoformat(f'{r["date"].strip()} {r.get("time", "09:30:00").strip() or "09:30:00"}')
            fills.append(Fill(dt, r["symbol"].strip().upper(), "B" if side in ("B", "BUY", "BC", "BTC") else "S",
                              _num(r["qty"]), _num(r["price"]), _num(r.get("fees"))))
    else:
        raise ValueError(f"unknown format {fmt}")
    fills.sort(key=lambda f: f.dt)
    return fills

def build_trips(fills: list[Fill]) -> list[Trip]:
    """A round trip starts when a symbol goes from flat to a position and ends when it returns to flat."""
    trips, state = [], {}
    for f in sorted(fills, key=lambda f: f.dt):
        signed = f.qty if f.side == "B" else -f.qty
        remaining = signed
        while abs(remaining) > 1e-9:
            s = state.get(f.symbol)
            if s is None:
                s = state[f.symbol] = dict(pos=0.0, cash=0.0, fees=0.0, open=f.dt, maxq=0.0, maxval=0.0,
                                         dir="long" if remaining > 0 else "short")
            pos = s["pos"]
            # portion that closes (opposite sign) is capped at |pos|
            if pos != 0 and (pos > 0) != (remaining > 0):
                part = -pos if abs(remaining) > abs(pos) else remaining
            else:
                part = remaining
            frac = abs(part) / f.qty if f.qty else 0
            s["pos"] += part; s["cash"] -= part * f.price; s["fees"] += f.fees * frac
            s["maxq"] = max(s["maxq"], abs(s["pos"])); s["maxval"] = max(s["maxval"], abs(s["pos"]) * f.price)
            remaining -= part
            if abs(s["pos"]) < 1e-9:
                trips.append(Trip(f.symbol, s["dir"], s["open"], f.dt, s["maxq"], round(s["maxval"], 2),
                                  s["cash"] - s["fees"], round(s["fees"], 4)))
                del state[f.symbol]
    return sorted(trips, key=lambda t: t.close_dt)

# ---------- stats ----------
def stats(trips: list[Trip]) -> dict:
    if not trips: return {"trades": 0, "note": "No closed round trips in range."}
    pnls = [t.pnl for t in trips]
    wins = [p for p in pnls if p > 0]; losses = [p for p in pnls if p < 0]
    eq, peak, mdd = 0.0, 0.0, 0.0
    for p in pnls:
        eq += p; peak = max(peak, eq); mdd = max(mdd, peak - eq)
    gl = -sum(losses)
    streak = cur = 0
    for p in pnls:
        cur = cur + 1 if p < 0 else 0; streak = max(streak, cur)
    return {
        "trades": len(trips), "net_pnl": round(sum(pnls), 2), "total_fees": round(sum(t.fees for t in trips), 2),
        "win_rate_pct": round(100 * len(wins) / len(pnls), 1),
        "avg_win": round(mean(wins), 2) if wins else 0.0, "avg_loss": round(mean(losses), 2) if losses else 0.0,
        "payoff_ratio": round(mean(wins) / -mean(losses), 2) if wins and losses else None,
        "profit_factor": round(sum(wins) / gl, 2) if gl else None,
        "expectancy_per_trade": round(mean(pnls), 2),
        "max_drawdown": round(mdd, 2), "longest_losing_streak": streak,
        "largest_win": round(max(pnls), 2), "largest_loss": round(min(pnls), 2),
        "avg_hold_minutes": round(mean(t.hold_minutes for t in trips), 1),
        "pdt": pdt_count(trips),
    }

def pdt_count(trips: list[Trip], as_of: date | None = None) -> dict:
    """Day trades = round trips opened and closed on the same calendar day. Rolling 5 business days."""
    days = defaultdict(int)
    for t in trips:
        if t.open_dt.date() == t.close_dt.date(): days[t.close_dt.date()] += 1
    as_of = as_of or (max(t.close_dt.date() for t in trips) if trips else date.today())
    window, d = [], as_of
    while len(window) < 5:
        if d.weekday() < 5: window.append(d)
        d -= timedelta(days=1)
    return {"as_of": as_of.isoformat(), "day_trades_last_5_business_days": sum(days[x] for x in window),
            "note": "Record-keeping count only. FINRA approved replacing the PDT rule effective June 4, 2026 with broker "
                    "phase-in through Oct 20, 2027; check your broker's current rules."}

# ---------- leak finder ----------
MIN_N = 3
def _bucket_hour(t): h = t.open_dt.hour; m = t.open_dt.minute
def _grp(trips, keyfn):
    g = defaultdict(list)
    for t in trips: g[keyfn(t)].append(t.pnl)
    return {k: v for k, v in g.items()}

def _time_bucket(t):
    m = t.open_dt.hour * 60 + t.open_dt.minute
    if m < 9*60+30: return "pre-market"
    if m < 10*60: return "09:30-10:00"
    if m < 11*60: return "10:00-11:00"
    if m < 12*60: return "11:00-12:00"
    if m < 14*60: return "12:00-14:00"
    if m < 16*60: return "14:00-16:00"
    return "after-hours"

def _hold_bucket(t):
    h = t.hold_minutes
    return "<2 min" if h < 2 else "2-10 min" if h < 10 else "10-30 min" if h < 30 else "30-120 min" if h < 120 else ">2 hours (incl. multi-day)"

def _table(groups):
    return [{"group": k, "trades": len(v), "net_pnl": round(sum(v), 2), "avg_pnl": round(mean(v), 2),
             "win_rate_pct": round(100*sum(p > 0 for p in v)/len(v), 1)} for k, v in sorted(groups.items(), key=lambda kv: sum(kv[1]))]

def _describe(dim, rows, total):
    out = []
    for r in rows:
        if r["trades"] < MIN_N: continue
        if r["net_pnl"] < 0 and (total >= 0 or r["net_pnl"] < total * 0.5 if total < 0 else True):
            out.append({"dimension": dim, "group": r["group"], "severity": round(-r["net_pnl"], 2),
                        "finding": f'Your {r["trades"]} trades in "{r["group"]}" ({dim}) netted ${r["net_pnl"]:,.2f} '
                                   f'(avg ${r["avg_pnl"]:,.2f}, win rate {r["win_rate_pct"]}%).'})
    return out

def find_leaks(trips: list[Trip]) -> dict:
    if len(trips) < 5:
        return {"findings": [], "note": "Need at least 5 closed round trips for pattern analysis.", "disclaimer": DISCLAIMER}
    total = sum(t.pnl for t in trips)
    dims = {"time of day (entry)": _time_bucket, "day of week": lambda t: t.open_dt.strftime("%A"),
            "hold time": _hold_bucket, "symbol": lambda t: t.symbol, "direction": lambda t: t.direction}
    tables, findings = {}, []
    for name, fn in dims.items():
        tables[name] = _table(_grp(trips, fn)); findings += _describe(name, tables[name], total)
    # after-loss behavior: size and result of the next trade the same day
    after_loss, after_other, sizes_al, sizes_other = [], [], [], []
    for prev, nxt in zip(trips, trips[1:]):
        if nxt.open_dt.date() != prev.close_dt.date() or nxt.open_dt < prev.close_dt: continue
        if prev.pnl < 0: after_loss.append(nxt.pnl); sizes_al.append(nxt.entry_value)
        else: after_other.append(nxt.pnl); sizes_other.append(nxt.entry_value)
    al = None
    if len(after_loss) >= MIN_N and sizes_other:
        al = {"trades_after_a_loss": len(after_loss), "avg_pnl_after_loss": round(mean(after_loss), 2),
              "avg_pnl_other": round(mean(after_other), 2) if after_other else None,
              "avg_size_after_loss": round(mean(sizes_al), 2), "avg_size_other": round(mean(sizes_other), 2)}
        ratio = mean(sizes_al) / mean(sizes_other) if mean(sizes_other) else 1
        if ratio > 1.2 or mean(after_loss) < 0:
            findings.append({"dimension": "after-loss behavior", "group": "next trade after a loss",
                             "severity": round(max(0, -sum(after_loss)), 2) + (1 if ratio > 1.2 else 0),
                             "finding": f"On trades taken right after a losing trade the same day, your average position was "
                                        f"${mean(sizes_al):,.0f} vs ${mean(sizes_other):,.0f} otherwise ({ratio:.1f}x), and those "
                                        f"{len(after_loss)} trades averaged ${mean(after_loss):,.2f}."})
    # losers held longer than winners
    w = [t.hold_minutes for t in trips if t.pnl > 0]; l = [t.hold_minutes for t in trips if t.pnl < 0]
    hold = None
    if len(w) >= MIN_N and len(l) >= MIN_N:
        hold = {"avg_hold_winners_min": round(mean(w), 1), "avg_hold_losers_min": round(mean(l), 1)}
        if mean(l) > 1.5 * mean(w):
            findings.append({"dimension": "hold time", "group": "losers vs winners", "severity": 0.5,
                             "finding": f"Your losing trades were held {mean(l):.1f} min on average vs {mean(w):.1f} min for winners."})
    findings.sort(key=lambda f: -f["severity"])
    return {"trades_analyzed": len(trips), "net_pnl": round(total, 2), "findings": findings,
            "breakdowns": tables, "after_loss": al, "hold_times": hold,
            "framing": "Descriptive observations about your own past trades. Sample sizes are small; patterns may be noise. "
                       "Use them as prompts for reflecting on your process, not as trading signals.",
            "disclaimer": DISCLAIMER}

def filter_range(trips, start=None, end=None):
    s = date.fromisoformat(start) if start else date.min; e = date.fromisoformat(end) if end else date.max
    return [t for t in trips if s <= t.close_dt.date() <= e]

def compare_periods(trips, a_start, a_end, b_start, b_end):
    A, B = stats(filter_range(trips, a_start, a_end)), stats(filter_range(trips, b_start, b_end))
    delta = {}
    for k, v in A.items():
        if isinstance(v, (int, float)) and isinstance(B.get(k), (int, float)) and not isinstance(v, bool):
            delta[k] = round(B[k] - v, 2)
    return {"period_a": {"start": a_start, "end": a_end, **A}, "period_b": {"start": b_start, "end": b_end, **B},
            "change_b_minus_a": delta, "disclaimer": DISCLAIMER}

# ---------- local store ----------
class Store:
    def __init__(self, path=None):
        self.path = path or os.environ.get("TAPELOG_DATA", os.path.expanduser("~/.tapelog/fills.json"))
        self.fills: list[Fill] = []
        if self.path != ":memory:" and os.path.exists(self.path):
            with open(self.path) as fh:
                for d in json.load(fh):
                    d["dt"] = datetime.fromisoformat(d["dt"]); self.fills.append(Fill(**d))
    def add(self, new):
        key = lambda f: (f.dt.isoformat(), f.symbol, f.side, f.qty, f.price)
        seen = {key(f) for f in self.fills}; added = [f for f in new if key(f) not in seen]
        self.fills += added; self.save(); return len(added), len(new) - len(added)
    def clear(self): self.fills = []; self.save()
    def save(self):
        if self.path == ":memory:": return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as fh:
            json.dump([{**asdict(f), "dt": f.dt.isoformat()} for f in self.fills], fh)
    def trips(self): return build_trips(self.fills)
