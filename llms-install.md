# Installing TapeLog MCP (for AI agents such as Cline)

TapeLog MCP is a local stdio server. It needs no API key and no broker login.

1. Make sure Python 3.10+ and `uv` are available (`uv --version`). If `uv` is missing, install it: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).
2. Add this server to the MCP settings file:

```json
{
  "mcpServers": {
    "tapelog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/tapelog-journal/tapelog-mcp", "tapelog-mcp"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

   Alternative without uv: `pip install git+https://github.com/tapelog-journal/tapelog-mcp`, then use `"command": "tapelog-mcp"` with no args.
3. Optional: set env `TAPELOG_DATA` to a file path to change where fills are stored (default `~/.tapelog/fills.json`).
4. Verify: call `get_stats`. With no data it returns `"trades": 0`. To try it with sample data, call `import_fills` with `file_path` pointing to a CSV from the repo's `samples/` folder (for DAS files also pass `trade_date`, e.g. `2026-10-15`), then `get_stats`, `find_leaks` or `weekly_habit_report`.

TapeLog describes the user's own past trades only. It is educational, not investment advice.
