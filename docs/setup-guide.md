# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

- [ ] Python 3.10+
- [ ] pip
- [ ] IBM Bob installed and configured (for the full conversational demo — the `--demo` mode below works without it)
- [ ] (Optional) An IBM Cloud account with watsonx.ai access, if you want report-language polishing

## Environment Variables

Copy `.env.example` to `.env` inside `src/` and fill in the values:

```bash
cd src
cp .env.example .env
```

| Variable | Description | Required |
|---|---|---|
| `WATSONX_API_KEY` | IBM watsonx.ai API key | No — pipeline works fully offline without it |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | No |
| `WATSONX_URL` | watsonx.ai region endpoint | No (defaults to `us-south`) |
| `APP_ENV` | `development` or `production` | No |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/[your-org]/[your-repo].git
cd [your-repo]

# 2. Install dependencies
cd src/mcp_server
pip install -r requirements.txt
```

## Running the Application

### Option A — Quick local demo (no Bob/MCP wiring needed)

```bash
cd src/mcp_server
python server.py --demo
```

This runs the full 4-stage pipeline (classify → score → map → draft) against a sample set of observations and prints the generated expert opinion report to the console.

### Option B — As an MCP server for IBM Bob

```bash
cd src/mcp_server
python server.py
```

Then register it with IBM Bob as an MCP server (stdio transport) pointing at this command, per your Bob MCP configuration. Once registered, ask Bob to walk through an examination — e.g.:

> "I have a suspected forged property document. The signature stroke pattern doesn't match the exemplar, and the paper fluoresces differently under UV. Can you classify this and draft a report?"

Bob will call `classify_anomaly_tool`, `score_forgery_confidence_tool`, `map_to_examination_standard_tool`, and `draft_expert_report_tool` in sequence.

## Connecting to IBM Bob

This repo already includes a project-level MCP config at `.bob/mcp.json`, pointing Bob at `src/mcp_server/server.py` via stdio. Open this repo folder in Bob and it should pick up the `docuverity` server automatically.

If it doesn't show up (e.g. Bob only reads `.bob/mcp.json` per-workspace and needs a restart, or your Bob version expects the global file instead):
1. Open Bob → click the **3 dots next to the gear icon** (top-right of the chat panel) → **MCP Servers**.
2. Either confirm `docuverity` is listed and enabled, or manually add it with:
   - **Command:** `python`
   - **Args:** `["server.py"]`
   - **Working directory:** the absolute path to `src/mcp_server` in your clone
3. Ask Bob something like: *"I have a suspected forged property document — the signature stroke pattern doesn't match the exemplar, and the paper fluoresces differently under UV. Classify this and draft a report."* Bob should call the 4 `docuverity` tools in sequence.

Reference: [Using MCP in Bob](https://bob.ibm.com/docs/ide/configuration/mcp/mcp-in-bob).

## Running Tests

No automated test suite yet — see `known_limitations` in `submission.yaml`. The `--demo` mode above serves as a smoke test of the full pipeline.

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Run `pip install -r requirements.txt` inside `src/mcp_server/`. Note: `--demo` mode works even without the `mcp` package installed. |
| `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | You have `mcp` v2.x installed, which renamed `FastMCP`. Run `pip install "mcp<2.0.0"` to get the compatible v1 API this code uses. |
| `ModuleNotFoundError: No module named 'forensics'` | Run `server.py` from inside `src/mcp_server/` (relative imports depend on the working directory). |
| watsonx.ai call fails / times out | This is expected if `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` aren't set — the pipeline falls back to the unpolished report automatically. Check `src/mcp_server/watsonx_polish.py` if you want to debug a configured key. |
| Garbled `—`/`→` characters in Windows terminal output | Cosmetic only (console codepage) — files are UTF-8; safe to ignore, or run `chcp 65001` first. |
