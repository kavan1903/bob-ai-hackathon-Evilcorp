# Source Code

All of DocuVerity's source code lives in `mcp_server/`.

```
src/
├── .env.example              ← Template for environment variables (watsonx.ai is optional)
├── README.md                 ← This file
└── mcp_server/
    ├── server.py              ← MCP server entry point (4 tools) + --demo mode
    ├── forensics.py           ← Core classification / scoring / mapping / report-drafting logic
    ├── watsonx_polish.py      ← Optional watsonx.ai report language polishing (safe no-op if unconfigured)
    └── requirements.txt       ← Python dependencies
```

## Running it

```bash
cd src/mcp_server
pip install -r requirements.txt
cp ../.env.example .env   # optional — only needed for watsonx.ai polishing

# Quick local demo, no Bob/MCP wiring required:
python server.py --demo

# Run as an MCP server for IBM Bob to connect to:
python server.py
```

See [`docs/setup-guide.md`](../docs/setup-guide.md) for how to register this server with IBM Bob.

## What NOT to Include in src/

- `.env` files with real secrets
- Large binary files
- `__pycache__/` or `.venv/` (already in `.gitignore`)
