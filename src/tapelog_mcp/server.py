"""TapeLog MCP server: local, private analysis of your own broker CSV exports."""
from __future__ import annotations
import os
try:  # mcp SDK 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp SDK 1.x
    from mcp.server.fastmcp import FastMCP
from . import DISCLAIMER, core

INSTRUCTIONS = ("TapeLog analyzes the user's OWN past trades (timing, sizing, hold times, discipline). "
    "Scope rule: never recommend buying, selling or holding any security, never give price targets, picks, signals "
    "or market predictions, and never tell the user to place a trade. Phrase results descriptively. " + DISCLAIMER)
mcp = FastMCP("tapelog", instructions=INSTRUCTIONS)
store = core.Store()

def _w(d): d = dict(d); d.setdefault("disclaimer", DISCLAIMER); return d

@mcp.tool()
def import_fills(csv_text: str = "", file_path: str = "", broker: str = "auto", trade_date: str = "") -> dict:
    """Import executions from a DAS Trader Trades-window CSV, a Robinhood account activity CSV, or a generic CSV
    (date,time,symbol,side,qty,price,fees). Pass csv_text or a local file_path. DAS exports have no date: pass trade_date
    (YYYY-MM-DD). Stored locally (~/.tapelog/fills.json); duplicates are skipped."""
    if file_path:
        with open(os.path.expanduser(file_path), encoding="utf-8-sig") as fh: csv_text = fh.read()
    if not csv_text: return {"error": "Provide csv_text or file_path."}
    fills = core.parse_csv(csv_text, broker, trade_date or None)
    added, dup = store.add(fills)
    return _w({"fills_parsed": len(fills), "added": added, "duplicates_skipped": dup,
               "total_fills": len(store.fills), "closed_round_trips": len(store.trips())})

@mcp.tool()
def get_stats(start: str = "", end: str = "") -> dict:
    """Stats for closed round trips (optionally between start/end YYYY-MM-DD): net P&L, win rate, profit factor,
    expectancy, average win/loss, max drawdown, losing streak, hold time, and PDT day-trade count."""
    return _w(core.stats(core.filter_range(store.trips(), start or None, end or None)))

@mcp.tool()
def find_leaks(start: str = "", end: str = "") -> dict:
    """Describe where the user's own past results were weakest: time of day, day of week, hold time, symbol,
    direction, sizing after a loss, and winners vs losers hold time. Descriptive findings only, never trade advice."""
    return core.find_leaks(core.filter_range(store.trips(), start or None, end or None))

@mcp.tool()
def compare_periods(a_start: str, a_end: str, b_start: str, b_end: str) -> dict:
    """Compare stats between period A and period B (YYYY-MM-DD dates), e.g. last week vs this week."""
    return core.compare_periods(store.trips(), a_start, a_end, b_start, b_end)

@mcp.tool()
def list_trades(start: str = "", end: str = "", limit: int = 50) -> dict:
    """List reconstructed round trips (most recent first)."""
    t = core.filter_range(store.trips(), start or None, end or None)[::-1][:limit]
    return _w({"trades": [x.to_dict() for x in t]})

@mcp.tool()
def clear_data(confirm: bool = False) -> dict:
    """Delete all locally stored fills. Requires confirm=true."""
    if not confirm: return {"error": "Pass confirm=true to delete all stored fills."}
    store.clear(); return {"cleared": True}

def main(): mcp.run()
if __name__ == "__main__": main()
