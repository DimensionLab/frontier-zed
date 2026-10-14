The Frontier context server is `python -m frontier_agent mcp` from the `frontier-agent`
package that ships with Frontier. Nothing is bundled with the extension: point it at an
interpreter that has the package installed.

1. Install Frontier as its documentation describes (Python 3.11 or newer); in a Frontier
   checkout `uv sync` creates `.venv` with the package.

2. Check that the server starts from a terminal:

   ```sh
   /path/to/.venv/bin/python -m frontier_agent mcp --help
   ```

3. Set `python` below to that interpreter. Without it the extension runs `python3` from
   your PATH.

Datasets are resolved from `datasets_dir` (or the `FRONTIER_DATASETS_DIR` environment
variable). Leave `approver` at `none`: in this mode the server refuses every operation that
writes unless the site policy grants autonomy, which is the safe setting for an agent panel
that has no approval dialog wired to Frontier. Data-prep sessions with approvals run
through the Frontier ACP agent (`python -m frontier_agent acp`), not through this server.
