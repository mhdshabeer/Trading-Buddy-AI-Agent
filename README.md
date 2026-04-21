# Trading Buddy AI

An AI-powered trading assistant that journals trades via voice, provides on-demand market digests, and answers analytics queries. Built with Groq LLM, LangChain, MCP (Model Context Protocol), MT5, PostgreSQL, Notion, and Telegram.

---

## 🚀 Current Status (End of Day 2)

| Component | Status |
|-----------|--------|
| Groq LLM (direct call) | ✅ |
| LangChain agent (no tools) | ✅ |
| Agent with fake tool | ✅ |
| MT5 direct connection | ✅ |
| MT5 as LangChain tool | ✅ |
| MT5 as MCP server | ✅ |
| Telegram MCP – send_message | ✅ |
| Telegram MCP – poll_updates | ✅ |
| File-based memory for Telegram | ✅ |
| Polling client (no LLM, stable) | ✅ |

Next up (Day 3):
- Add /digest command handler (economic calendar + news → LLM summary)
- Voice memo handling (download audio → Whisper transcription)

---

## 📁 Project Structure

trading-buddy-ai/
├── src/
│   ├── mcp_servers/
│   │   ├── mt5_mcp.py
│   │   └── telegram_mcp.py
│   └── ...
├── scripts/
│   ├── 01_llm_only.py
│   ├── 02_agent_no_tools.py
│   ├── 03_agent_fake_tool.py
│   ├── 04_mt5_direct.py
│   ├── 05_agent_mt5_tool.py
│   ├── 06_mcp_client.py
│   └── test_telegram_polling.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md

---

## 🧪 How to Run

.env:
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_numeric_chat_id
GROQ_API_KEY=your_groq_key

pip install -r requirements.txt
python scripts/test_telegram_polling.py

---

## Notes

- MT5 must be open and logged in
- Start Telegram bot with /start
- Runs locally (Docker/AWS later)
