# Trading Buddy AI  
Autonomous AI Trading Journal Agent (MT5 + Telegram + LLM + PostgreSQL + Notion)

---

## TL;DR
AI agent that automatically journals your MetaTrader 5 trades via Telegram voice input, extracts structured psychology using LLMs, and stores everything in PostgreSQL + Notion with natural language analytics and on-demand market/news summaries.

---

## Overview

Trading Buddy AI removes all friction from trade journaling by automating the entire process — from trade detection to structured logging and analytics.

When a trade closes in MT5, the system:
- Detects it in real-time  
- Prompts you via Telegram  
- Accepts voice or text input  
- Transcribes and extracts trading psychology using an LLM  
- Stores structured data for both analytics and review  

No spreadsheets. No manual logging. No missed trades.

---

## Key Features

### Automated Trade Journaling
- Real-time MT5 trade detection (≈5s latency)
- Telegram prompts for instant journaling
- Voice + text input support
- Zero manual data entry

### AI-Powered Psychology Extraction
- Voice → text via local transcription (faster-whisper)
- LLM extracts structured fields:
  - HTF bias  
  - Trade logic  
  - Confluences  
  - Psychology during & after  
  - Mistakes & learnings  

### Natural Language Analytics
Ask questions directly in Telegram:
- “What’s my win rate when I felt impatient?”
- “Total profit for EURUSD last month?”
- “How many trades did I win this week?”

Pipeline:
NL → SQL → execution → formatted response

### On-Demand Market & News Digest
- Triggered via `/digest`
- Aggregates:
  - Economic calendar (Forex Factory)
  - Latest forex news (Finnhub)
- LLM generates a concise, actionable briefing
- Highlights high-impact events separately
- Fully on-demand (no spam)

---

## Architecture

```
Telegram User
      ↕
Telegram MCP Server
      ↕
Orchestrator (async event loop)
      ├── MT5 MCP Server         ↔ MetaTrader 5 Terminal
      ├── PostgreSQL MCP Server  ↔ Local Database
      ├── Notion MCP Server      ↔ Notion API
      └── Services:
            ├── Transcription      (faster-whisper, local)
            ├── LLM Processing     (Groq / LLaMA)
            ├── Market Digest      (Forex Factory + Finnhub)
            └── Analytics Engine   (NL → SQL → response)
```

---

## Trade Journaling Flow

```
MT5 trade closes
      ↓
Detected by polling engine (deduplicated via ticket tracking)
      ↓
Queued for processing
      ↓
Telegram prompt sent:
"EURUSD +$120 — explain your logic, psychology, mistakes"
      ↓
User responds (voice/text)
      ↓
Voice → transcription (local)
      ↓
LLM extracts structured psychology (JSON schema)
      ↓
Merged with MT5 trade data
      ↓
Stored in:
  • PostgreSQL (analytics)
  • Notion (human-readable journal)
      ↓
Confirmation sent via Telegram
```

---

## Tech Stack

| Layer | Technology |
|------|-----------|
| Language | Python |
| Orchestration | asyncio |
| LLM | Groq (LLaMA models) |
| Transcription | faster-whisper (local, CPU) |
| Trading Platform | MetaTrader 5 (Python API) |
| Architecture | MCP (Model Context Protocol) |
| Messaging | Telegram Bot API |
| Database | PostgreSQL |
| Knowledge Mirror | Notion API |
| APIs | Finnhub, Forex Factory |
| HTTP Client | httpx |

---

## MCP-Based Modular Design

Each integration runs as an isolated subprocess (JSON-RPC over stdio):

| Server | Responsibility |
|--------|---------------|
| Telegram MCP | Messaging + polling |
| MT5 MCP | Trade + account data |
| PostgreSQL MCP | Data storage + queries |
| Notion MCP | Journal visualization |

---

## Database Schema (Trades)

```sql
CREATE TABLE trades (
    id VARCHAR PRIMARY KEY,
    trade_date DATE,
    asset VARCHAR,
    direction VARCHAR,
    lot_size FLOAT,
    entry_price FLOAT,
    exit_price FLOAT,
    profit_loss FLOAT,
    htf_bias VARCHAR,
    trade_logic TEXT,
    confluences VARCHAR,
    psychology_during VARCHAR,
    psychology_after VARCHAR,
    mistake VARCHAR,
    learning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Running Locally

### Requirements
- Windows (required for MT5 Python API)
- MetaTrader 5 terminal running
- Python 3.11+
- PostgreSQL
- Telegram bot credentials

### Setup

```bash
git clone https://github.com/mhdshabeer/Trading-Buddy-AI-Agent.git
cd Trading-Buddy-AI-Agent
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

```
GROQ_API_KEY = 
mt5_ID = 
mt5_PASSWORD = 
TELEGRAM_BOT_TOKEN = 
TELEGRAM_CHAT_ID = 
FINNHUB_API_KEY=
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
NOTION_API_KEY=
NOTION_DATABASE_ID=
```

### Run

```bash
python src/main.py
```

---

## Commands

| Command | Description |
|--------|------------|
| `/digest` | Market + news summary |
| `/skip` | Skip current trade |
| Any question | Triggers analytics query |
| Voice note | Used for journaling |

---

## Key Design Decisions

- No LLM in polling loop → avoids unnecessary computation  
- Local transcription → zero API cost, faster, private  
- Queue-based journaling → prevents overlapping trade logs  
- Dual storage (PostgreSQL + Notion)  
- Persistent trade tracking → prevents duplicate entries  

---

## Project Status

Core system fully functional:
- Trade detection  
- Voice journaling  
- Psychology extraction  
- Analytics queries  
- Market/news digest  

Built and tested on real MT5 trades, Telegram interactions, and a live PostgreSQL database.

---

## Roadmap (v2)

- Docker containerization  
- Cloud deployment (AWS EC2)  

---

## License

MIT License

---

## Author

Mohammed Shabeer
