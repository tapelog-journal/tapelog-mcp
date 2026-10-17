"""Weekly habit report: compares this week's behavior with prior weeks, using the user's own stored fills.
Descriptive counts only. No market data, no signals, no advice."""
from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from . import DISCLAIMER
from .core import Trip, _time_bucket

SHORT_DISCLAIMER = "Educational, not investment advice."
BURST_WINDOW_MIN, BURST_MIN_TRADES, SIZE_UP_RATIO = 15, 3, 1.2

HABITS = {
    "size_up_after_loss": "Size-up after a loss",
    "losers_held_longer": "Losers held longer than winners",
    "overtrading_burst": "Overtrading bursts",
    "time_of_day_slump": "Time-of-day slump",
}

def week_start(d: date) -> date: return d - timedelta(days=d.weekday())

def _size_up(trips, base_size):
    n = 0
    for prev, nxt in zip(trips, trips[1:]):
        if (prev.pnl < 0 and nxt.open_dt.date() == prev.close_dt.date() and nxt.open_dt >= prev.close_dt
                and base_size and nxt.entry_value > SIZE_UP_RATIO * base_size):
            n += 1
    return n

def _losers_longer(trips, ref_win_hold):
    w = [t.hold_minutes for t in trips if t.pnl > 0]
    ref = mean(w) if w else ref_win_hold
    if not ref: return 0
    return sum(1 for t in trips if t.pnl < 0 and t.hold_minutes > ref)

def _bursts(trips):
    opens = sorted(t.open_dt for t in trips); n, i = 0, 0
    while i < len(opens):
        j = i
        while j + 1 < len(opens) and (opens[j + 1] - opens[i]).total_seconds() <= BURST_WINDOW_MIN * 60: j += 1
        if j - i + 1 >= BURST_MIN_TRADES: n += 1; i = j + 1
        else: i += 1
    return n

def _slump(trips):
    g = defaultdict(list)
    for t in trips: g[_time_bucket(t)].append(t)
    worst, cnt = None, 0
    for b, ts in g.items():
        losers = sum(t.pnl < 0 for t in ts); net = sum(t.pnl for t in ts)
        if len(ts) >= 3 and net < 0 and losers >= 2 and (worst is None or net < worst[1]):
            worst, cnt = (b, net), losers
    return cnt, (worst[0] if worst else None)

def week_counts(trips, base_size, ref_win_hold):
    trips = sorted(trips, key=lambda t: t.open_dt)
    slump, bucket = _slump(trips)
    return {"trades": len(trips), "net_pnl": round(sum(t.pnl for t in trips), 2),
            "size_up_after_loss": _size_up(trips, base_size), "losers_held_longer": _losers_longer(trips, ref_win_hold),
            "overtrading_burst": _bursts(trips), "time_of_day_slump": slump, "slump_window": bucket}

def _detail(key, wk):
    return {"size_up_after_loss": f"next trade after a same-day loss was over {SIZE_UP_RATIO}x the usual position size",
            "losers_held_longer": "losing trade held longer than the average winning trade",
            "overtrading_burst": f"{BURST_MIN_TRADES}+ trades opened within {BURST_WINDOW_MIN} minutes",
            "time_of_day_slump": f"losing trades in the weakest entry window ({wk.get('slump_window') or 'n/a'})"}[key]

def _times(n): return "1 time" if n == 1 else f"{n} times"

def weekly_habit_report(trips: list[Trip], as_of: str | None = None, prior_weeks: int = 4) -> dict:
    if not trips:
        return {"note": "No closed round trips stored yet.", "disclaimer": DISCLAIMER}
    end = date.fromisoformat(as_of) if as_of else max(t.close_dt.date() for t in trips)
    this_ws = week_start(end)
    weeks = defaultdict(list)
    for t in trips:
        ws = week_start(t.close_dt.date())
        if this_ws - timedelta(weeks=prior_weeks) <= ws <= this_ws and t.close_dt.date() <= end: weeks[ws].append(t)
    cur = weeks.get(this_ws, [])
    prior_keys = sorted(k for k in weeks if k < this_ws)
    prior_trips = [t for k in prior_keys for t in weeks[k]]
    base = median([t.entry_value for t in (prior_trips or cur)]) if (prior_trips or cur) else 0
    pw = [t.hold_minutes for t in prior_trips if t.pnl > 0]
    ref = mean(pw) if pw else 0
    this = week_counts(cur, base, ref)
    prior = {k.isoformat(): week_counts(weeks[k], base, ref) for k in prior_keys}
    appeared, faded, steady = [], [], []
    for key, label in HABITS.items():
        now = this[key]; avg = round(mean(p[key] for p in prior.values()), 1) if prior else 0.0
        item = {"habit": key, "label": label, "this_week": now, "prior_weekly_avg": avg, "detail": _detail(key, this)}
        if not prior:
            if now: item["summary"] = f"{label}: this showed up {_times(now)} this week ({item['detail']})."; appeared.append(item)
            continue
        if now >= 1 and now >= max(1.0, 1.5 * avg) and now > avg:
            item["summary"] = f"{label}: this showed up {_times(now)} this week vs {avg} per week before ({item['detail']})."
            appeared.append(item)
        elif avg >= 1 and now <= avg / 2:
            item["summary"] = f"{label}: showed up {_times(now)} this week vs {avg} per week before."
            faded.append(item)
        elif now or avg:
            item["summary"] = f"{label}: {_times(now)} this week vs {avg} per week before (about the same)."
            steady.append(item)
    return {"week_of": this_ws.isoformat(), "as_of": end.isoformat(), "prior_weeks_compared": len(prior),
            "this_week": this, "prior_weeks": prior, "appeared": appeared, "faded": faded, "steady": steady,
            "framing": "Counts of your own past behavior only. Small samples can be noise. "
                       "Use them as prompts for reflection, not as trading signals.",
            "disclaimer": DISCLAIMER}

def render_markdown(r: dict, title: str = "TapeLog weekly habit report") -> str:
    if "week_of" not in r: return f"# {title}\n\n{r.get('note','')}\n\n*{SHORT_DISCLAIMER}*\n"
    t = r["this_week"]; L = [f"# {title}", "", f"**Week of {r['week_of']}** (data through {r['as_of']}), "
         f"compared with {r['prior_weeks_compared']} prior week(s).", "",
         f"This week: {t['trades']} closed trades, net ${t['net_pnl']:,.2f}.", ""]
    for head, key, empty in (("Habits that appeared", "appeared", "None this week."),
                             ("Habits that faded", "faded", "None this week."),
                             ("About the same", "steady", "Nothing else to note.")):
        L += [f"## {head}", ""] + ([f"- {i['summary']}" for i in r[key]] or [empty]) + [""]
    L += ["## Week by week", "", "| Week of | Trades | Size-up after loss | Losers held longer | Overtrading bursts | Time-of-day slump |",
          "|---|---|---|---|---|---|"]
    for wk, c in list(r["prior_weeks"].items()) + [(r["week_of"] + " (this week)", t)]:
        L.append(f"| {wk} | {c['trades']} | {c['size_up_after_loss']} | {c['losers_held_longer']} | {c['overtrading_burst']} | {c['time_of_day_slump']} |")
    L += ["", f"_{r['framing']}_", "", f"**{SHORT_DISCLAIMER}** {r['disclaimer']}", ""]
    return "\n".join(L)
