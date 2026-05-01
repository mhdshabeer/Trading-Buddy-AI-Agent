# Trading Buddy AI
### Autonomous AI Trading Journal Agent — Voice, MT5, PostgreSQL, Notion, Telegram

---

## What It Does

Removes all friction from trade journaling.

Trade closes in MT5 → bot detects it within 5 seconds → pings you on Telegram → you send a voice memo → AI transcribes, extracts psychology, saves everything to PostgreSQL and Notion. No spreadsheets, no manual input, no dashboards.

Also answers natural language queries about your trading behavior directly in Telegram:
> *"What's my win rate when I felt impatient?"*
> *"Show me total profit for EURUSD last month"*

---

## Architecture

```
Telegram User
      ↕
Telegram MCP Server
      ↕
Orchestrator (async polling loop)
      ├── MT5 MCP Server         ←→ MetaTrader 5 Terminal (Windows)
      ├── PostgreSQL MCP Server  ←→ Local PostgreSQL DB
      ├── Notion MCP Server      ←→ Notion API
      └── Services:
            ├── Voice Transcription  (faster-whisper, local)
            ├── Psychology Extractor (Groq LLM)
            ├── Market Digest        (Forex Factory + Finnhub + Groq)
            └── Analytics Queries    (NL → SQL → LLM formatted answer)
```

---

## Full Trade Journaling Flow

```
MT5 trade closes
      ↓
MT5 poller detects it within 5 seconds
(filters zero-profit opening deals, deduplicates via persisted ticket set)
      ↓
Trade added to queue
      ↓
Queue worker pops one trade, sends Telegram prompt:
"EURUSD +$120.50 — explain your logic, psychology, mistakes"
      ↓
You reply with voice memo or text
      ↓
Voice → faster-whisper transcription (local, zero API cost)
      ↓
Groq LLM extracts 7 structured fields (JSON schema enforced):
  htf_bias, trade_logic, confluences,
  psychology_during, psychology_after,
  mistake, learning
      ↓
MT5 auto-fields + extracted psychology merged into complete entry
      ↓
Saved to PostgreSQL (analytics) + Notion page created (readable mirror)
      ↓
Telegram confirmation sent
```

---

## Analytics Queries

Ask anything about your trading history directly in Telegram:

| You ask | What happens |
|---------|-------------|
| "What's my win rate when psychology was scared?" | LLM generates SQL → executes → LLM formats answer |
| "Show me total profit for EURUSD last month" | LLM generates SQL → executes → LLM formats answer |
| "How many trades did I win last week?" | Returns: "You won 12 trades in the last 7 days" |

The system generates a PostgreSQL SELECT query from your question, executes it, and returns a clean natural language answer — all without leaving Telegram.

---

## Market Digest

Text `/digest` at any time:

```
/digest
  ↓
Fetches today's economic calendar (Forex Factory)
Fetches latest forex news (Finnhub API)
Converts event times to IST
Groq LLM summarises into a short actionable briefing
  ↓
Delivered to your Telegram
```

Red-folder (high-impact) events are listed separately. On-demand only — no scheduled noise.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Python asyncio, LangChain MCP adapters |
| LLM | Groq (llama-3.3-70b-versatile) |
| Transcription | faster-whisper (base, CPU, local) |
| Trading Platform | MetaTrader 5 + Python MT5 library |
| MCP Framework | mcp Python SDK (stdio transport) |
| Messaging | Telegram Bot API |
| Primary Database | PostgreSQL (local) |
| Mirror | Notion API |
| HTTP Client | httpx (async) |
| State Persistence | JSON file (processed_tickets.json) |

---

## MCP Servers

Each integration runs as an isolated subprocess exposing tools via stdio JSON-RPC:

| Server | Tools Exposed |
|--------|--------------|
| `telegram_mcp.py` | `send_message`, `poll_updates` |
| `mt5_mcp.py` | `get_closed_trades`, `get_account_info`, `get_open_positions` |
| `postgresql_mcp.py` | `insert_trade`, `query_trades` |
| `notion_mcp.py` | `create_journal_page` |

The orchestrator connects to all four at startup. Each server can be swapped or extended independently without touching the orchestrator.

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| MCP servers as separate processes | Modular — each integration is independent and swappable |
| No LLM in polling loop | Prevents unwanted replies; LLM only activates when a decision is needed |
| Local faster-whisper transcription | Zero API cost, no latency, no internet dependency for transcription |
| Trade queue (one at a time) | Multiple simultaneous closures handled cleanly — no mixed psychology notes |
| PostgreSQL + Notion dual storage | PostgreSQL for unlimited analytics queries; Notion for human-readable review |
| Persistent processed_tickets.json | Survives restarts — no duplicate prompts for already-journaled trades |

---

## Database Schema (trades table)

```sql
CREATE TABLE trades (
    id              VARCHAR PRIMARY KEY,
    trade_date      DATE,
    asset           VARCHAR,
    direction       VARCHAR CHECK (direction IN ('long', 'short')),
    lot_size        FLOAT,
    entry_price     FLOAT,
    exit_price      FLOAT,
    profit_loss     FLOAT,
    htf_bias        VARCHAR,
    trade_logic     TEXT,
    confluences     VARCHAR,
    psychology_during VARCHAR,
    psychology_after  VARCHAR,
    mistake         VARCHAR,
    learning        TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## Running Locally

**Requirements:**
- Windows (MT5 Python library is Windows-only)
- MetaTrader 5 terminal open and logged in
- Python 3.11+
- PostgreSQL running locally
- Telegram bot token + chat ID

**Setup:**
```bash
git clone https://github.com/mhdshabeer/Trading-Buddy-AI-Agent.git
cd Trading-Buddy-AI-Agent
pip install -r requirements.txt
cp .env.example .env
# fill in your API keys in .env
```

**Environment variables (.env):**
```
GROQ_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
NOTION_API_KEY=
NOTION_DATABASE_ID=
FINNHUB_API_KEY=
DATABASE_URL=postgresql://localhost/trading_buddy
```

**Run:**
```bash
python src/agent/orchestrator.py
```

Bot starts. Open MT5, start trading. Everything else is automatic.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/digest` | Fetches today's economic events + news, returns LLM summary |
| `/skip` | Skips current trade journal prompt, moves to next in queue |
| Any question | Treated as analytics query — LLM generates SQL, returns answer |
| Voice memo | Transcribed and used as journal entry if bot is awaiting psychology |

---

## What's Next (v2)

- Docker containerisation
- AWS EC2 deployment (removes Windows dependency)

---

## Project Status

Core journaling loop, market digest, and analytics queries are fully working locally. PostgreSQL storage and Notion mirror both operational. Built and tested over 3 weeks as a real tool for personal use.

---

*Built to solve a real problem. Every component you see was debugged against actual MT5 data, real Telegram voice memos, and a live PostgreSQL instance.*
