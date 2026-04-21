# Trading Buddy AI

An AI-powered trading assistant that journals trades via voice, provides market digests, and answers analytics queries. Built with Groq LLM, LangChain, MCP (Model Context Protocol), MT5, PostgreSQL, Notion, and Telegram.

## Current Progress (Day 1)
- ✅ Groq LLM integration
- ✅ LangChain agent with tool calling
- ✅ MetaTrader 5 direct connection
- ✅ MT5 wrapped as LangChain tool
- ✅ First MCP server (MT5) exposing `get_account_balance`

## How to Run Steps 1-6
1. Clone the repo
2. Copy `.env.example` to `.env` and add your `GROQ_API_KEY`
3. Install dependencies: `pip install -r requirements.txt`
4. Run each script in `scripts/` folder in order (01 to 06)

## Next Steps
- Telegram MCP server for voice journaling
- PostgreSQL MCP server for analytics
- Notion MCP server as readable mirror
- On‑demand morning digest via `/digest` command

## Tech Stack
- Groq (Llama 3.3 70B, Whisper)
- LangChain + MCP
- MetaTrader 5
- PostgreSQL / Notion
- Docker + AWS (planned for v2)
