# Publishing tapelog-mcp

Status: PyPI-ready (sdist + wheel build, `twine check --strict` passes). Not yet published.

## 1. PyPI
1. Create a PyPI account (https://pypi.org/account/register/) with the TapeLog email, verify it, and turn on 2FA (required to upload).
2. Create an API token (Account settings, API tokens; scope "Entire account" for the first upload, then a project-scoped token).
3. Upload:
   ```bash
   python -m pip install build twine
   rm -rf dist && python -m build
   twine check --strict dist/*
   twine upload dist/*        # username: __token__, password: the pypi-... token
   ```
   Optional later: Trusted Publishing from GitHub Actions instead of a token.
4. Check https://pypi.org/project/tapelog-mcp/ shows the README (it contains the `mcp-name:` line the registry checks).

## 2. Official MCP Registry (after step 1)
```bash
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
./mcp-publisher login github     # device flow; the GitHub user must be an Owner of the tapelog-journal org
./mcp-publisher publish          # reads server.json
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.tapelog-journal/tapelog-mcp"
```

## Releasing a new version
Bump the version in `pyproject.toml`, `src/tapelog_mcp/__init__.py` and both `version` fields in `server.json`, then repeat both steps.
