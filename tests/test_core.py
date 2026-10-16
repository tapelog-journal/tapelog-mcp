from pathlib import Path
import re
from tapelog_mcp import core, DISCLAIMER
S = Path(__file__).parent.parent / "samples"
rd = lambda n: (S / n).read_text(encoding="utf-8-sig")

def test_das_roundtrips():
    f = core.parse_csv(rd("SAMPLE_das_trader_trades_window.csv"), trade_date="2026-10-15")
    t = core.build_trips(f)
    assert [x.symbol for x in t] == ["AMD", "SOFI", "TSLA", "NVDA", "AMD"]  # PLTR still open
    amd = t[0]; assert amd.qty == 300
    assert round(amd.pnl, 2) == round(150*164.05 + 150*163.7 - 200*162.4 - 100*162.55 - 4.0, 2)
    tsla = [x for x in t if x.symbol == "TSLA"][0]
    assert tsla.direction == "short" and round(tsla.pnl, 2) == round((251.3-249.1)*50 - 2, 2)

def test_robinhood():
    t = core.build_trips(core.parse_csv(rd("SAMPLE_robinhood_activity_report.csv")))
    assert {x.symbol for x in t} == {"AMD", "SOFI", "NIO"} and len(t) == 4
    nio = [x for x in t if x.symbol == "NIO"][0]; assert round(nio.pnl, 2) == 74.95

def test_stats_and_pdt():
    s = core.stats(core.build_trips(core.parse_csv(rd("SAMPLE_das_trader_trades_window.csv"), trade_date="2026-10-15")))
    assert s["trades"] == 5 and s["win_rate_pct"] == 60.0
    assert s["pdt"]["day_trades_last_5_business_days"] == 5
    assert s["profit_factor"] and s["max_drawdown"] >= 0

def test_leaks_descriptive_no_advice():
    t = core.build_trips(core.parse_csv(rd("SAMPLE_generic_60_trades.csv")))
    assert len(t) == 60
    r = core.find_leaks(t)
    dims = {f["dimension"] for f in r["findings"]}
    assert "time of day (entry)" in dims and "after-loss behavior" in dims
    text = " ".join(f["finding"] for f in r["findings"]).lower()
    assert not re.search(r"\b(you should|buy|sell|short it|price target|recommend)\b", text)
    assert r["disclaimer"] == DISCLAIMER

def test_compare_and_store(tmp_path):
    st = core.Store(str(tmp_path / "f.json"))
    f = core.parse_csv(rd("SAMPLE_generic_60_trades.csv"))
    assert st.add(f) == (120, 0) and st.add(f) == (0, 120)
    assert len(core.Store(str(tmp_path / "f.json")).fills) == 120
    c = core.compare_periods(st.trips(), "2026-09-14", "2026-09-25", "2026-09-28", "2026-10-09")
    assert c["period_a"]["trades"] > 0 and "net_pnl" in c["change_b_minus_a"]
