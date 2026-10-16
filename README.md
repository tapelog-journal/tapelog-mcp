# TapeLog MCP: a private AI trade-journal coach

<!-- mcp-name: io.github.tapelog-journal/tapelog-mcp -->

An open-source [Model Context Protocol](https://modelcontextprotocol.io) server that lets Claude, ChatGPT, Cursor or any MCP client analyze **your own** broker exports. It parses **DAS Trader Pro** and **Robinhood** CSVs, rebuilds round trips, and reports your stats plus the behavioral patterns where your results were weakest: time of day, sizing after a loss, hold time, symbol and day of week.

- **Local and private:** no broker login, no cloud. Fills are stored in `~/.tapelog/fills.json` on your machine.
- **Free:** MIT licensed.
- **Process, not picks:** TapeLog describes what you already did. It never suggests trades.

> **Disclaimer:** TapeLog is an educational, record-keeping tool. It is **not investment advice**, and TapeLog is **not a registered investment adviser** or broker-dealer. It does not recommend buying, selling or holding any security, does not give price targets, signals or market predictions, and does not place trades. Past results don't predict future results.

## Tools

| Tool | What it does |
|---|---|
| `import_fills` | Import a DAS Trader Trades-window CSV, a Robinhood account activity CSV, or a generic CSV (`date,time,symbol,side,qty,price,fees`). Duplicates are skipped. |
| `get_stats` | Net P&L, win rate, profit factor, expectancy, average win and loss, payoff ratio, max drawdown, losing streak, hold time, and PDT day-trade count over the last 5 business days |
| `find_leaks` | Descriptive breakdowns of your weakest groups, for example *"Your 18 trades entered 11:00-12:00 netted -$2,039 (win rate 11%)"* or *"After a loss your position was 2.1x larger"* |
| `compare_periods` | Period A vs period B, such as last week vs this week |
| `list_trades` | Your reconstructed round trips |
| `clear_data` | Deletes all stored fills (requires `confirm=true`) |

## Install

You need Python 3.10+ and [uv](https://docs.astral.sh/uv/), or pip.

**Claude Desktop:** add this to `claude_desktop_config.json` (Settings, then Developer, then Edit Config):

```json
{
  "mcpServers": {
    "tapelog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/tapelog-journal/tapelog-mcp", "tapelog-mcp"]
    }
  }
}
```

**Cursor:** add the same block under `mcpServers` in `~/.cursor/mcp.json`.

**Claude Code:** `claude mcp add tapelog -- uvx --from git+https://github.com/tapelog-journal/tapelog-mcp tapelog-mcp`

**Other MCP clients (Windsurf, VS Code, Cline, Goose):** use a stdio server with command `uvx` and the args shown above. Or run `pip install git+https://github.com/tapelog-journal/tapelog-mcp` and use the command `tapelog-mcp`.

Optional: set the env var `TAPELOG_DATA=/path/to/fills.json` to change where fills are stored.

## Use it

> "Import ~/Downloads/trades.csv with trade_date 2026-10-15, then show my stats and find my leaks."

> "Compare Sept 1-15 to Sept 16-30."

**Exporting your trades:** in DAS Trader, open the Trades window, right-click and choose Export. DAS files have no date, so pass `trade_date`. In Robinhood, go to Account, then Reports and statements, then Account activity report (CSV). Step-by-step guides are on the [TapeLog site](https://tapelog-journal.github.io/tapelog/guides/).

**No MCP?** The [`/coach`](coach/) folder has a ready-to-paste Custom GPT or Claude Project instruction pack and a one-shot prompt that works on an uploaded CSV.

## Scope rules (enforced in the server instructions and coach prompts)

TapeLog analyzes only your past behavior and process: timing, sizing, hold times and discipline. Findings are descriptive. Small samples are flagged, and patterns are framed as prompts for reflection, not signals.

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -e . pytest && .venv/bin/pytest -q
```

Everything in `samples/` is synthetic sample data. More free tools are at [tapelog-journal.github.io/tapelog](https://tapelog-journal.github.io/tapelog/ai-coach/), and there's a weekly newsletter at [thetapelog.beehiiv.com](https://thetapelog.beehiiv.com/subscribe).

Not affiliated with DAS Inc., Robinhood Markets, Inc., Anthropic or OpenAI.
