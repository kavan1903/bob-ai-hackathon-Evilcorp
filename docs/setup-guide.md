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

## Running Tests

No automated test suite yet — see `known_limitations` in `submission.yaml`. The `--demo` mode above serves as a smoke test of the full pipeline.

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Run `pip install -r requirements.txt` inside `src/mcp_server/`. Note: `--demo` mode works even without the `mcp` package installed. |
| `ModuleNotFoundError: No module named 'forensics'` | Run `server.py` from inside `src/mcp_server/` (relative imports depend on the working directory). |
| watsonx.ai call fails / times out | This is expected if `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` aren't set — the pipeline falls back to the unpolished report automatically. Check `src/mcp_server/watsonx_polish.py` if you want to debug a configured key. |
| Garbled `—`/`→` characters in Windows terminal output | Cosmetic only (console codepage) — files are UTF-8; safe to ignore, or run `chcp 65001` first. |
